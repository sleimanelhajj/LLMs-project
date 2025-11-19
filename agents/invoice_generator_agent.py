"""
Invoice Generator Agent

Uses LangGraph for multi-step invoice generation workflow.
This demonstrates a state machine with validation, calculation, and PDF generation.
"""
import sqlite3
from typing import Dict, Any, List, TypedDict
from datetime import datetime
from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

from langgraph.graph import StateGraph, END
from langchain_google_genai import ChatGoogleGenerativeAI

from agents.base_agent import BaseAgent
from models.schemas import QueryRequest, AgentResponse
from config import DEFAULT_LLM_MODEL, LLM_TEMPERATURE, LLM_MAX_RETRIES


class InvoiceState(TypedDict):
    customer_name: str
    customer_address: str
    items: List[Dict[str, Any]]
    validated_items: List[Dict[str, Any]]
    subtotal: float
    tax_rate: float
    tax_amount: float
    discount_rate: float
    discount_amount: float
    total: float
    invoice_number: str
    invoice_date: str
    pdf_path: str
    errors: List[str]
    current_step: str
    success: bool


class InvoiceGeneratorAgent(BaseAgent):
    def __init__(
        self, google_api_key: str, db_path: str, output_dir: str = "data/invoices"
    ):
        super().__init__(
            name="InvoiceGeneratorAgent",
            description="Generates professional invoices using multi-step workflow",
        )
        self.google_api_key = google_api_key
        self.db_path = db_path
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        self.llm = ChatGoogleGenerativeAI(
            model=DEFAULT_LLM_MODEL,
            temperature=0.1,
            google_api_key=google_api_key,
            max_retries=LLM_MAX_RETRIES,
        )

        self.workflow = self._build_workflow()
        self.app = self.workflow.compile()
        self.invoice_counter = self._get_next_invoice_number()

    def _get_next_invoice_number(self) -> int:
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
        keywords = [
            "invoice",
            "generate invoice",
            "create invoice",
            "bill",
            "quote",
            "quotation",
            "order",
            "purchase order",
        ]
        return any(keyword in query.lower() for keyword in keywords)

    def _build_workflow(self) -> StateGraph:
        workflow = StateGraph(InvoiceState)

        workflow.add_node("validate_input", self._validate_input)
        workflow.add_node("fetch_prices", self._fetch_prices)
        workflow.add_node("calculate_totals", self._calculate_totals)
        workflow.add_node("generate_pdf", self._generate_pdf)

        workflow.set_entry_point("validate_input")

        workflow.add_conditional_edges(
            "validate_input",
            self._check_validation,
            {"continue": "fetch_prices", "error": END},
        )

        workflow.add_conditional_edges(
            "fetch_prices",
            self._check_fetch,
            {"continue": "calculate_totals", "error": END},
        )

        workflow.add_edge("calculate_totals", "generate_pdf")
        workflow.add_edge("generate_pdf", END)

        return workflow

    def _validate_input(self, state: InvoiceState) -> InvoiceState:
        print("[InvoiceGenerator] Step 1: Validating input...")

        state["current_step"] = "validate_input"
        state["errors"] = []

        if not state.get("customer_name") or len(state["customer_name"].strip()) < 2:
            state["errors"].append(
                "Customer name is required and must be at least 2 characters"
            )

        if (
            not state.get("customer_address")
            or len(state["customer_address"].strip()) < 5
        ):
            state["errors"].append("Customer address is required")

        if not state.get("items") or len(state["items"]) == 0:
            state["errors"].append("At least one item is required")
        else:
            for i, item in enumerate(state["items"]):
                if not item.get("sku"):
                    state["errors"].append(f"Item {i + 1}: SKU is required")
                if not item.get("quantity") or item["quantity"] <= 0:
                    state["errors"].append(f"Item {i + 1}: Valid quantity is required")

        if state["errors"]:
            print(f"[InvoiceGenerator] Validation failed: {state['errors']}")
            state["success"] = False
        else:
            print("[InvoiceGenerator] Input validated")
            state["success"] = True

        return state

    def _fetch_prices(self, state: InvoiceState) -> InvoiceState:
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

                cursor.execute("SELECT * FROM products WHERE sku = ?", (sku,))
                product = cursor.fetchone()

                if not product:
                    state["errors"].append(f"Product with SKU '{sku}' not found")
                    continue

                if product["quantity_on_hand"] < quantity:
                    state["errors"].append(
                        f"{product['name']}: Insufficient stock (requested: {quantity}, available: {product['quantity_on_hand']})"
                    )

                line_total = product["unit_price"] * quantity

                validated_items.append(
                    {
                        "sku": sku,
                        "name": product["name"],
                        "description": product["description"],
                        "unit_price": product["unit_price"],
                        "unit_of_measure": product["unit_of_measure"],
                        "quantity": quantity,
                        "line_total": line_total,
                    }
                )

            conn.close()

            if state["errors"]:
                print(f"[InvoiceGenerator] Price fetch failed: {state['errors']}")
                state["success"] = False
            else:
                state["validated_items"] = validated_items
                print(
                    f"[InvoiceGenerator] Fetched prices for {len(validated_items)} items"
                )
                state["success"] = True

        except Exception as e:
            state["errors"].append(f"Database error: {str(e)}")
            state["success"] = False
            print(f"[InvoiceGenerator] Error fetching prices: {e}")

        return state

    def _calculate_totals(self, state: InvoiceState) -> InvoiceState:
        print("[InvoiceGenerator] Step 3: Calculating totals...")

        state["current_step"] = "calculate_totals"

        subtotal = sum(item["line_total"] for item in state["validated_items"])
        state["subtotal"] = subtotal

        if subtotal >= 20000:
            state["discount_rate"] = 0.20
        elif subtotal >= 10000:
            state["discount_rate"] = 0.15
        elif subtotal >= 5000:
            state["discount_rate"] = 0.10
        else:
            state["discount_rate"] = 0.0

        state["discount_amount"] = subtotal * state["discount_rate"]

        taxable_amount = subtotal - state["discount_amount"]
        state["tax_rate"] = 0.0825
        state["tax_amount"] = taxable_amount * state["tax_rate"]

        state["total"] = taxable_amount + state["tax_amount"]

        state["invoice_number"] = f"INV-{self.invoice_counter:06d}"
        state["invoice_date"] = datetime.now().strftime("%Y-%m-%d")

        print(f"[InvoiceGenerator] Subtotal: ${subtotal:.2f}")
        print(
            f"[InvoiceGenerator] Discount ({state['discount_rate'] * 100:.0f}%): -${state['discount_amount']:.2f}"
        )
        print(f"[InvoiceGenerator] Tax: ${state['tax_amount']:.2f}")
        print(f"[InvoiceGenerator] Total: ${state['total']:.2f}")

        return state

    def _generate_pdf(self, state: InvoiceState) -> InvoiceState:
        print("[InvoiceGenerator] Step 4: Generating PDF...")

        state["current_step"] = "generate_pdf"

        try:
            pdf_filename = f"{state['invoice_number']}.pdf"
            pdf_path = self.output_dir / pdf_filename

            c = canvas.Canvas(str(pdf_path), pagesize=letter)
            _, height = letter

            c.setFont("Helvetica-Bold", 24)
            c.drawString(1 * inch, height - 1 * inch, "INVOICE")

            c.setFont("Helvetica", 11)
            c.drawString(
                1 * inch,
                height - 1.4 * inch,
                f"Invoice Number: {state['invoice_number']}",
            )
            c.drawString(
                1 * inch, height - 1.6 * inch, f"Date: {state['invoice_date']}"
            )

            c.setFont("Helvetica-Bold", 12)
            c.drawString(1 * inch, height - 2.2 * inch, "From:")
            c.setFont("Helvetica", 10)
            c.drawString(1 * inch, height - 2.5 * inch, "Warehouse Supply Co.")
            c.drawString(1 * inch, height - 2.7 * inch, "123 Industrial Park")
            c.drawString(1 * inch, height - 2.9 * inch, "Dallas, TX 75201")
            c.drawString(1 * inch, height - 3.1 * inch, "Phone: (555) 123-4567")

            c.setFont("Helvetica-Bold", 12)
            c.drawString(4 * inch, height - 2.2 * inch, "Bill To:")
            c.setFont("Helvetica", 10)
            c.drawString(4 * inch, height - 2.5 * inch, state["customer_name"])

            address_lines = state["customer_address"].split("\n")
            y_offset = 2.7
            for line in address_lines:
                c.drawString(4 * inch, height - y_offset * inch, line.strip())
                y_offset += 0.2

            y = height - 4 * inch
            c.setFont("Helvetica-Bold", 10)
            c.drawString(1 * inch, y, "Item")
            c.drawString(3.5 * inch, y, "Qty")
            c.drawString(4.3 * inch, y, "Unit")
            c.drawString(5 * inch, y, "Price")
            c.drawString(6 * inch, y, "Total")

            c.line(1 * inch, y - 0.1 * inch, 7 * inch, y - 0.1 * inch)

            c.setFont("Helvetica", 9)
            y -= 0.3 * inch

            for item in state["validated_items"]:
                c.drawString(1 * inch, y, item["name"][:35])
                c.drawString(3.5 * inch, y, f"{item['quantity']}")
                c.drawString(4.3 * inch, y, item["unit_of_measure"])
                c.drawString(5 * inch, y, f"${item['unit_price']:.2f}")
                c.drawString(6 * inch, y, f"${item['line_total']:.2f}")

                y -= 0.25 * inch

                if y < 2 * inch:
                    c.showPage()
                    c.setFont("Helvetica", 9)
                    y = height - 1 * inch

            y -= 0.3 * inch
            c.line(5 * inch, y, 7 * inch, y)

            y -= 0.3 * inch
            c.setFont("Helvetica", 10)
            c.drawString(5 * inch, y, "Subtotal:")
            c.drawString(6 * inch, y, f"${state['subtotal']:.2f}")

            if state["discount_amount"] > 0:
                y -= 0.25 * inch
                c.drawString(
                    5 * inch, y, f"Discount ({state['discount_rate'] * 100:.0f}%):"
                )
                c.drawString(6 * inch, y, f"-${state['discount_amount']:.2f}")

            y -= 0.25 * inch
            c.drawString(5 * inch, y, f"Tax ({state['tax_rate'] * 100:.2f}%):")
            c.drawString(6 * inch, y, f"${state['tax_amount']:.2f}")

            y -= 0.3 * inch
            c.line(5 * inch, y, 7 * inch, y)

            y -= 0.3 * inch
            c.setFont("Helvetica-Bold", 12)
            c.drawString(5 * inch, y, "Total:")
            c.drawString(6 * inch, y, f"${state['total']:.2f}")

            c.setFont("Helvetica", 9)
            c.drawString(1 * inch, 1.2 * inch, "Payment Terms: Net 30 days")
            c.drawString(1 * inch, 1 * inch, "Thank you for your business!")

            c.save()

            state["pdf_path"] = str(pdf_path)
            state["success"] = True

            self.invoice_counter += 1

            print(f"[InvoiceGenerator] PDF generated: {pdf_path}")

        except Exception as e:
            state["errors"].append(f"PDF generation error: {str(e)}")
            state["success"] = False
            print(f"[InvoiceGenerator] Error generating PDF: {e}")

        return state

    def _check_validation(self, state: InvoiceState) -> str:
        return "continue" if state["success"] and not state["errors"] else "error"

    def _check_fetch(self, state: InvoiceState) -> str:
        return "continue" if state["success"] and not state["errors"] else "error"

    async def generate_invoice(
        self, customer_name: str, customer_address: str, items: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
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
            "success": False,
        }

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
                "items": final_state["validated_items"],
            }
        else:
            return {
                "success": False,
                "errors": final_state["errors"],
                "current_step": final_state["current_step"],
            }

    async def process_query(self, request: QueryRequest) -> AgentResponse:
        metadata = request.metadata or {}
        invoice_state = metadata.get("invoice_state", {})
        step = invoice_state.get("step", "start")

        query_lower = request.query.lower()

        if step == "start":
            return AgentResponse(
                agent_name=self.name,
                response="I'll help you generate an invoice! Let's start with the customer details.\n\nWhat is the customer's name?",
                success=True,
                data={"invoice_state": {"step": "waiting_for_name", "collected": {}}},
            )

        elif step == "waiting_for_name":
            invoice_state["collected"]["customer_name"] = request.query
            return AgentResponse(
                agent_name=self.name,
                response=f"Great! Customer name: {request.query}\n\nNow, what is the customer's address? (You can provide it in one line or multiple lines)",
                success=True,
                data={
                    "invoice_state": {
                        "step": "waiting_for_address",
                        "collected": invoice_state["collected"],
                    }
                },
            )

        elif step == "waiting_for_address":
            invoice_state["collected"]["customer_address"] = request.query
            return AgentResponse(
                agent_name=self.name,
                response=f"Perfect! Address saved.\n\nNow, let's add items to the invoice. Please provide items in this format:\n\nSKU: quantity\n\nFor example:\n- PP-ROPE-001: 100\n- NY-BAG-001: 50\n- CLIP-001: 20\n- HOOK-001: 10\n\nYou can provide one item per message, or multiple items separated by commas or new lines. Type 'done' when you're finished adding items.",
                success=True,
                data={
                    "invoice_state": {
                        "step": "waiting_for_items",
                        "collected": invoice_state["collected"],
                    }
                },
            )

        elif step == "waiting_for_items":
            if "items" not in invoice_state["collected"]:
                invoice_state["collected"]["items"] = []

            if query_lower.strip() in [
                "done",
                "finish",
                "complete",
                "generate",
                "that's all",
                "thats all",
            ]:
                if len(invoice_state["collected"]["items"]) == 0:
                    return AgentResponse(
                        agent_name=self.name,
                        response="You haven't added any items yet. Please add at least one item, or type 'cancel' to start over.",
                        success=True,
                        data={
                            "invoice_state": {
                                "step": "waiting_for_items",
                                "collected": invoice_state["collected"],
                            }
                        },
                    )

                return await self._finalize_invoice(invoice_state["collected"])

            if query_lower.strip() in ["cancel", "stop", "abort"]:
                return AgentResponse(
                    agent_name=self.name,
                    response="Invoice generation cancelled. Type 'generate invoice' if you want to start over.",
                    success=True,
                    data={"invoice_state": {"step": "start", "collected": {}}},
                )

            parsed_items = self._parse_items_from_text(request.query)

            if not parsed_items:
                return AgentResponse(
                    agent_name=self.name,
                    response="I couldn't understand that format. Please provide items like:\n\nPP-ROPE-001: 100 or CLIP-001: 20 or NY-BAG-001: 50\n\nOr type 'done' if you're finished adding items.",
                    success=True,
                    data={
                        "invoice_state": {
                            "step": "waiting_for_items",
                            "collected": invoice_state["collected"],
                        }
                    },
                )

            invoice_state["collected"]["items"].extend(parsed_items)

            items_summary = "\n".join(
                [
                    f"  - {item['sku']}: {item['quantity']} units"
                    for item in invoice_state["collected"]["items"]
                ]
            )

            return AgentResponse(
                agent_name=self.name,
                response=f"Items added!\n\nCurrent items:\n{items_summary}\n\nAdd more items, or type 'done' to generate the invoice.",
                success=True,
                data={
                    "invoice_state": {
                        "step": "waiting_for_items",
                        "collected": invoice_state["collected"],
                    }
                },
            )

        else:
            return AgentResponse(
                agent_name=self.name,
                response="I'll help you generate an invoice! Let's start with the customer details.\n\nWhat is the customer's name?",
                success=True,
                data={"invoice_state": {"step": "waiting_for_name", "collected": {}}},
            )

    def _parse_items_from_text(self, text: str) -> List[Dict[str, Any]]:
        import re

        items = []

        patterns = [
            r"(?<![A-Z-])([A-Z]{2,10}-[A-Z]{2,10}-\d{1,5})\s*[:,-]\s*(\d+)(?!\d)",
            r"(?<![A-Z-])([A-Z]{2,10}-\d{1,5})\s*[:,-]\s*(\d+)(?!\d)",
            r"(?<![A-Z-])([A-Z]{2,10}-[A-Z]{2,10}-\d{1,5})\s+(\d+)(?!\d)",
            r"(?<![A-Z-])([A-Z]{2,10}-\d{1,5})\s+(\d+)(?!\d)",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for sku, quantity in matches:
                if not any(item["sku"] == sku.upper() for item in items):
                    items.append({"sku": sku.upper(), "quantity": int(quantity)})

        return items

    async def _finalize_invoice(self, collected_data: Dict[str, Any]) -> AgentResponse:
        try:
            result = await self.generate_invoice(
                customer_name=collected_data["customer_name"],
                customer_address=collected_data["customer_address"],
                items=collected_data["items"],
            )

            if result["success"]:
                items_summary = "\n".join(
                    [
                        f"  - {item['name']}: {item['quantity']} x ${item['unit_price']:.2f} = ${item['line_total']:.2f}"
                        for item in result["items"]
                    ]
                )

                response_text = f"""Invoice Generated Successfully!

Invoice Number: {result["invoice_number"]}
Date: {result["invoice_date"]}
Customer: {collected_data["customer_name"]}

Items:
{items_summary}

Subtotal: ${result["subtotal"]:.2f}
"""
                if result["discount"] > 0:
                    response_text += f"Discount: -${result['discount']:.2f}\n"

                response_text += f"""Tax: ${result["tax"]:.2f}
Total: ${result["total"]:.2f}

PDF saved to: {result["pdf_path"]}

The invoice has been generated and saved. You can download it using the invoice number: {result["invoice_number"]}"""

                return AgentResponse(
                    agent_name=self.name,
                    response=response_text,
                    success=True,
                    data={
                        "invoice_state": {"step": "start", "collected": {}},
                        "invoice_result": result,
                    },
                )
            else:
                error_text = "\n".join([f"  - {err}" for err in result["errors"]])
                return AgentResponse(
                    agent_name=self.name,
                    response=f"Invoice generation failed:\n\n{error_text}\n\nPlease try again by typing 'generate invoice'.",
                    success=False,
                    data={"invoice_state": {"step": "start", "collected": {}}},
                )

        except Exception as e:
            import traceback

            traceback.print_exc()
            return AgentResponse(
                agent_name=self.name,
                response=f"Error generating invoice: {str(e)}\n\nPlease try again by typing 'generate invoice'.",
                success=False,
                data={"invoice_state": {"step": "start", "collected": {}}},
            )
