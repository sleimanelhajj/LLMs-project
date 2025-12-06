"""
Sales Report Tools
Tools for generating sales summaries and reports.
"""

from datetime import datetime, timedelta
from langchain_core.tools import tool

from tools.utils.db_utils import get_db_connection
from tools.utils.html_utils import generate_html_table


@tool
def get_sales_summary(period: str = "30days") -> str:
    """
    Get a summary of sales performance.

    Args:
        period: Time period - "7days", "30days", "90days", or "all"

    Returns:
        Sales summary with revenue, orders, and top products/customers as HTML.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        # Most recent order date as reference
        cursor.execute("SELECT MAX(order_date) FROM orders")
        max_date_result = cursor.fetchone()

        if max_date_result and max_date_result[0]:
            reference_date = datetime.strptime(max_date_result[0][:10], "%Y-%m-%d")
        else:
            reference_date = datetime.now()

        if period == "7days":
            start_date = reference_date - timedelta(days=7)
            period_label = "Last 7 Days"
        elif period == "30days":
            start_date = reference_date - timedelta(days=30)
            period_label = "Last 30 Days"
        elif period == "90days":
            start_date = reference_date - timedelta(days=90)
            period_label = "Last 90 Days"
        else:
            start_date = reference_date - timedelta(days=365)
            period_label = "All Time"

        start_date_str = start_date.strftime("%Y-%m-%d")

        # Summary stats
        cursor.execute(
            """
            SELECT 
                COUNT(*) as total_orders,
                SUM(total_amount) as total_revenue,
                AVG(total_amount) as avg_order
            FROM orders
            WHERE order_date >= ?
            """,
            (start_date_str,),
        )
        summary = cursor.fetchone() or {}
        
        # Debug logging
        print(f"[SALES TOOL] Period: {period}, Start Date: {start_date_str}")
        print(f"[SALES TOOL] Summary results: {summary}")

        # Top products
        cursor.execute(
            """
            SELECT oi.product_name, SUM(oi.quantity) as qty, SUM(oi.total_price) as revenue
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.order_id
            WHERE o.order_date >= ?
            GROUP BY oi.product_name
            ORDER BY revenue DESC
            LIMIT 5
            """,
            (start_date_str,),
        )
        top_products = cursor.fetchall() or []
        
        print(f"[SALES TOOL] Top products count: {len(top_products)}")

        # Top customers
        cursor.execute(
            """
            SELECT c.name, c.company, SUM(o.total_amount) as spent
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            WHERE o.order_date >= ?
            GROUP BY c.customer_id, c.name, c.company
            ORDER BY spent DESC
            LIMIT 5
            """,
            (start_date_str,),
        )
        top_customers = cursor.fetchall() or []
        
        print(f"[SALES TOOL] Top customers count: {len(top_customers)}")

        # Build HTML response (no newlines, use <br> sparingly)
        result = f"<strong>📈 Sales Summary ({period_label})</strong><br><br>"
        result += f"<strong>Total Orders:</strong> {summary['total_orders'] or 0}<br>"
        result += f"<strong>Total Revenue:</strong> ${(summary['total_revenue'] or 0):,.2f}<br>"
        result += f"<strong>Avg Order Value:</strong> ${(summary['avg_order'] or 0):,.2f}<br><br>"

        if top_products:
            result += "<strong>Top 5 Products:</strong>"
            product_rows = [
                [p["product_name"], p["qty"], f"${p['revenue']:,.2f}"]
                for p in top_products
            ]
            result += generate_html_table(
                ["Product", "Qty Sold", "Revenue"],
                product_rows,
            )

        if top_customers:
            result += "<br><strong>Top 5 Customers:</strong>"
            customer_rows = [
                [c["name"], c["company"], f"${c['spent']:,.2f}"] for c in top_customers
            ]
            result += generate_html_table(
                ["Name", "Company", "Total Spent"],
                customer_rows,
            )
        
        print(f"[SALES TOOL] Final result length: {len(result)} chars")
        print(f"[SALES TOOL] Result preview: {result[:200]}...")
        return result

    finally:
        conn.close()
