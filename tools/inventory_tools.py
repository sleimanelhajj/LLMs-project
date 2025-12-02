"""
Inventory Tools

Tools for checking inventory levels and getting inventory summaries.
"""

from typing import Optional
from langchain_core.tools import tool
from tools.utils.db_utils import get_db_connection
from tools.utils.html_utils import generate_html_table


@tool
def check_inventory(
    category: Optional[str] = None, low_stock_only: bool = False
) -> str:
    """
    Check inventory levels across products.

    Args:
        category: Optional category filterf
        low_stock_only: If True, only show items with less than 100 units

    Returns:
        Inventory summary with stock levels
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        query = """
            SELECT sku, name, category, quantity_on_hand, unit_price,
                   (quantity_on_hand * unit_price) as stock_value
            FROM products
        """
        params = []
        conditions = []

        if category:
            conditions.append("LOWER(category) = LOWER(?)")
            params.append(category)

        if low_stock_only:
            conditions.append("quantity_on_hand < 100")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY quantity_on_hand ASC LIMIT 15"

        cursor.execute(query, params)
        products = cursor.fetchall()

        if not products:
            return "No products found matching criteria"

        result = "Inventory Status\n\n"
        if low_stock_only:
            result += "LOW STOCK ITEMS (< 100 units)\n\n"

        total_value = 0
        for p in products:
            status = (
                "CRITICAL"
                if p["quantity_on_hand"] < 50
                else "LOW"
                if p["quantity_on_hand"] < 100
                else "OK"
            )
            result += f"{p['name']} ({p['sku']})\n"
            result += f"  Stock: {p['quantity_on_hand']} units - {status}\n"
            result += f"  Value: ${p['stock_value']:,.2f}\n\n"
            total_value += p["stock_value"]

        result += f"---\nTotal Value Shown: ${total_value:,.2f}"

        return result

    finally:
        conn.close()


@tool
def get_inventory_summary() -> str:
    """
    Get an inventory summary by category as an HTML table.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT 
                category,
                COUNT(DISTINCT sku) AS products,
                SUM(quantity_on_hand) AS units,
                SUM(quantity_on_hand * unit_price) AS value
            FROM products
            GROUP BY category
            ORDER BY category
            """
        )
        rows = cursor.fetchall()

        total_products = sum(r["products"] for r in rows)
        total_units = sum(r["units"] for r in rows)
        total_value = sum(r["value"] for r in rows)

        table_rows = [
            [
                r["category"],
                r["products"],
                r["units"],
                f"${r['value']:,.2f}",
            ]
            for r in rows
        ]

        # Add a total row
        table_rows.append(
            [
                "TOTAL",
                total_products,
                total_units,
                f"${total_value:,.2f}",
            ]
        )

        result = "Here's a summary of our inventory:<br><br>"
        result += "<strong>Inventory Summary by Category</strong>"
        result += generate_html_table(
            headers=["Category", "Products", "Units", "Value"],
            rows=table_rows,
        )

        return result

    finally:
        conn.close()
