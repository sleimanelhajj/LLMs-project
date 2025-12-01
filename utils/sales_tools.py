"""
Sales Report Tools

Tools for generating sales summaries and reports.
"""

from datetime import datetime, timedelta
from langchain_core.tools import tool
from utils.db_utils import get_db_connection


@tool
def get_sales_summary(period: str = "30days") -> str:
    """
    Get a summary of sales performance.

    Args:
        period: Time period - "7days", "30days", "90days", or "all"

    Returns:
        Sales summary with revenue, orders, and top products
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        now = datetime.now()
        if period == "7days":
            start_date = now - timedelta(days=7)
            period_label = "Last 7 Days"
        elif period == "30days":
            start_date = now - timedelta(days=30)
            period_label = "Last 30 Days"
        elif period == "90days":
            start_date = now - timedelta(days=90)
            period_label = "Last 90 Days"
        else:
            start_date = now - timedelta(days=365)
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

        summary = cursor.fetchone()

        # Top products
        cursor.execute(
            """
            SELECT oi.product_name, SUM(oi.quantity) as qty, SUM(oi.total_price) as revenue
            FROM order_items oi
            JOIN orders o ON oi.order_id = o.order_id
            WHERE o.order_date >= ?
            GROUP BY oi.product_sku
            ORDER BY revenue DESC
            LIMIT 5
        """,
            (start_date_str,),
        )

        top_products = cursor.fetchall()

        # Top customers
        cursor.execute(
            """
            SELECT c.name, c.company, SUM(o.total_amount) as spent
            FROM orders o
            JOIN customers c ON o.customer_id = c.customer_id
            WHERE o.order_date >= ?
            GROUP BY c.customer_id
            ORDER BY spent DESC
            LIMIT 5
        """,
            (start_date_str,),
        )

        top_customers = cursor.fetchall()

        result = f"**📈 Sales Summary ({period_label})**\n\n"
        result += f"**Total Orders:** {summary['total_orders'] or 0}\n"
        result += f"**Total Revenue:** ${(summary['total_revenue'] or 0):,.2f}\n"
        result += f"**Avg Order Value:** ${(summary['avg_order'] or 0):,.2f}\n\n"

        if top_products:
            result += "**Top 5 Products:**\n"
            for p in top_products:
                result += (
                    f"  • {p['product_name']}: {p['qty']} sold - ${p['revenue']:,.2f}\n"
                )
            result += "\n"

        if top_customers:
            result += "**Top 5 Customers:**\n"
            for c in top_customers:
                result += f"  • {c['name']} ({c['company']}): ${c['spent']:,.2f}\n"

        return result

    finally:
        conn.close()
