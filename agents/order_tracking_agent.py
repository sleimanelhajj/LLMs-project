"""
Order Tracking Agent - Handles order tracking and order history queries.

This agent provides two tools:
1. track_order - Track order status by order ID or customer email
2. get_order_history - Retrieve past orders for a customer
"""

import sqlite3
from typing import Optional
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain.agents import create_agent
from agents.base_agent import BaseAgent
from models.schemas import QueryRequest, AgentResponse
from config import CATALOG_DB_PATH, GOOGLE_API_KEY


class OrderTrackingAgent(BaseAgent):
    """Agent for tracking orders and retrieving order history."""
    
    def __init__(self):
        super().__init__(
            name="OrderTrackingAgent",
            description="Tracks order status and retrieves order history for customers"
        )
        self.db_path = CATALOG_DB_PATH
        self._setup_agent()
    
    def _get_db_connection(self):
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
  
    def can_handle(self, query: str) -> bool:
        return True
    
    def _setup_agent(self):
        """Set up the LangChain agent with tools."""
        
        @tool
        def track_order(identifier: str) -> str:
            """
            Track an order by order ID or customer email.
            
            Args:
                identifier: Either an order ID (e.g., 'ORD-2024-0001') or customer email
                
            Returns:
                Order status information including current location and estimated delivery
            """
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            try:
                # Check if identifier is an order ID or email
                if identifier.upper().startswith('ORD-') or identifier.upper().startswith('TRK'):
                    # Search by order ID or tracking number
                    cursor.execute("""
                        SELECT o.order_id, o.tracking_number, o.status, o.current_location,
                               o.estimated_delivery, o.order_date, o.total_amount, o.currency,
                               o.shipping_address, o.shipping_city, o.shipping_country,
                               c.name as customer_name, c.email, c.company
                        FROM orders o
                        JOIN customers c ON o.customer_id = c.customer_id
                        WHERE UPPER(o.order_id) = UPPER(?) OR UPPER(o.tracking_number) = UPPER(?)
                    """, (identifier, identifier))
                else:
                    # Search by email - get the most recent order
                    cursor.execute("""
                        SELECT o.order_id, o.tracking_number, o.status, o.current_location,
                               o.estimated_delivery, o.order_date, o.total_amount, o.currency,
                               o.shipping_address, o.shipping_city, o.shipping_country,
                               c.name as customer_name, c.email, c.company
                        FROM orders o
                        JOIN customers c ON o.customer_id = c.customer_id
                        WHERE LOWER(c.email) = LOWER(?)
                        ORDER BY o.order_date DESC
                        LIMIT 1
                    """, (identifier,))
                
                order = cursor.fetchone()
                
                if not order:
                    return f"No order found for '{identifier}'. Please check the order ID or email and try again."
                
                # Get order items
                cursor.execute("""
                    SELECT product_name, quantity, unit_price, total_price
                    FROM order_items
                    WHERE order_id = ?
                """, (order['order_id'],))
                items = cursor.fetchall()
                
                # Format status with emoji
                status_emoji = {
                    'pending': '⏳',
                    'confirmed': '✅',
                    'processing': '🔄',
                    'shipped': '📦',
                    'in_transit': '🚚',
                    'out_for_delivery': '🏃',
                    'delivered': '✅',
                    'cancelled': '❌'
                }
                
                emoji = status_emoji.get(order['status'], '📋')
                
                result = f"""
📦 **Order Tracking Information**

**Order ID:** {order['order_id']}
**Tracking Number:** {order['tracking_number'] or 'Not yet assigned'}
**Status:** {emoji} {order['status'].replace('_', ' ').title()}
**Current Location:** {order['current_location']}
**Estimated Delivery:** {order['estimated_delivery']}

**Customer:** {order['customer_name']} ({order['company']})
**Email:** {order['email']}

**Shipping To:**
{order['shipping_address']}
{order['shipping_city']}, {order['shipping_country']}

**Order Items:**
"""
                for item in items:
                    result += f"  • {item['product_name']} x{item['quantity']} - ${item['total_price']:.2f}\n"
                
                result += f"\n**Total Amount:** ${order['total_amount']:.2f} {order['currency']}"
                result += f"\n**Order Date:** {order['order_date']}"
                
                return result
                
            except Exception as e:
                return f"Error tracking order: {str(e)}"
            finally:
                conn.close()
        
        @tool
        def get_order_history(
            customer_identifier: str,
            status_filter: Optional[str] = None,
            limit: int = 10
        ) -> str:
            """
            Retrieve order history for a customer.
            
            Args:
                customer_identifier: Customer email or customer ID
                status_filter: Optional filter by status (pending, confirmed, processing, shipped, in_transit, out_for_delivery, delivered, cancelled)
                limit: Maximum number of orders to return (default 10)
                
            Returns:
                List of past orders with dates, items, totals, and status
            """
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            try:
                # First, find the customer
                cursor.execute("""
                    SELECT customer_id, name, email, company
                    FROM customers
                    WHERE LOWER(email) = LOWER(?) OR UPPER(customer_id) = UPPER(?)
                """, (customer_identifier, customer_identifier))
                
                customer = cursor.fetchone()
                
                if not customer:
                    return f"No customer found with identifier '{customer_identifier}'. Please provide a valid email or customer ID."
                
                # Build query for orders
                query = """
                    SELECT order_id, order_date, status, total_amount, currency,
                           tracking_number, current_location, estimated_delivery
                    FROM orders
                    WHERE customer_id = ?
                """
                params = [customer['customer_id']]
                
                if status_filter:
                    query += " AND LOWER(status) = LOWER(?)"
                    params.append(status_filter)
                
                query += " ORDER BY order_date DESC LIMIT ?"
                params.append(limit)
                
                cursor.execute(query, params)
                orders = cursor.fetchall()
                
                if not orders:
                    filter_msg = f" with status '{status_filter}'" if status_filter else ""
                    return f"No orders found{filter_msg} for customer {customer['name']}."
                
                # Format status with emoji
                status_emoji = {
                    'pending': '⏳',
                    'confirmed': '✅',
                    'processing': '🔄',
                    'shipped': '📦',
                    'in_transit': '🚚',
                    'out_for_delivery': '🏃',
                    'delivered': '✅',
                    'cancelled': '❌'
                }
                
                result = f"""
📋 **Order History for {customer['name']}**
**Company:** {customer['company']}
**Email:** {customer['email']}

"""
                # Calculate summary stats
                total_orders = len(orders)
                total_spent = sum(order['total_amount'] for order in orders)
                
                result += f"**Summary:** {total_orders} orders | Total spent: ${total_spent:.2f}\n\n"
                result += "---\n\n"
                
                for order in orders:
                    emoji = status_emoji.get(order['status'], '📋')
                    
                    # Get items for this order
                    cursor.execute("""
                        SELECT product_name, quantity, total_price
                        FROM order_items
                        WHERE order_id = ?
                    """, (order['order_id'],))
                    items = cursor.fetchall()
                    
                    result += f"**{order['order_id']}** - {order['order_date'][:10]}\n"
                    result += f"Status: {emoji} {order['status'].replace('_', ' ').title()}\n"
                    
                    if order['tracking_number']:
                        result += f"Tracking: {order['tracking_number']}\n"
                    
                    result += "Items:\n"
                    for item in items:
                        result += f"  • {item['product_name']} x{item['quantity']} - ${item['total_price']:.2f}\n"
                    
                    result += f"**Total: ${order['total_amount']:.2f} {order['currency']}**\n\n"
                
                return result
                
            except Exception as e:
                return f"Error retrieving order history: {str(e)}"
            finally:
                conn.close()
        
        # Store tools
        self.tools = [track_order, get_order_history]
        
        # Create the LLM
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=GOOGLE_API_KEY,
            temperature=0.3
        )
        
        # System prompt for the agent
        system_prompt = """You are an Order Tracking Assistant for a warehouse supply company.

Your role is to help customers and employees track orders and view order history.

You have access to two tools:
1. **track_order**: Use this to track a specific order by order ID, tracking number, or customer email
2. **get_order_history**: Use this to retrieve the order history for a customer

When users ask about:
- "Where is my order?" or "Track order X" → Use track_order
- "What orders do I have?" or "Show my order history" → Use get_order_history
- Order status, delivery date, tracking → Use track_order
- Past purchases, previous orders → Use get_order_history

Always be helpful and provide clear, formatted responses."""
        
        # Create agent using langchain
        self.agent = create_agent(llm, self.tools, system_prompt=system_prompt)
    
    async def process(self, query: str, context: dict = None) -> dict:
        """
        Process an order tracking query.
        
        Args:
            query: The user's query about order tracking
            context: Optional context with chat history
            
        Returns:
            dict with response and metadata
        """
        try:
            # Invoke the agent with messages format
            result = await self.agent.ainvoke({
                "messages": [{"role": "user", "content": query}]
            })
            
            # Extract the output from messages
            messages = result.get("messages", [])
            if messages:
                last_message = messages[-1]
                response = last_message.content if hasattr(last_message, 'content') else str(last_message)
            else:
                response = "I couldn't process your order tracking request."
            
            return {
                "success": True,
                "response": response,
                "agent": self.name,
                "tools_used": ["track_order", "get_order_history"]
            }
            
        except Exception as e:
            print(f"[OrderTrackingAgent] Error: {str(e)}")
            return {
                "success": False,
                "response": f"I encountered an error while tracking your order: {str(e)}",
                "agent": self.name,
                "error": str(e)
            }
    
    async def process_query(self, request: QueryRequest) -> AgentResponse:
        """Process an order tracking query - required by BaseAgent."""
        result = await self.process(request.query)
        return AgentResponse(
            agent_name=self.name,
            response=result.get("response", ""),
            success=result.get("success", False),
            data=result
        )


# For testing
if __name__ == "__main__":
    import asyncio
    
    async def test_agent():
        agent = OrderTrackingAgent()
        
        # Test tracking by email
        print("\n=== Test 1: Track by Email ===")
        result = await agent.process("Track my order. My email is john.smith@email.com")
        print(result["response"])
        
        # Test order history
        print("\n=== Test 2: Order History ===")
        result = await agent.process("Show me the order history for sarah.j@techcorp.com")
        print(result["response"])
    
    asyncio.run(test_agent())
