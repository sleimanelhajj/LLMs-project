"""
Initialize Product Catalog Database

Creates SQLite database with sample products.
"""

import sqlite3
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from config import CATALOG_DB_PATH


def create_catalog_database():
    """Create and populate the product catalog database."""
    
    print("=" * 80)
    print("CATALOG DATABASE INITIALIZATION")
    print("=" * 80 + "\n")
    
    # Ensure data directory exists
    os.makedirs(os.path.dirname(CATALOG_DB_PATH), exist_ok=True)
    
    # Connect to database
    conn = sqlite3.connect(CATALOG_DB_PATH)
    cursor = conn.cursor()
    
    # Drop existing table if it exists
    cursor.execute("DROP TABLE IF EXISTS products")
    
    # Create products table
    cursor.execute("""
        CREATE TABLE products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            unit_price REAL NOT NULL,
            unit_of_measure TEXT NOT NULL,
            quantity_on_hand INTEGER NOT NULL,
            description TEXT,
            specifications TEXT
        )
    """)
    
    # Sample products
    products = [
        # Ropes
        ("PP-ROPE-001", "Polypropylene Rope 8mm", "Ropes", 2.50, "meter", 1500,
         "High-strength polypropylene rope suitable for general purpose use",
         "Diameter: 8mm, Breaking strength: 800kg, UV resistant"),
        
        ("PP-ROPE-002", "Polypropylene Rope 12mm", "Ropes", 3.75, "meter", 800,
         "Heavy-duty polypropylene rope for industrial applications",
         "Diameter: 12mm, Breaking strength: 1500kg, UV resistant"),
        
        ("NY-ROPE-001", "Nylon Rope 10mm", "Ropes", 4.20, "meter", 650,
         "Premium nylon rope with excellent elasticity and strength",
         "Diameter: 10mm, Breaking strength: 1200kg, Shock absorbing"),
        
        # Wires
        ("ST-WIRE-001", "Steel Wire 2mm", "Wire", 1.25, "meter", 2000,
         "Galvanized steel wire for light-duty applications",
         "Diameter: 2mm, Tensile strength: 400MPa, Corrosion resistant"),
        
        ("ST-WIRE-002", "Steel Wire 4mm", "Wire", 2.10, "meter", 1200,
         "Heavy-duty galvanized steel wire",
         "Diameter: 4mm, Tensile strength: 500MPa, Corrosion resistant"),
        
        ("ST-CABLE-001", "Steel Cable 6mm", "Wire", 5.50, "meter", 450,
         "Flexible steel cable for heavy lifting",
         "Diameter: 6mm, Breaking strength: 3000kg, 7x19 construction"),
        
        # Bags
        ("NY-BAG-001", "Nylon Storage Bag Large", "Bags", 15.00, "piece", 200,
         "Durable nylon storage bag for warehouse organization",
         "Dimensions: 60x40x30cm, Capacity: 70L, Water resistant"),
        
        ("NY-BAG-002", "Nylon Storage Bag Medium", "Bags", 12.00, "piece", 350,
         "Medium-sized nylon storage bag",
         "Dimensions: 45x30x25cm, Capacity: 35L, Water resistant"),
        
        ("PP-BAG-001", "Polypropylene Bag Heavy Duty", "Bags", 8.50, "piece", 500,
         "Heavy-duty woven polypropylene bag",
         "Dimensions: 50x80cm, Load capacity: 25kg, Reusable"),
        
        # Tools & Accessories
        ("HOOK-001", "Steel S-Hook 5cm", "Accessories", 1.80, "piece", 800,
         "Heavy-duty steel S-hook",
         "Size: 5cm, Load capacity: 50kg, Zinc plated"),
        
        ("CLIP-001", "Carabiner Clip Large", "Accessories", 3.20, "piece", 600,
         "Aluminum carabiner with screw lock",
         "Size: 10cm, Load capacity: 250kg, Lightweight"),
        
        ("THIMBLE-001", "Wire Rope Thimble", "Accessories", 0.85, "piece", 1000,
         "Galvanized steel thimble for wire rope",
         "For 6mm wire rope, Prevents wear at termination points"),
    ]
    
    # Insert products
    cursor.executemany("""
        INSERT INTO products (sku, name, category, unit_price, unit_of_measure, 
                            quantity_on_hand, description, specifications)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, products)
    
    conn.commit()
    
    # Verify insertion
    cursor.execute("SELECT COUNT(*) FROM products")
    count = cursor.fetchone()[0]
    
    print(f"✅ Created products table")
    print(f"✅ Inserted {count} products\n")
    
    # Display sample data
    print("📦 Sample Products:")
    print("-" * 80)
    cursor.execute("""
        SELECT sku, name, category, unit_price, unit_of_measure, quantity_on_hand 
        FROM products 
        LIMIT 5
    """)
    
    for row in cursor.fetchall():
        sku, name, cat, price, unit, qty = row
        print(f"• {name} ({sku})")
        print(f"  Category: {cat} | Price: ${price}/{unit} | Stock: {qty} {unit}s")
    
    print(f"\n... and {count - 5} more products")
    print("-" * 80)
    
    conn.close()
    
    print(f"\n✅ SUCCESS: Catalog database created at {CATALOG_DB_PATH}")
    print("=" * 80)


if __name__ == "__main__":
    create_catalog_database()