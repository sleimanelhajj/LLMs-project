"""
LangGraph Agent for Invoice Processing

This agent handles complex invoice generation workflows using LangGraph.
It communicates with other agents via A2A protocol and uses MCP tools.
"""

import asyncio
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
from dataclasses import dataclass

# Placeholder for LangGraph imports (will be added after dependencies are installed)
# from langgraph.graph import Graph, StateGraph
# from langgraph.prebuilt import ToolNode

@dataclass
class InvoiceState:
    """State for the invoice generation workflow."""
    customer_info: Optional[Dict[str, Any]] = None
    items: Optional[List[Dict[str, Any]]] = None
    totals: Optional[Dict[str, float]] = None
    invoice_id: Optional[str] = None
    html_content: Optional[str] = None
    file_path: Optional[str] = None
    errors: Optional[List[str]] = None
    step: str = "start"


class LangGraphInvoiceAgent:
    """LangGraph-based agent for invoice processing."""
    
    def __init__(self, mcp_client=None):
        self.mcp_client = mcp_client
        self.workflow = None
        self._build_workflow()
    
    def _build_workflow(self):
        """Build the LangGraph workflow for invoice processing."""
        # This is a placeholder for the LangGraph workflow
        # In a full implementation, this would create the actual graph
        print("LangGraph workflow initialized (placeholder)")
    
    async def process_invoice_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process an invoice generation request."""
        try:
            # Initialize state
            state = InvoiceState(
                customer_info=request_data.get("customer"),
                items=request_data.get("items", []),
                step="validate_input"
            )
            
            # Execute workflow steps
            state = await self._validate_input(state)
            if state.errors:
                return {"success": False, "errors": state.errors}
            
            state = await self._calculate_totals(state)
            if state.errors:
                return {"success": False, "errors": state.errors}
            
            state = await self._generate_invoice_html(state)
            if state.errors:
                return {"success": False, "errors": state.errors}
            
            return {
                "success": True,
                "invoice_id": state.invoice_id,
                "file_path": state.file_path,
                "totals": state.totals
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def _validate_input(self, state: InvoiceState) -> InvoiceState:
        """Validate input data for invoice generation."""
        errors = []
        
        # Validate customer info
        if not state.customer_info:
            errors.append("Customer information is required")
        else:
            required_fields = ["name", "email", "address"]
            for field in required_fields:
                if field not in state.customer_info:
                    errors.append(f"Customer {field} is required")
        
        # Validate items
        if not state.items:
            errors.append("At least one item is required")
        else:
            for i, item in enumerate(state.items):
                if "sku" not in item:
                    errors.append(f"Item {i+1}: SKU is required")
                if "quantity" not in item or item["quantity"] <= 0:
                    errors.append(f"Item {i+1}: Valid quantity is required")
        
        state.errors = errors if errors else None
        state.step = "input_validated" if not errors else "validation_failed"
        return state
    
    async def _calculate_totals(self, state: InvoiceState) -> InvoiceState:
        """Calculate totals for the invoice."""
        try:
            subtotal = 0.0
            updated_items = []
            
            for item in state.items:
                # Get product info from database via MCP
                if self.mcp_client:
                    product_result = await self.mcp_client.call_tool(
                        "kb_sql",
                        {"query": f"SELECT * FROM products WHERE sku = '{item['sku']}'"}
                    )
                    
                    if product_result.get("success") and product_result.get("results"):
                        product = product_result["results"][0]
                        unit_price = product["unit_price"]
                    else:
                        # Fallback if MCP not available
                        unit_price = item.get("unit_price", 0.0)
                else:
                    unit_price = item.get("unit_price", 0.0)
                
                quantity = item["quantity"]
                total_price = unit_price * quantity
                subtotal += total_price
                
                updated_items.append({
                    **item,
                    "unit_price": unit_price,
                    "total_price": total_price
                })
            
            # Calculate tax (8.25% for example)
            tax_rate = 0.0825
            tax = subtotal * tax_rate
            total = subtotal + tax
            
            state.items = updated_items
            state.totals = {
                "subtotal": round(subtotal, 2),
                "tax": round(tax, 2),
                "total": round(total, 2)
            }
            state.step = "totals_calculated"
            
        except Exception as e:
            state.errors = [f"Error calculating totals: {str(e)}"]
            state.step = "calculation_failed"
        
        return state
    
    async def _generate_invoice_html(self, state: InvoiceState) -> InvoiceState:
        """Generate HTML invoice using MCP tool."""
        try:
            # Generate unique invoice ID
            state.invoice_id = f"INV-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            
            # Prepare invoice data for template
            invoice_data = {
                "invoice_id": state.invoice_id,
                "customer_name": state.customer_info["name"],
                "customer_email": state.customer_info["email"],
                "customer_address": state.customer_info["address"],
                "items": state.items,
                "subtotal": state.totals["subtotal"],
                "tax": state.totals["tax"],
                "total": state.totals["total"]
            }
            
            # Generate HTML via MCP
            if self.mcp_client:
                html_result = await self.mcp_client.call_tool(
                    "fill_invoice_html",
                    {"invoice_data": invoice_data}
                )
                
                if html_result.get("success"):
                    state.file_path = html_result["file_path"]
                    state.step = "invoice_generated"
                else:
                    state.errors = [f"Error generating HTML: {html_result.get('error')}"]
                    state.step = "generation_failed"
            else:
                # Fallback without MCP
                state.errors = ["MCP client not available for HTML generation"]
                state.step = "generation_failed"
            
        except Exception as e:
            state.errors = [f"Error generating invoice: {str(e)}"]
            state.step = "generation_failed"
        
        return state


class MockMCPClient:
    """Mock MCP client for testing without full MCP setup."""
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Mock tool calls."""
        if tool_name == "kb_sql":
            # Mock product data
            query = arguments.get("query", "")
            if "sku" in query:
                return {
                    "success": True,
                    "results": [{
                        "sku": "PP-ROPE-001",
                        "name": "Polypropylene Rope 8mm",
                        "unit_price": 2.50,
                        "currency": "USD"
                    }]
                }
        elif tool_name == "fill_invoice_html":
            return {
                "success": True,
                "invoice_id": arguments["invoice_data"]["invoice_id"],
                "file_path": f"/tmp/{arguments['invoice_data']['invoice_id']}.html"
            }
        
        return {"success": False, "error": "Mock tool not implemented"}


# A2A Server for LangGraph Agent
class A2AServer:
    """Agent-to-Agent communication server for LangGraph agent."""
    
    def __init__(self, host: str = "localhost", port: int = 8001):
        self.host = host
        self.port = port
        self.invoice_agent = LangGraphInvoiceAgent(MockMCPClient())
    
    async def handle_request(self, request_data: Dict[str, Any]) -> Dict[str, Any]:
        """Handle incoming A2A requests."""
        try:
            request_type = request_data.get("type")
            
            if request_type == "generate_invoice":
                return await self.invoice_agent.process_invoice_request(
                    request_data.get("data", {})
                )
            elif request_type == "health_check":
                return {"status": "healthy", "agent": "LangGraphInvoiceAgent"}
            else:
                return {"success": False, "error": f"Unknown request type: {request_type}"}
                
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def start(self):
        """Start the A2A server."""
        print(f"A2A Server starting on {self.host}:{self.port}")
        print("LangGraph Invoice Agent ready for A2A communication")
        
        # Placeholder for actual server implementation
        # In a full implementation, this would start FastAPI or similar
        while True:
            await asyncio.sleep(1)


if __name__ == "__main__":
    async def main():
        server = A2AServer()
        await server.start()
    
    asyncio.run(main())
