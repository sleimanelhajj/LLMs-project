#!/usr/bin/env python3
"""
Initialize databases for the Employee Assistant Chatbot system.

This script creates:
1. SQLite database for product catalog
2. Customers, orders, and order items tables
3. Sample data for testing
4. Directory structure for file storage
"""

import sqlite3
import os
import sys
from datetime import datetime, timedelta
import random

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
    cursor.execute("DROP TABLE IF EXISTS order_items")
    cursor.execute("DROP TABLE IF EXISTS orders")
    cursor.execute("DROP TABLE IF EXISTS customers")
    cursor.execute("DROP TABLE IF EXISTS products")
    
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
    
    # Create customers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            company TEXT,
            address TEXT,
            city TEXT,
            country TEXT DEFAULT 'USA',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Create orders table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            customer_id TEXT NOT NULL,
            order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'pending',
            shipping_address TEXT,
            shipping_city TEXT,
            shipping_country TEXT,
            tracking_number TEXT,
            current_location TEXT,
            estimated_delivery DATE,
            total_amount REAL DEFAULT 0,
            currency TEXT DEFAULT 'USD',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        )
    """)
    
    # Create order_items table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS order_items (
            item_id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id TEXT NOT NULL,
            sku TEXT NOT NULL,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            total_price REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (sku) REFERENCES products(sku)
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
    
    # Sample customer data
    customers = [
        ("CUST-001", "John Smith", "john.smith@email.com", "+1-555-0101", "Smith Construction", "123 Main St", "New York", "USA"),
        ("CUST-002", "Sarah Johnson", "sarah.j@techcorp.com", "+1-555-0102", "TechCorp Industries", "456 Oak Ave", "Los Angeles", "USA"),
        ("CUST-003", "Michael Brown", "m.brown@builders.net", "+1-555-0103", "Brown Builders LLC", "789 Pine Rd", "Chicago", "USA"),
        ("CUST-004", "Emily Davis", "emily.davis@marine.co", "+1-555-0104", "Marine Supplies Co", "321 Harbor Blvd", "Miami", "USA"),
        ("CUST-005", "Robert Wilson", "rwilson@safetyfirst.com", "+1-555-0105", "Safety First Inc", "654 Safety Lane", "Houston", "USA"),
        ("CUST-006", "Lisa Anderson", "l.anderson@warehouse.io", "+1-555-0106", "Warehouse Solutions", "987 Storage Dr", "Phoenix", "USA"),
        ("CUST-007", "David Martinez", "david.m@constructall.com", "+1-555-0107", "ConstructAll Corp", "147 Builder Way", "Philadelphia", "USA"),
        ("CUST-008", "Jennifer Taylor", "jtaylor@industrial.net", "+1-555-0108", "Industrial Supplies Ltd", "258 Factory Rd", "San Antonio", "USA"),
    ]
    
    cursor.executemany(
        "INSERT OR REPLACE INTO customers (customer_id, name, email, phone, company, address, city, country) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        customers
    )
    
    # Generate sample orders with various statuses
    order_statuses = ['pending', 'confirmed', 'processing', 'shipped', 'in_transit', 'out_for_delivery', 'delivered', 'cancelled']
    locations = [
        "Warehouse - New York",
        "Distribution Center - Chicago", 
        "Transit Hub - Dallas",
        "Local Facility - Los Angeles",
        "Out for Delivery - Local Area",
        "Delivered"
    ]
    
    orders = []
    order_items_data = []
    
    # Create orders for each customer
    base_date = datetime.now()
    order_counter = 1
    
    for customer in customers:
        customer_id = customer[0]
        customer_city = customer[6]
        
        # Each customer gets 2-4 orders
        num_orders = random.randint(2, 4)
        
        for i in range(num_orders):
            order_id = f"ORD-2024-{order_counter:04d}"
            order_date = base_date - timedelta(days=random.randint(1, 90))
            
            # Determine status based on order age
            days_ago = (base_date - order_date).days
            if days_ago > 30:
                status = 'delivered'
                current_location = 'Delivered'
                est_delivery = order_date + timedelta(days=random.randint(3, 7))
            elif days_ago > 14:
                status = random.choice(['delivered', 'delivered', 'in_transit'])
                current_location = 'Delivered' if status == 'delivered' else random.choice(locations[:-1])
                est_delivery = order_date + timedelta(days=random.randint(5, 10))
            elif days_ago > 7:
                status = random.choice(['shipped', 'in_transit', 'out_for_delivery'])
                current_location = random.choice(locations[1:5])
                est_delivery = base_date + timedelta(days=random.randint(1, 3))
            elif days_ago > 3:
                status = random.choice(['processing', 'shipped'])
                current_location = random.choice(locations[:3])
                est_delivery = base_date + timedelta(days=random.randint(2, 5))
            else:
                status = random.choice(['pending', 'confirmed', 'processing'])
                current_location = locations[0]
                est_delivery = base_date + timedelta(days=random.randint(5, 10))
            
            tracking_number = f"TRK{random.randint(100000000, 999999999)}" if status not in ['pending', 'confirmed'] else None
            
            # Select random products for this order
            num_items = random.randint(1, 4)
            selected_products = random.sample(products, num_items)
            total_amount = 0
            
            for product in selected_products:
                sku = product[0]
                product_name = product[1]
                unit_price = product[5]
                quantity = random.randint(5, 50)
                item_total = round(unit_price * quantity, 2)
                total_amount += item_total
                
                order_items_data.append((order_id, sku, product_name, quantity, unit_price, item_total))
            
            orders.append((
                order_id,
                customer_id,
                order_date.strftime("%Y-%m-%d %H:%M:%S"),
                status,
                customer[5],  # shipping address
                customer_city,
                customer[7],  # country
                tracking_number,
                current_location,
                est_delivery.strftime("%Y-%m-%d"),
                round(total_amount, 2),
                "USD",
                None
            ))
            
            order_counter += 1
    
    # Insert orders
    cursor.executemany(
        """INSERT INTO orders 
           (order_id, customer_id, order_date, status, shipping_address, shipping_city, 
            shipping_country, tracking_number, current_location, estimated_delivery, 
            total_amount, currency, notes) 
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        orders
    )
    
    # Insert order items
    cursor.executemany(
        """INSERT INTO order_items 
           (order_id, sku, product_name, quantity, unit_price, total_price) 
           VALUES (?, ?, ?, ?, ?, ?)""",
        order_items_data
    )
    
    conn.commit()
    conn.close()
    
    print(f"✓ Catalog database created at: {CATALOG_DB_PATH}")
    print(f"✓ Inserted {len(products)} sample products")
    print(f"✓ Inserted {len(customers)} sample customers")
    print(f"✓ Inserted {len(orders)} sample orders")
    print(f"✓ Inserted {len(order_items_data)} order items")


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
        
        # Check products table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='products'")
        if cursor.fetchone():
            print("✓ Products table exists")
        else:
            print("✗ Products table not found")
            return False
        
        # Check customers table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='customers'")
        if cursor.fetchone():
            print("✓ Customers table exists")
        else:
            print("✗ Customers table not found")
            return False
        
        # Check orders table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='orders'")
        if cursor.fetchone():
            print("✓ Orders table exists")
        else:
            print("✗ Orders table not found")
            return False
        
        # Check order_items table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='order_items'")
        if cursor.fetchone():
            print("✓ Order_items table exists")
        else:
            print("✗ Order_items table not found")
            return False
        
        # Check data counts
        cursor.execute("SELECT COUNT(*) FROM products")
        product_count = cursor.fetchone()[0]
        print(f"✓ Found {product_count} products in database")
        
        cursor.execute("SELECT COUNT(*) FROM customers")
        customer_count = cursor.fetchone()[0]
        print(f"✓ Found {customer_count} customers in database")
        
        cursor.execute("SELECT COUNT(*) FROM orders")
        order_count = cursor.fetchone()[0]
        print(f"✓ Found {order_count} orders in database")
        
        # Show sample products
        cursor.execute("SELECT sku, name, category, unit_price FROM products LIMIT 3")
        print("\nSample products:")
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]} ({row[2]}) - ${row[3]:.2f}")
        
        # Show sample customers
        cursor.execute("SELECT customer_id, name, email, company FROM customers LIMIT 3")
        print("\nSample customers:")
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]} ({row[2]}) - {row[3]}")
        
        # Show sample orders
        cursor.execute("""
            SELECT o.order_id, c.name, o.status, o.total_amount 
            FROM orders o 
            JOIN customers c ON o.customer_id = c.customer_id 
            LIMIT 3
        """)
        print("\nSample orders:")
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]} - {row[2]} - ${row[3]:.2f}")
        
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
