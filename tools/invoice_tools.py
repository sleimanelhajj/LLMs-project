"""
Invoice Generation Tools
Tools for generating PDF invoices.
"""

import os
from datetime import datetime
from pathlib import Path
from langchain_core.tools import tool
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
import httpx

from config import INVOICES_DIR
from tools.utils.db_utils import get_db_connection

# Ensure directory exists
os.makedirs(INVOICES_DIR, exist_ok=True)


def _get_next_invoice_number() -> str:
    """Get the next invoice number based on existing invoices."""
    existing = list(Path(INVOICES_DIR).glob("INV-*.pdf"))
    if not existing:
        return "INV-000001"
    
    numbers = []
    for f in existing:
        try:
            num = int(f.stem.split("-")[1])
            numbers.append(num)
        except Exception:
            pass
    
    next_num = max(numbers) + 1 if numbers else 1
    return f"INV-{next_num:06d}"


def _generate_invoice_pdf(invoice_number: str, customer_name: str, customer_email: str,
                          items: list, subtotal: float, tax: float, total: float, 
                          currency: str = "USD", exchange_rate: float = 1.0) -> str:
    """Generate a PDF invoice and return the file path."""
    pdf_path = os.path.join(INVOICES_DIR, f"{invoice_number}.pdf")
    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter
    
    # Currency symbol mapping
    currency_symbols = {
        "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", 
        "CAD": "CA$", "AUD": "A$", "CHF": "CHF", "CNY": "¥", "MXN": "MX$"
    }
    symbol = currency_symbols.get(currency.upper(), currency + " ")
    
    # Header
    c.setFont("Helvetica-Bold", 24)
    c.drawString(1 * inch, height - 1 * inch, "INVOICE")
    
    c.setFont("Helvetica", 11)
    c.drawString(1 * inch, height - 1.4 * inch, f"Invoice Number: {invoice_number}")
    c.drawString(1 * inch, height - 1.6 * inch, f"Date: {datetime.now().strftime('%Y-%m-%d')}")
    if currency != "USD":
        c.setFont("Helvetica", 9)
        c.drawString(1 * inch, height - 1.8 * inch, f"Currency: {currency} (Rate: 1 USD = {exchange_rate:.4f} {currency})")
        c.setFont("Helvetica", 11)
    
    # From
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1 * inch, height - 2.2 * inch, "From:")
    c.setFont("Helvetica", 10)
    c.drawString(1 * inch, height - 2.5 * inch, "Warehouse Supply Co.")
    c.drawString(1 * inch, height - 2.7 * inch, "123 Industrial Blvd")
    c.drawString(1 * inch, height - 2.9 * inch, "Chicago, IL 60601")
    
    # Bill To
    c.setFont("Helvetica-Bold", 12)
    c.drawString(4 * inch, height - 2.2 * inch, "Bill To:")
    c.setFont("Helvetica", 10)
    c.drawString(4 * inch, height - 2.5 * inch, customer_name)
    c.drawString(4 * inch, height - 2.7 * inch, customer_email)
    
    # Items header
    y = height - 4 * inch
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1 * inch, y, "Item")
    c.drawString(4 * inch, y, "Qty")
    c.drawString(5 * inch, y, "Price")
    c.drawString(6 * inch, y, "Total")
    
    # Line
    y -= 0.2 * inch
    c.line(1 * inch, y, 7.5 * inch, y)
    
    # Items
    c.setFont("Helvetica", 10)
    y -= 0.3 * inch
    for item in items:
        c.drawString(1 * inch, y, item['name'][:35])
        c.drawString(4 * inch, y, str(item['quantity']))
        c.drawString(5 * inch, y, f"{symbol}{item['unit_price']:.2f}")
        c.drawString(6 * inch, y, f"{symbol}{item['line_total']:.2f}")
        y -= 0.25 * inch
    
    # Totals
    y -= 0.3 * inch
    c.line(1 * inch, y, 7.5 * inch, y)
    y -= 0.3 * inch
    
    c.drawString(5 * inch, y, "Subtotal:")
    c.drawString(6 * inch, y, f"{symbol}{subtotal:.2f}")
    y -= 0.25 * inch
    
    c.drawString(5 * inch, y, "Tax (8.25%):")
    c.drawString(6 * inch, y, f"{symbol}{tax:.2f}")
    y -= 0.25 * inch
    
    c.setFont("Helvetica-Bold", 11)
    c.drawString(5 * inch, y, "Total:")
    c.drawString(6 * inch, y, f"{symbol}{total:.2f}")
    
    # Footer
    c.setFont("Helvetica", 9)
    c.drawString(1 * inch, 1 * inch, "Thank you for your business!")
    c.drawString(1 * inch, 0.75 * inch, "Payment due within 30 days. Questions? Contact support@warehousesupply.com")
    
    c.save()
    return pdf_path


