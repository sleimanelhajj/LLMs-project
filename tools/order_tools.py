"""
Order Tracking Tools
Tools for tracking orders and viewing order history.
"""

from langchain_core.tools import tool
from tools.utils.db_utils import get_db_connection
from tools.utils.html_utils import generate_html_table


@tool
def track_order(identifier: str) -> str:
    """
    Track an order by order ID, tracking number, or customer email.

    Args:
        identifier: Order ID (e.g., 'ORD-2024-0001'), tracking number, or customer email

    Returns:
        Order status and tracking information
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Check if identifier is an order ID/tracking number or email
        if identifier.upper().startswith("ORD-") or identifier.upper().startswith(
            "TRK"
        ):
            cursor.execute(
                """
                SELECT o.*, c.name as customer_name, c.email, c.company
                FROM orders o
                JOIN customers c ON o.customer_id = c.customer_id
                WHERE UPPER(o.order_id) = UPPER(?) OR UPPER(o.tracking_number) = UPPER(?)
            """,
                (identifier, identifier),
            )
        else:
            # Search by email - get the most recent order
            cursor.execute(
                """
                SELECT o.*, c.name as customer_name, c.email, c.company
                FROM orders o
                JOIN customers c ON o.customer_id = c.customer_id
                WHERE LOWER(c.email) = LOWER(?)
                ORDER BY o.order_date DESC
                LIMIT 1
            """,
                (identifier,),
            )

        order = cursor.fetchone()

        if not order:
            return f"No order found for '{identifier}'. Please check the order ID or email."

        # Get order items
        cursor.execute(
            """
            SELECT product_name, quantity, unit_price, total_price
            FROM order_items WHERE order_id = ?
        """,
            (order["order_id"],),
        )
        items = cursor.fetchall()

        # Build status text without emojis
        status_text = order["status"].replace("_", " ").title()

        # Build HTML instead of markdown
        result = "<strong>Order Tracking</strong><br><br>"
        result += f"<strong>Order ID:</strong> {order['order_id']}<br>"
        result += f"<strong>Tracking:</strong> {order['tracking_number'] or 'Not yet assigned'}<br>"
        result += f"<strong>Status:</strong> {status_text}<br>"
        result += f"<strong>Location:</strong> {order['current_location']}<br>"
        result += (
            f"<strong>Est. Delivery:</strong> {order['estimated_delivery']}<br><br>"
        )
        result += f"<strong>Customer:</strong> {order['customer_name']} ({order['company']})<br>"
        result += f"<strong>Ship To:</strong> {order['shipping_address']}, {order['shipping_city']}<br><br>"
        result += "<strong>Items:</strong><br>"

        # Use shared HTML table generator for items
        item_rows = [
            [
                item["product_name"],
                item["quantity"],
                f"${item['unit_price']:.2f}",
                f"${item['total_price']:.2f}",
            ]
            for item in items
        ]
        if item_rows:
            result += generate_html_table(
                ["Product", "Qty", "Unit Price", "Total"], item_rows
            )
        else:
            result += "No items found for this order."

        result += f"<br><br><strong>Total:</strong> ${order['total_amount']:.2f}"

        return result

    finally:
        conn.close()


@tool
def get_order_history(customer_email: str, limit: int = 5) -> str:
    """
    Get order history for a customer by their email.

    Args:
        customer_email: Customer's email address
        limit: Maximum number of orders to return (default 5)

    Returns:
        List of past orders with status and totals
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT c.customer_id, c.name, c.company
            FROM customers c
            WHERE LOWER(c.email) = LOWER(?)
        """,
            (customer_email,),
        )

        customer = cursor.fetchone()
        if not customer:
            return f"No customer found with email '{customer_email}'"

        cursor.execute(
            """
            SELECT order_id, order_date, status, total_amount, tracking_number
            FROM orders
            WHERE customer_id = ?
            ORDER BY order_date DESC
            LIMIT ?
        """,
            (customer["customer_id"], limit),
        )

        orders = cursor.fetchall()

        if not orders:
            return f"No orders found for {customer['name']}"

        # Build HTML response
        result = f"<strong>Order History for {customer['name']}</strong> ({customer['company']})<br><br>"

        total_spent = sum(o["total_amount"] for o in orders)
        result += f"<strong>Total:</strong> {len(orders)} orders | ${total_spent:,.2f} spent<br><br>"

        # Build table data for orders without emojis, using shared table generator
        table_data = []
        for order in orders:
            status_display = order["status"].replace("_", " ").title()
            table_data.append(
                [
                    order["order_id"],
                    order["order_date"][:10],
                    status_display,
                    f"${order['total_amount']:.2f}",
                ]
            )

        result += generate_html_table(
            ["Order ID", "Date", "Status", "Total"], table_data
        )

        return result

    finally:
        conn.close()
