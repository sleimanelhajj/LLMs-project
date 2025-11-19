"""
Create sample PDF documents for testing PDF Analysis Agent
"""

from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from pathlib import Path


def create_sample_invoice():
    """Create a sample invoice PDF."""
    
    output_dir = Path("data/test_documents")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    pdf_path = output_dir / "sample_invoice.pdf"
    
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    width, height = letter
    
    # Header
    c.setFont("Helvetica-Bold", 20)
    c.drawString(1*inch, height - 1*inch, "INVOICE")
    
    c.setFont("Helvetica", 12)
    c.drawString(1*inch, height - 1.5*inch, "Invoice Number: INV-2024-001")
    c.drawString(1*inch, height - 1.8*inch, "Date: November 15, 2024")
    
    # Company info
    c.setFont("Helvetica-Bold", 12)
    c.drawString(1*inch, height - 2.5*inch, "From:")
    c.setFont("Helvetica", 10)
    c.drawString(1*inch, height - 2.8*inch, "Warehouse Supply Co.")
    c.drawString(1*inch, height - 3.0*inch, "123 Industrial Park")
    c.drawString(1*inch, height - 3.2*inch, "Dallas, TX 75201")
    
    # Customer info
    c.setFont("Helvetica-Bold", 12)
    c.drawString(4*inch, height - 2.5*inch, "Bill To:")
    c.setFont("Helvetica", 10)
    c.drawString(4*inch, height - 2.8*inch, "John Construction LLC")
    c.drawString(4*inch, height - 3.0*inch, "456 Builder Ave")
    c.drawString(4*inch, height - 3.2*inch, "Houston, TX 77001")
    
    # Items table
    y = height - 4*inch
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1*inch, y, "Item")
    c.drawString(3.5*inch, y, "Quantity")
    c.drawString(4.5*inch, y, "Unit Price")
    c.drawString(5.5*inch, y, "Total")
    
    # Draw line
    c.line(1*inch, y - 0.1*inch, 6.5*inch, y - 0.1*inch)
    
    # Items
    items = [
        ("Polypropylene Rope 12mm", "100 m", "$3.75", "$375.00"),
        ("Nylon Storage Bag Large", "20 pcs", "$15.00", "$300.00"),
        ("Steel Wire 4mm", "50 m", "$2.10", "$105.00"),
        ("Wire Rope Thimble", "30 pcs", "$0.85", "$25.50"),
    ]
    
    c.setFont("Helvetica", 10)
    y -= 0.4*inch
    for item, qty, price, total in items:
        c.drawString(1*inch, y, item)
        c.drawString(3.5*inch, y, qty)
        c.drawString(4.5*inch, y, price)
        c.drawString(5.5*inch, y, total)
        y -= 0.3*inch
    
    # Totals
    y -= 0.3*inch
    c.line(4.5*inch, y, 6.5*inch, y)
    
    y -= 0.3*inch
    c.setFont("Helvetica-Bold", 10)
    c.drawString(4.5*inch, y, "Subtotal:")
    c.drawString(5.5*inch, y, "$805.50")
    
    y -= 0.3*inch
    c.drawString(4.5*inch, y, "Tax (8.25%):")
    c.drawString(5.5*inch, y, "$66.45")
    
    y -= 0.3*inch
    c.line(4.5*inch, y, 6.5*inch, y)
    
    y -= 0.3*inch
    c.setFont("Helvetica-Bold", 12)
    c.drawString(4.5*inch, y, "Total:")
    c.drawString(5.5*inch, y, "$871.95")
    
    # Footer
    c.setFont("Helvetica", 9)
    c.drawString(1*inch, 1*inch, "Payment Terms: Net 30 days")
    c.drawString(1*inch, 0.8*inch, "Thank you for your business!")
    
    c.save()
    
    print(f"✅ Created sample invoice: {pdf_path}")
    return pdf_path


def create_sample_contract():
    """Create a sample contract PDF."""
    
    output_dir = Path("data/test_documents")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    pdf_path = output_dir / "sample_contract.pdf"
    
    c = canvas.Canvas(str(pdf_path), pagesize=letter)
    width, height = letter
    
    # Header
    c.setFont("Helvetica-Bold", 16)
    c.drawString(1*inch, height - 1*inch, "SUPPLY AGREEMENT")
    
    c.setFont("Helvetica", 11)
    y = height - 1.8*inch
    
    contract_text = """
This Supply Agreement ("Agreement") is entered into as of November 15, 2024,
between Warehouse Supply Co. ("Supplier") and Construction Partners LLC ("Customer").

1. SCOPE OF SUPPLY
The Supplier agrees to provide industrial supplies including ropes, wire, bags,
and related accessories as detailed in attached product catalog.

2. PRICING AND PAYMENT
Pricing is as per current catalog rates. Volume discounts apply:
- 10% discount for orders over $5,000
- 15% discount for orders over $10,000
- 20% discount for orders over $20,000

Payment terms: Net 30 days from invoice date.

3. DELIVERY
Standard delivery within 5-7 business days.
Express delivery available for additional fee.
Free shipping on orders over $500.

4. WARRANTY
All products carry a 1-year warranty against manufacturing defects.
Warranty does not cover normal wear and tear.

5. RETURNS
Returns accepted within 30 days of purchase.
Products must be unused and in original packaging.
15% restocking fee applies.

6. TERM AND TERMINATION
This agreement is valid for 12 months from the signing date.
Either party may terminate with 30 days written notice.
    """
    
    c.setFont("Helvetica", 10)
    for line in contract_text.strip().split('\n'):
        if line.strip():
            c.drawString(1*inch, y, line.strip())
            y -= 0.2*inch
            
            if y < 2*inch:
                c.showPage()
                c.setFont("Helvetica", 10)
                y = height - 1*inch
    
    # Signatures
    y -= 0.5*inch
    c.setFont("Helvetica-Bold", 10)
    c.drawString(1*inch, y, "AGREED AND ACCEPTED:")
    
    y -= 0.8*inch
    c.line(1*inch, y, 3*inch, y)
    y -= 0.2*inch
    c.setFont("Helvetica", 9)
    c.drawString(1*inch, y, "Supplier Signature")
    
    y2 = y + 0.2*inch
    c.line(4*inch, y2, 6*inch, y2)
    c.drawString(4*inch, y, "Customer Signature")
    
    c.save()
    
    print(f"✅ Created sample contract: {pdf_path}")
    return pdf_path


if __name__ == "__main__":
    print("Creating sample PDF documents...\n")
    
    try:
        invoice_path = create_sample_invoice()
        contract_path = create_sample_contract()
        
        print("\n" + "=" * 60)
        print("✅ Sample PDFs created successfully!")
        print("=" * 60)
        print(f"\n1. Invoice: {invoice_path}")
        print(f"2. Contract: {contract_path}")
        
    except ImportError:
        print("\n⚠️  reportlab not installed. Installing...")
        print("Run: pip install reportlab")