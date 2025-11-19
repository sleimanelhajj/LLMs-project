#!/usr/bin/env python3
"""
Initialize databases for the Employee Assistant Chatbot system.

This script creates:
1. SQLite database for product catalog
2. Sample data for testing
3. Directory structure for file storage
"""

import sqlite3
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from config import CATALOG_DB_PATH, DATABASE_DIR, INVOICES_DIR, UPLOADS_DIR


def create_catalog_database():
    """Create and populate the product catalog database."""
    print("Creating catalog database...")
    
    # Ensure directory exists
    os.makedirs(DATABASE_DIR, exist_ok=True)
    
    # Create database
    conn = sqlite3.connect(CATALOG_DB_PATH)
    cursor = conn.cursor()
    
    # Create products table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            sku TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            diameter_mm REAL,
            unit TEXT NOT NULL,
            unit_price REAL NOT NULL,
            currency TEXT DEFAULT 'USD',
            quantity_on_hand INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Sample product data
    products = [
        ("PP-ROPE-001", "Polypropylene Rope 8mm", "Ropes", 8.0, "meter", 2.50, "USD", 1500),
        ("PP-ROPE-002", "Polypropylene Rope 12mm", "Ropes", 12.0, "meter", 3.75, "USD", 800),
        ("PP-ROPE-003", "Polypropylene Rope 16mm", "Ropes", 16.0, "meter", 5.25, "USD", 400),
        ("NY-BAG-001", "Nylon Storage Bag Large", "Bags", None, "piece", 15.00, "USD", 200),
        ("NY-BAG-002", "Nylon Storage Bag Medium", "Bags", None, "piece", 12.00, "USD", 350),
        ("NY-BAG-003", "Nylon Storage Bag Small", "Bags", None, "piece", 8.50, "USD", 500),
        ("ST-WIRE-001", "Steel Wire 2mm", "Wire", 2.0, "meter", 1.25, "USD", 2000),
        ("ST-WIRE-002", "Steel Wire 4mm", "Wire", 4.0, "meter", 2.10, "USD", 1200),
        ("ST-WIRE-003", "Steel Wire 6mm", "Wire", 6.0, "meter", 3.80, "USD", 600),
        ("SF-GEAR-001", "Safety Harness Standard", "Safety", None, "piece", 89.99, "USD", 75),
        ("SF-GEAR-002", "Safety Helmet Class A", "Safety", None, "piece", 34.99, "USD", 120),
        ("SF-GEAR-003", "Safety Goggles Anti-Fog", "Safety", None, "piece", 24.99, "USD", 200),
        ("BX-CARDBOARD-001", "Cardboard Box Large", "Packaging", None, "piece", 3.50, "USD", 800),
        ("BX-CARDBOARD-002", "Cardboard Box Medium", "Packaging", None, "piece", 2.75, "USD", 1200),
        ("BX-CARDBOARD-003", "Cardboard Box Small", "Packaging", None, "piece", 1.95, "USD", 1500),
    ]
    
    # Insert products
    cursor.executemany(
        "INSERT OR REPLACE INTO products (sku, name, category, diameter_mm, unit, unit_price, currency, quantity_on_hand) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        products
    )
    
    conn.commit()
    conn.close()
    
    print(f"✓ Catalog database created at: {CATALOG_DB_PATH}")
    print(f"✓ Inserted {len(products)} sample products")


def create_directories():
    """Create necessary directories for file storage."""
    print("Creating directory structure...")
    
    directories = [
        DATABASE_DIR,
        INVOICES_DIR,
        UPLOADS_DIR,
        os.path.join(os.path.dirname(DATABASE_DIR), "templates"),
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)
        print(f"✓ Created directory: {directory}")


def verify_setup():
    """Verify that the database was created correctly."""
    print("\nVerifying setup...")
    
    try:
        conn = sqlite3.connect(CATALOG_DB_PATH)
        cursor = conn.cursor()
        
        # Check table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='products'")
        if cursor.fetchone():
            print("✓ Products table exists")
        else:
            print("✗ Products table not found")
            return False
        
        # Check data
        cursor.execute("SELECT COUNT(*) FROM products")
        count = cursor.fetchone()[0]
        print(f"✓ Found {count} products in database")
        
        # Show sample products
        cursor.execute("SELECT sku, name, category, unit_price FROM products LIMIT 5")
        print("\nSample products:")
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]} ({row[2]}) - ${row[3]:.2f}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Error verifying setup: {e}")
        return False


def main():
    """Main setup function."""
    print("=== Employee Assistant Chatbot - Database Initialization ===\n")
    
    try:
        create_directories()
        create_catalog_database()
        
        if verify_setup():
            print("\n🎉 Database initialization completed successfully!")
            print("\nNext steps:")
            print("1. Copy .env.example to .env and add your API keys")
            print("2. Install dependencies: pip install -r requirements.txt")
            print("3. Start the MCP server: python mcp/server.py")
            print("4. Start the FastAPI server: python api/main.py")
        else:
            print("\n❌ Database initialization failed!")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ Error during initialization: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
