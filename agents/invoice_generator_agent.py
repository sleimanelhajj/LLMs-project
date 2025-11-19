"""
Invoice Generator Agent

Uses LangGraph for multi-step invoice generation workflow.
This demonstrates a state machine with validation, calculation, and PDF generation.
"""

import asyncio
import sqlite3
from typing import Dict, Any, List, Annotated, TypedDict
from datetime import datetime
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage

from agents.base_agent import BaseAgent
from models.schemas import QueryRequest, AgentResponse
from config import DEFAULT_LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_RETRIES, CATALOG_DB_PATH


# Define the state structure for LangGraph
class InvoiceState(TypedDict):
    """State for invoice generation workflow."""
    # Input
    customer_name: str
    customer_address: str
    items: List[Dict[str, Any]]  # [{"sku": "PP-ROPE-001", "quantity": 100}, ...]
    
    # Intermediate
    validated_items: List[Dict[str, Any]]
    subtotal: float
    tax_rate: float
    tax_amount: float
    discount_rate: float
    discount_amount: float
    total: float
    
    # Output
    invoice_number: str
    invoice_date: str
    pdf_path: str
    
    # Control
    errors: List[str]
    current_step: str
    success: bool


class InvoiceGeneratorAgent(BaseAgent):
    """
    Agent for generating invoices using LangGraph state machine.
    
    Workflow:
    1. Validate Input - Check customer and items data
    2. Fetch Prices - Get product details from catalog
    3. Calculate Totals - Apply discounts and taxes
    4. Generate PDF - Create formatted invoice
    """
    
    def __init__(self, google_api_key: str, db_path: str, output_dir: str = "data/invoices"):
        super().__init__(
            name="InvoiceGeneratorAgent",
            description="Generates professional invoices using multi-step workflow"
        )
        self.google_api_key = google_api_key
        self.db_path = db_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize LLM
        self.llm = ChatGoogleGenerativeAI(
            model=DEFAULT_LLM_MODEL,
            temperature=0.1,  # Low temperature for precise calculations
            google_api_key=google_api_key,
            max_retries=LLM_MAX_RETRIES,
        )
        
        # Build LangGraph workflow
        self.workflow = self._build_workflow()
        self.app = self.workflow.compile()
        
        # Invoice counter
        self.invoice_counter = self._get_next_invoice_number()
    
    def _get_next_invoice_number(self) -> int:
        """Get next invoice number."""
        existing = list(self.output_dir.glob("INV-*.pdf"))
        if not existing:
            return 1
        
        numbers = []
        for f in existing:
            try:
                num = int(f.stem.split("-")[1])
                numbers.append(num)
            except:
                pass
        
        return max(numbers) + 1 if numbers else 1
    
    def can_handle(self, query: str) -> bool:
        """Check if query is invoice-related."""
        keywords = [
            "invoice", "generate invoice", "create invoice", "bill",
            "quote", "quotation", "order", "purchase order"
        ]
        return any(keyword in query.lower() for keyword in keywords)
    
    def _build_workflow(self) -> StateGraph:
        """Build LangGraph workflow for invoice generation."""
        
        workflow = StateGraph(InvoiceState)
        
        # Add nodes
        workflow.add_node("validate_input", self._validate_input)
        workflow.add_node("fetch_prices", self._fetch_prices)
        workflow.add_node("calculate_totals", self._calculate_totals)
        workflow.add_node("generate_pdf", self._generate_pdf)
        
        # Define edges
        workflow.set_entry_point("validate_input")
        
        workflow.add_conditional_edges(
            "validate_input",
            self._check_validation,
            {
                "continue": "fetch_prices",
                "error": END
            }
        )
        
        workflow.add_conditional_edges(
            "fetch_prices",
            self._check_fetch,
            {
                "continue": "calculate_totals",
                "error": END
            }
        )
        
        workflow.add_edge("calculate_totals", "generate_pdf")
        workflow.add_edge("generate_pdf", END)
        
        return workflow
    
    # State machine nodes
    
    def _validate_input(self, state: InvoiceState) -> InvoiceState:
        """Validate customer and items input."""
        print("[InvoiceGenerator] Step 1: Validating input...")
        
        state["current_step"] = "validate_input"
        state["errors"] = []
        
        # Validate customer name
        if not state.get("customer_name") or len(state["customer_name"].strip()) < 2:
            state["errors"].append("Customer name is required and must be at least 2 characters")
        
        # Validate customer address
        if not state.get("customer_address") or len(state["customer_address"].strip()) < 5:
            state["errors"].append("Customer address is required")
        
        # Validate items
        if not state.get("items") or len(state["items"]) == 0:
            state["errors"].append("At least one item is required")
        else:
            for i, item in enumerate(state["items"]):
                if not item.get("sku"):
                    state["errors"].append(f"Item {i+1}: SKU is required")
                if not item.get("quantity") or item["quantity"] <= 0:
                    state["errors"].append(f"Item {i+1}: Valid quantity is required")
        
        if state["errors"]:
            print(f"[InvoiceGenerator] Validation failed: {state['errors']}")
            state["success"] = False
        else:
            print("[InvoiceGenerator] ✓ Input validated")
            state["success"] = True
        
        return state
    
    def _fetch_prices(self, state: InvoiceState) -> InvoiceState:
        """Fetch product details from catalog database."""
        print("[InvoiceGenerator] Step 2: Fetching prices from catalog...")
        
        state["current_step"] = "fetch_prices"
        validated_items = []
        
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            for item in state["items"]:
                sku = item["sku"]
                quantity = item["quantity"]
                
                # Fetch product from database
                cursor.execute(
                    "SELECT * FROM products WHERE sku = ?",
                    (sku,)
                )
                product = cursor.fetchone()
                
                if not product:
                    state["errors"].append(f"Product with SKU '{sku}' not found")
                    continue
                
                # Check stock availability
                if product["quantity_on_hand"] < quantity:
                    state["errors"].append(
                        f"{product['name']}: Insufficient stock (requested: {quantity}, available: {product['quantity_on_hand']})"
                    )
                
                # Calculate line total
                line_total = product["unit_price"] * quantity
                
                validated_items.append({
                    "sku": sku,
                    "name": product["name"],
                    "description": product["description"],
                    "unit_price": product["unit_price"],
                    "unit_of_measure": product["unit_of_measure"],
                    "quantity": quantity,
                    "line_total": line_total
                })
            
            conn.close()
            
            if state["errors"]:
                print(f"[InvoiceGenerator] Price fetch failed: {state['errors']}")
                state["success"] = False
            else:
                state["validated_items"] = validated_items
                print(f"[InvoiceGenerator] ✓ Fetched prices for {len(validated_items)} items")
                state["success"] = True
        
        except Exception as e:
            state["errors"].append(f"Database error: {str(e)}")
            state["success"] = False
            print(f"[InvoiceGenerator] Error fetching prices: {e}")
        
        return state
    
    def _calculate_totals(self, state: InvoiceState) -> InvoiceState:
        """Calculate subtotal, discounts, taxes, and total."""
        print("[InvoiceGenerator] Step 3: Calculating totals...")
        
        state["current_step"] = "calculate_totals"
        
        # Calculate subtotal
        subtotal = sum(item["line_total"] for item in state["validated_items"])
        state["subtotal"] = subtotal
        
        # Apply volume discounts
        if subtotal >= 20000:
            state["discount_rate"] = 0.20
        elif subtotal >= 10000:
            state["discount_rate"] = 0.15
        elif subtotal >= 5000:
            state["discount_rate"] = 0.10
        else:
            state["discount_rate"] = 0.0
        
        state["discount_amount"] = subtotal * state["discount_rate"]
        
        # Calculate tax (8.25% on subtotal after discount)
        taxable_amount = subtotal - state["discount_amount"]
        state["tax_rate"] = 0.0825
        state["tax_amount"] = taxable_amount * state["tax_rate"]
        
        # Calculate total
        state["total"] = taxable_amount + state["tax_amount"]
        
        # Generate invoice metadata
        state["invoice_number"] = f"INV-{self.invoice_counter:06d}"
        state["invoice_date"] = datetime.now().strftime("%Y-%m-%d")
        
        print(f"[InvoiceGenerator] ✓ Subtotal: ${subtotal:.2f}")
        print(f"[InvoiceGenerator] ✓ Discount ({state['discount_rate']*100:.0f}%): -${state['discount_amount']:.2f}")
        print(f"[InvoiceGenerator] ✓ Tax: ${state['tax_amount']:.2f}")
        print(f"[InvoiceGenerator] ✓ Total: ${state['total']:.2f}")
        
        return state
    
    def _generate_pdf(self, state: InvoiceState) -> InvoiceState:
        """Generate PDF invoice."""
        print("[InvoiceGenerator] Step 4: Generating PDF...")
        
        state["current_step"] = "generate_pdf"
        
        try:
            pdf_filename = f"{state['invoice_number']}.pdf"
            pdf_path = self.output_dir / pdf_filename
            
            # Create PDF
            c = canvas.Canvas(str(pdf_path), pagesize=letter)
            width, height = letter
            
            # Header
            c.setFont("Helvetica-Bold", 24)
            c.drawString(1*inch, height - 1*inch, "INVOICE")
            
            c.setFont("Helvetica", 11)
            c.drawString(1*inch, height - 1.4*inch, f"Invoice Number: {state['invoice_number']}")
            c.drawString(1*inch, height - 1.6*inch, f"Date: {state['invoice_date']}")
            
            # Company info (From)
            c.setFont("Helvetica-Bold", 12)
            c.drawString(1*inch, height - 2.2*inch, "From:")
            c.setFont("Helvetica", 10)
            c.drawString(1*inch, height - 2.5*inch, "Warehouse Supply Co.")
            c.drawString(1*inch, height - 2.7*inch, "123 Industrial Park")
            c.drawString(1*inch, height - 2.9*inch, "Dallas, TX 75201")
            c.drawString(1*inch, height - 3.1*inch, "Phone: (555) 123-4567")
            
            # Customer info (Bill To)
            c.setFont("Helvetica-Bold", 12)
            c.drawString(4*inch, height - 2.2*inch, "Bill To:")
            c.setFont("Helvetica", 10)
            c.drawString(4*inch, height - 2.5*inch, state["customer_name"])
            
            # Split address into lines
            address_lines = state["customer_address"].split("\n")
            y_offset = 2.7
            for line in address_lines:
                c.drawString(4*inch, height - y_offset*inch, line.strip())
                y_offset += 0.2
            
            # Items table header
            y = height - 4*inch
            c.setFont("Helvetica-Bold", 10)
            c.drawString(1*inch, y, "Item")
            c.drawString(3.5*inch, y, "Qty")
            c.drawString(4.3*inch, y, "Unit")
            c.drawString(5*inch, y, "Price")
            c.drawString(6*inch, y, "Total")
            
            # Line under header
            c.line(1*inch, y - 0.1*inch, 7*inch, y - 0.1*inch)
            
            # Items
            c.setFont("Helvetica", 9)
            y -= 0.3*inch
            
            for item in state["validated_items"]:
                # Item name
                c.drawString(1*inch, y, item["name"][:35])
                
                # Quantity and unit
                c.drawString(3.5*inch, y, f"{item['quantity']}")
                c.drawString(4.3*inch, y, item["unit_of_measure"])
                
                # Unit price
                c.drawString(5*inch, y, f"${item['unit_price']:.2f}")
                
                # Line total
                c.drawString(6*inch, y, f"${item['line_total']:.2f}")
                
                y -= 0.25*inch
                
                # Page break if needed
                if y < 2*inch:
                    c.showPage()
                    c.setFont("Helvetica", 9)
                    y = height - 1*inch
            
            # Totals section
            y -= 0.3*inch
            c.line(5*inch, y, 7*inch, y)
            
            y -= 0.3*inch
            c.setFont("Helvetica", 10)
            c.drawString(5*inch, y, "Subtotal:")
            c.drawString(6*inch, y, f"${state['subtotal']:.2f}")
            
            if state["discount_amount"] > 0:
                y -= 0.25*inch
                c.drawString(5*inch, y, f"Discount ({state['discount_rate']*100:.0f}%):")
                c.drawString(6*inch, y, f"-${state['discount_amount']:.2f}")
            
            y -= 0.25*inch
            c.drawString(5*inch, y, f"Tax ({state['tax_rate']*100:.2f}%):")
            c.drawString(6*inch, y, f"${state['tax_amount']:.2f}")
            
            y -= 0.3*inch
            c.line(5*inch, y, 7*inch, y)
            
            y -= 0.3*inch
            c.setFont("Helvetica-Bold", 12)
            c.drawString(5*inch, y, "Total:")
            c.drawString(6*inch, y, f"${state['total']:.2f}")
            
            # Footer
            c.setFont("Helvetica", 9)
            c.drawString(1*inch, 1.2*inch, "Payment Terms: Net 30 days")
            c.drawString(1*inch, 1*inch, "Thank you for your business!")
            
            c.save()
            
            state["pdf_path"] = str(pdf_path)
            state["success"] = True
            
            # Increment counter
            self.invoice_counter += 1
            
            print(f"[InvoiceGenerator] ✓ PDF generated: {pdf_path}")
        
        except Exception as e:
            state["errors"].append(f"PDF generation error: {str(e)}")
            state["success"] = False
            print(f"[InvoiceGenerator] Error generating PDF: {e}")
        
        return state
    
    # Edge condition functions
    
    def _check_validation(self, state: InvoiceState) -> str:
        """Check if validation passed."""
        return "continue" if state["success"] and not state["errors"] else "error"
    
    def _check_fetch(self, state: InvoiceState) -> str:
        """Check if price fetch passed."""
        return "continue" if state["success"] and not state["errors"] else "error"
    
    # Public API
    
    async def generate_invoice(
        self,
        customer_name: str,
        customer_address: str,
        items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Generate an invoice using LangGraph workflow.
        
        Args:
            customer_name: Customer name
            customer_address: Customer address (can be multi-line)
            items: List of items [{"sku": "PP-ROPE-001", "quantity": 100}, ...]
            
        Returns:
            Dict with invoice details and status
        """
        
        initial_state: InvoiceState = {
            "customer_name": customer_name,
            "customer_address": customer_address,
            "items": items,
            "validated_items": [],
            "subtotal": 0.0,
            "tax_rate": 0.0,
            "tax_amount": 0.0,
            "discount_rate": 0.0,
            "discount_amount": 0.0,
            "total": 0.0,
            "invoice_number": "",
            "invoice_date": "",
            "pdf_path": "",
            "errors": [],
            "current_step": "",
            "success": False
        }
        
        # Run workflow
        final_state = self.app.invoke(initial_state)
        
        if final_state["success"]:
            return {
                "success": True,
                "invoice_number": final_state["invoice_number"],
                "invoice_date": final_state["invoice_date"],
                "pdf_path": final_state["pdf_path"],
                "subtotal": final_state["subtotal"],
                "discount": final_state["discount_amount"],
                "tax": final_state["tax_amount"],
                "total": final_state["total"],
                "items": final_state["validated_items"]
            }
        else:
            return {
                "success": False,
                "errors": final_state["errors"],
                "current_step": final_state["current_step"]
            }
    
    async def process_query(self, request: QueryRequest) -> AgentResponse:
        """Process invoice generation request with conversational flow."""
        
        # Get session state from metadata
        metadata = request.metadata or {}
        invoice_state = metadata.get('invoice_state', {})
        step = invoice_state.get('step', 'start')
        
        query_lower = request.query.lower()
        
        # Step 1: Start - Ask for customer name
        if step == 'start':
            return AgentResponse(
                agent_name=self.name,
                response="📋 I'll help you generate an invoice! Let's start with the customer details.\n\nWhat is the customer's name?",
                success=True,
                data={
                    'invoice_state': {
                        'step': 'waiting_for_name',
                        'collected': {}
                    }
                }
            )
        
        # Step 2: Collect name, ask for address
        elif step == 'waiting_for_name':
            invoice_state['collected']['customer_name'] = request.query
            return AgentResponse(
                agent_name=self.name,
                response=f"Great! Customer name: **{request.query}**\n\nNow, what is the customer's address? (You can provide it in one line or multiple lines)",
                success=True,
                data={
                    'invoice_state': {
                        'step': 'waiting_for_address',
                        'collected': invoice_state['collected']
                    }
                }
            )
        
        # Step 3: Collect address, ask for items
        elif step == 'waiting_for_address':
            invoice_state['collected']['customer_address'] = request.query
            return AgentResponse(
                agent_name=self.name,
                response=f"Perfect! Address saved.\n\nNow, let's add items to the invoice. Please provide items in this format:\n\n**SKU: quantity**\n\nFor example:\n- PP-ROPE-001: 100\n- NY-BAG-001: 50\n- CLIP-001: 20\n- HOOK-001: 10\n\nYou can provide one item per message, or multiple items separated by commas or new lines. Type **'done'** when you're finished adding items.",
                success=True,
                data={
                    'invoice_state': {
                        'step': 'waiting_for_items',
                        'collected': invoice_state['collected']
                    }
                }
            )
        
        # Step 4: Collect items
        elif step == 'waiting_for_items':
            if 'items' not in invoice_state['collected']:
                invoice_state['collected']['items'] = []
            
            # Check if user is done
            if query_lower.strip() in ['done', 'finish', 'complete', 'generate', "that's all", "thats all"]:
                if len(invoice_state['collected']['items']) == 0:
                    return AgentResponse(
                        agent_name=self.name,
                        response="⚠️ You haven't added any items yet. Please add at least one item, or type **'cancel'** to start over.",
                        success=True,
                        data={
                            'invoice_state': {
                                'step': 'waiting_for_items',
                                'collected': invoice_state['collected']
                            }
                        }
                    )
                
                # Generate the invoice
                return await self._finalize_invoice(invoice_state['collected'])
            
            # Check for cancel
            if query_lower.strip() in ['cancel', 'stop', 'abort']:
                return AgentResponse(
                    agent_name=self.name,
                    response="❌ Invoice generation cancelled. Type 'generate invoice' if you want to start over.",
                    success=True,
                    data={'invoice_state': {'step': 'start', 'collected': {}}}
                )
            
            # Parse items from message
            parsed_items = self._parse_items_from_text(request.query)
            
            if not parsed_items:
                return AgentResponse(
                    agent_name=self.name,
                    response="⚠️ I couldn't understand that format. Please provide items like:\n\n**PP-ROPE-001: 100** or **CLIP-001: 20** or **NY-BAG-001: 50**\n\nOr type **'done'** if you're finished adding items.",
                    success=True,
                    data={
                        'invoice_state': {
                            'step': 'waiting_for_items',
                            'collected': invoice_state['collected']
                        }
                    }
                )
            
            # Add parsed items
            invoice_state['collected']['items'].extend(parsed_items)
            
            # Show confirmation
            items_summary = "\n".join([
                f"  • {item['sku']}: {item['quantity']} units"
                for item in invoice_state['collected']['items']
            ])
            
            return AgentResponse(
                agent_name=self.name,
                response=f"✅ Items added!\n\n**Current items:**\n{items_summary}\n\nAdd more items, or type **'done'** to generate the invoice.",
                success=True,
                data={
                    'invoice_state': {
                        'step': 'waiting_for_items',
                        'collected': invoice_state['collected']
                    }
                }
            )
        
        # Default: Start the flow
        else:
            return AgentResponse(
                agent_name=self.name,
                response="📋 I'll help you generate an invoice! Let's start with the customer details.\n\nWhat is the customer's name?",
                success=True,
                data={
                    'invoice_state': {
                        'step': 'waiting_for_name',
                        'collected': {}
                    }
                }
            )
    
    def _parse_items_from_text(self, text: str) -> List[Dict[str, Any]]:
        """Parse items from user text input."""
        import re
        
        items = []
        
        # Pattern: SKU: quantity
        # Handle formats: PP-ROPE-001: 100, CLIP-001: 50, ST-CABLE-001: 10
        # Use negative lookbehind/lookahead to prevent matching substrings
        patterns = [
            # Format: XX-YYYY-###: quantity (with colon/comma/dash separator)
            r'(?<![A-Z-])([A-Z]{2,10}-[A-Z]{2,10}-\d{1,5})\s*[:,-]\s*(\d+)(?!\d)',
            # Format: XXXX-###: quantity (with colon/comma/dash separator)
            r'(?<![A-Z-])([A-Z]{2,10}-\d{1,5})\s*[:,-]\s*(\d+)(?!\d)',
            # Format: XX-YYYY-### quantity (space separated)
            r'(?<![A-Z-])([A-Z]{2,10}-[A-Z]{2,10}-\d{1,5})\s+(\d+)(?!\d)',
            # Format: XXXX-### quantity (space separated)
            r'(?<![A-Z-])([A-Z]{2,10}-\d{1,5})\s+(\d+)(?!\d)',
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for sku, quantity in matches:
                # Avoid duplicates
                if not any(item['sku'] == sku.upper() for item in items):
                    items.append({
                        'sku': sku.upper(),
                        'quantity': int(quantity)
                    })
        
        return items
    
    async def _finalize_invoice(self, collected_data: Dict[str, Any]) -> AgentResponse:
        """Generate the final invoice."""
        
        try:
            result = await self.generate_invoice(
                customer_name=collected_data['customer_name'],
                customer_address=collected_data['customer_address'],
                items=collected_data['items']
            )
            
            if result['success']:
                items_summary = "\n".join([
                    f"  • {item['name']}: {item['quantity']} × ${item['unit_price']:.2f} = ${item['line_total']:.2f}"
                    for item in result['items']
                ])
                
                response_text = f"""✅ **Invoice Generated Successfully!**

📄 **Invoice Number:** {result['invoice_number']}
📅 **Date:** {result['invoice_date']}
👤 **Customer:** {collected_data['customer_name']}

**Items:**
{items_summary}

💰 **Subtotal:** ${result['subtotal']:.2f}
"""
                if result['discount'] > 0:
                    response_text += f"🎁 **Discount:** -${result['discount']:.2f}\n"
                
                response_text += f"""📊 **Tax:** ${result['tax']:.2f}
💵 **Total:** ${result['total']:.2f}

📁 **PDF saved to:** {result['pdf_path']}

The invoice has been generated and saved. You can download it using the invoice number: **{result['invoice_number']}**"""
                
                return AgentResponse(
                    agent_name=self.name,
                    response=response_text,
                    success=True,
                    data={
                        'invoice_state': {'step': 'start', 'collected': {}},
                        'invoice_result': result
                    }
                )
            else:
                error_text = "\n".join([f"  • {err}" for err in result['errors']])
                return AgentResponse(
                    agent_name=self.name,
                    response=f"❌ **Invoice generation failed:**\n\n{error_text}\n\nPlease try again by typing 'generate invoice'.",
                    success=False,
                    data={'invoice_state': {'step': 'start', 'collected': {}}}
                )
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            return AgentResponse(
                agent_name=self.name,
                response=f"❌ **Error generating invoice:** {str(e)}\n\nPlease try again by typing 'generate invoice'.",
                success=False,
                data={'invoice_state': {'step': 'start', 'collected': {}}}
            )


# Test function
async def test_invoice_generator():
    """Test the Invoice Generator Agent."""
    from config import GOOGLE_API_KEY
    
    if not GOOGLE_API_KEY:
        print("❌ GOOGLE_API_KEY not found")
        return
    
    print("=" * 80)
    print("INVOICE GENERATOR AGENT TEST - LANGGRAPH WORKFLOW")
    print("=" * 80 + "\n")
    
    agent = InvoiceGeneratorAgent(
        google_api_key=GOOGLE_API_KEY,
        db_path=CATALOG_DB_PATH
    )
    
    # Test case 1: Normal order
    print("TEST 1: Normal Order")
    print("-" * 80)
    
    result1 = await agent.generate_invoice(
        customer_name="John Construction LLC",
        customer_address="456 Builder Ave\nHouston, TX 77001",
        items=[
            {"sku": "PP-ROPE-001", "quantity": 100},
            {"sku": "NY-BAG-001", "quantity": 20},
            {"sku": "ST-WIRE-002", "quantity": 50},
        ]
    )
    
    if result1["success"]:
        print(f"\n✅ Invoice generated successfully!")
        print(f"   Invoice Number: {result1['invoice_number']}")
        print(f"   Date: {result1['invoice_date']}")
        print(f"   Subtotal: ${result1['subtotal']:.2f}")
        print(f"   Discount: -${result1['discount']:.2f}")
        print(f"   Tax: ${result1['tax']:.2f}")
        print(f"   Total: ${result1['total']:.2f}")
        print(f"   PDF: {result1['pdf_path']}")
    else:
        print(f"\n❌ Failed: {result1['errors']}")
    
    print("\n" + "=" * 80 + "\n")
    
    # Test case 2: Large order with discount
    print("TEST 2: Large Order (with 15% discount)")
    print("-" * 80)
    
    result2 = await agent.generate_invoice(
        customer_name="MegaBuild Corporation",
        customer_address="789 Construction Blvd\nDallas, TX 75201",
        items=[
            {"sku": "PP-ROPE-001", "quantity": 1000},
            {"sku": "PP-ROPE-002", "quantity": 500},
            {"sku": "ST-CABLE-001", "quantity": 300},
            {"sku": "NY-BAG-001", "quantity": 100},
        ]
    )
    
    if result2["success"]:
        print(f"\n✅ Invoice generated successfully!")
        print(f"   Invoice Number: {result2['invoice_number']}")
        print(f"   Total: ${result2['total']:.2f}")
        print(f"   Discount Applied: {result2['discount']/result2['subtotal']*100:.0f}%")
        print(f"   PDF: {result2['pdf_path']}")
    else:
        print(f"\n❌ Failed: {result2['errors']}")
    
    print("\n" + "=" * 80 + "\n")
    
    # Test case 3: Invalid SKU
    print("TEST 3: Error Handling (invalid SKU)")
    print("-" * 80)
    
    result3 = await agent.generate_invoice(
        customer_name="Test Customer",
        customer_address="123 Test St",
        items=[
            {"sku": "INVALID-SKU", "quantity": 10},
        ]
    )
    
    if not result3["success"]:
        print(f"\n✅ Error handling worked correctly")
        print(f"   Errors: {result3['errors']}")
    else:
        print(f"\n❌ Should have failed with invalid SKU")
    
    print("\n" + "=" * 80)
    print("✅ TEST COMPLETED")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_invoice_generator())