"""
Product Catalog Tools
Tools for searching products, getting product details, and listing categories.
"""

from typing import Optional
from langchain_core.tools import tool
from tools.utils.db_utils import get_db_connection


@tool
def search_products(query: str, category: Optional[str] = None) -> str:
    """
    Search for products in the catalog by name, description, or category.

    Args:
        query: Search term (product name, material, description keywords)
        category: Optional category filter (Ropes, Wire, Bags, Safety, Hardware, Packaging)

    Returns:
        List of matching products with details
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        search_term = f"%{query}%"

        if category:
            cursor.execute(
                """
                SELECT sku, name, category, description, material, 
                       diameter_mm, unit, unit_price, quantity_on_hand
                FROM products
                WHERE (name LIKE ? OR description LIKE ? OR material LIKE ?)
                AND LOWER(category) = LOWER(?)
                ORDER BY name
                LIMIT 10
            """,
                (search_term, search_term, search_term, category),
            )
        else:
            cursor.execute(
                """
                SELECT sku, name, category, description, material,
                       diameter_mm, unit, unit_price, quantity_on_hand
                FROM products
                WHERE name LIKE ? OR description LIKE ? OR material LIKE ? OR category LIKE ?
                ORDER BY name
                LIMIT 10
            """,
                (search_term, search_term, search_term, search_term),
            )

        products = cursor.fetchall()

        if not products:
            return f"No products found matching '{query}'" + (
                f" in category '{category}'" if category else ""
            )

        result = f"Found {len(products)} products:\n\n"
        for p in products:
            result += f"{p['name']} (SKU: {p['sku']})\n"
            result += f"  Category: {p['category']}\n"
            if p["description"]:
                result += f"  Description: {p['description']}\n"
            if p["material"]:
                result += f"  Material: {p['material']}\n"
            if p["diameter_mm"]:
                result += f"  Diameter: {p['diameter_mm']}mm\n"
            result += f"  Price: ${p['unit_price']:.2f}/{p['unit']}\n"
            result += f"  In Stock: {p['quantity_on_hand']} {p['unit']}s\n\n"

        return result

    finally:
        conn.close()


@tool
def get_product_by_sku(sku: str) -> str:
    """
    Get detailed information about a specific product by its SKU.

    Args:
        sku: Product SKU code (e.g., 'PP-ROPE-12MM')

    Returns:
        Detailed product information
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute(
            """
            SELECT * FROM products WHERE UPPER(sku) = UPPER(?)
        """,
            (sku,),
        )

        product = cursor.fetchone()

        if not product:
            return f"No product found with SKU '{sku}'"

        result = f"{product['name']}\n"
        result += f"SKU: {product['sku']}\n"
        result += f"Category: {product['category']}\n"
        if product["description"]:
            result += f"Description: {product['description']}\n"
        if product["material"]:
            result += f"Material: {product['material']}\n"
        if product["diameter_mm"]:
            result += f"Diameter: {product['diameter_mm']}mm\n"
        if product["weight_kg"]:
            result += f"Weight: {product['weight_kg']}kg\n"
        if product["breaking_strength"]:
            result += f"Breaking Strength: {product['breaking_strength']}\n"
        result += f"Price: ${product['unit_price']:.2f}/{product['unit']}\n"
        result += f"In Stock: {product['quantity_on_hand']} units\n"
        result += f"Min Order Qty: {product['min_order_qty']}\n"
        result += f"Lead Time: {product['lead_time_days']} days\n"

        return result

    finally:
        conn.close()


@tool
def list_categories() -> str:
    """
    List all available product categories with product counts.

    Returns:
        List of categories with the number of products in each
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        cursor.execute("""
            SELECT category, COUNT(*) as count, 
                   SUM(quantity_on_hand) as total_stock
            FROM products
            GROUP BY category
            ORDER BY category
        """)

        categories = cursor.fetchall()

        result = "Product Categories:\n\n"
        for cat in categories:
            result += f"• {cat['category']}: {cat['count']} products ({cat['total_stock']:,} units in stock)\n"

        return result

    finally:
        conn.close()