@tool
def generate_invoice(customer_name: str, customer_email: str, items_str: str, currency: str = "USD") -> str:
    """
    Generate an invoice PDF for a customer order with optional currency conversion.
    
    Args:
        customer_name: Name of the customer
        customer_email: Customer's email address
        items_str: Comma-separated list of items in format "SKU:quantity" (e.g., "PP-ROPE-12MM:10,HW-SHACKLE-10:5")
        currency: Currency code for the invoice (default: 'USD'). Supports USD, EUR, GBP, CAD, AUD, JPY, etc.
    
    Returns:
        Invoice details and PDF file path
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get exchange rate if currency is not USD
        exchange_rate = 1.0
        if currency.upper() != "USD":
            try:
                url = f"https://api.exchangerate-api.com/v4/latest/USD"
                response = httpx.get(url, timeout=5.0)
                response.raise_for_status()
                data = response.json()
                
                if currency.upper() not in data["rates"]:
                    return f"Currency '{currency}' not supported. Please use: USD, EUR, GBP, CAD, AUD, JPY, CHF, CNY, MXN, etc."
                
                exchange_rate = data["rates"][currency.upper()]
            except Exception as e:
                return f"Error fetching exchange rate: {str(e)}. Using USD instead."
        
        # Parse items
        items = []
        errors = []
        
        for item_spec in items_str.split(","):
            item_spec = item_spec.strip()
            if ":" not in item_spec:
                errors.append(f"Invalid format: '{item_spec}' (use SKU:quantity)")
                continue
            
            parts = item_spec.split(":")
            if len(parts) != 2:
                errors.append(f"Invalid format: '{item_spec}'")
                continue
            
            sku, qty_str = parts
            try:
                quantity = int(qty_str)
            except ValueError:
                errors.append(f"Invalid quantity for {sku}: '{qty_str}'")
                continue
            
            # Look up product
            cursor.execute("SELECT name, unit_price FROM products WHERE UPPER(sku) = UPPER(?)", (sku.strip(),))
            product = cursor.fetchone()
            
            if not product:
                errors.append(f"Product not found: '{sku}'")
                continue
            
            items.append({
                "sku": sku.strip().upper(),
                "name": product['name'],
                "quantity": quantity,
                "unit_price": product['unit_price'] * exchange_rate,
                "line_total": quantity * product['unit_price'] * exchange_rate
            })
        
        if errors:
            return "**Errors:**\n" + "\n".join(f"• {e}" for e in errors)
        
        if not items:
            return "No valid items provided. Use format: SKU:quantity (e.g., PP-ROPE-12MM:10)"
        
        # Calculate totals
        subtotal = sum(item['line_total'] for item in items)
        tax_rate = 0.0825
        tax = subtotal * tax_rate
        total = subtotal + tax
        
        # Generate invoice number and PDF
        invoice_number = _get_next_invoice_number()
        pdf_path = _generate_invoice_pdf(
            invoice_number, customer_name, customer_email,
            items, subtotal, tax, total, currency.upper(), exchange_rate
        )
        
        # Currency symbol
        currency_symbols = {
            "USD": "$", "EUR": "€", "GBP": "£", "JPY": "¥", 
            "CAD": "CA$", "AUD": "A$", "CHF": "CHF", "CNY": "¥", "MXN": "MX$"
        }
        symbol = currency_symbols.get(currency.upper(), currency.upper() + " ")
        
        # Format response
        result = "<strong>Invoice Generated Successfully!</strong><br><br>"
        result += f"<strong>Invoice Number:</strong> {invoice_number}<br>"
        result += f"<strong>Customer:</strong> {customer_name} ({customer_email})<br>"
        result += f"<strong>Date:</strong> {datetime.now().strftime('%Y-%m-%d')}<br>"
        result += f"<strong>Currency:</strong> {currency.upper()}<br>"
        if currency.upper() != "USD":
            result += f"<strong>Exchange Rate:</strong> 1 USD = {exchange_rate:.4f} {currency.upper()}<br>"
        result += "<br><strong>Items:</strong><br>"
        for item in items:
            result += f"  • {item['name']} x{item['quantity']} @ {symbol}{item['unit_price']:.2f} = {symbol}{item['line_total']:.2f}<br>"
        result += f"<br><strong>Subtotal:</strong> {symbol}{subtotal:.2f}<br>"
        result += f"<strong>Tax (8.25%):</strong> {symbol}{tax:.2f}<br>"
        result += f"<strong>Total:</strong> {symbol}{total:.2f}<br><br>"
        result += f"<strong>PDF saved to:</strong> {pdf_path}"
        
        return result
        
    finally:
        conn.close()
