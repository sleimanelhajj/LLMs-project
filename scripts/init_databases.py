#!/usr/bin/env python3
"""
Initialize ALL databases and components for the Employee Assistant Chatbot system.

This script creates:
1. SQLite database for product catalog
2. SQLite database for customers and orders
3. Vector database for company documents (RAG)
4. Sample data for testing
5. Directory structure for file storage
"""

import sqlite3
import os
import sys

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from config import CATALOG_DB_PATH, DATABASE_DIR, INVOICES_DIR
from tools.utils.rag_utils import initialize_company_vector_db


def create_catalog_database():
    """Create and populate the product catalog database."""
    print("Creating catalog database...")
    
    # Ensure directory exists
    os.makedirs(DATABASE_DIR, exist_ok=True)
    
    # Create database
    conn = sqlite3.connect(CATALOG_DB_PATH)
    cursor = conn.cursor()
    
    # Drop existing table to ensure clean schema
    cursor.execute("DROP TABLE IF EXISTS products")
    
    # Create products table with enhanced schema
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS products (
            sku TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            material TEXT,
            diameter_mm REAL,
            weight_kg REAL,
            breaking_strength TEXT,
            unit TEXT NOT NULL,
            unit_price REAL NOT NULL,
            currency TEXT DEFAULT 'USD',
            quantity_on_hand INTEGER DEFAULT 0,
            min_order_qty INTEGER DEFAULT 1,
            lead_time_days INTEGER DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    # Comprehensive product data with descriptions
    products = [
        # ===== ROPES =====
        ("PP-ROPE-8MM", "Polypropylene Rope 8mm", "Ropes", 
         "Lightweight, floating rope ideal for water applications and general purpose use. UV resistant and rot-proof.",
         "Polypropylene", 8.0, 0.04, "120 kg", "meter", 2.50, "USD", 1500, 10, 1),
        ("PP-ROPE-12MM", "Polypropylene Rope 12mm", "Ropes",
         "Medium-duty floating rope perfect for marine, camping, and utility applications. Excellent chemical resistance.",
         "Polypropylene", 12.0, 0.08, "280 kg", "meter", 3.75, "USD", 800, 10, 1),
        ("PP-ROPE-16MM", "Polypropylene Rope 16mm", "Ropes",
         "Heavy-duty polypropylene rope for industrial and marine use. Floats on water, resists mildew and rot.",
         "Polypropylene", 16.0, 0.14, "480 kg", "meter", 5.25, "USD", 400, 10, 1),
        ("NY-ROPE-10MM", "Nylon Rope 10mm", "Ropes",
         "High-strength nylon rope with excellent shock absorption. Ideal for towing, anchoring, and climbing applications.",
         "Nylon", 10.0, 0.07, "450 kg", "meter", 4.99, "USD", 600, 10, 1),
        ("NY-ROPE-14MM", "Nylon Rope 14mm", "Ropes",
         "Premium nylon rope offering superior strength and elasticity. Perfect for heavy-duty lifting and rigging.",
         "Nylon", 14.0, 0.12, "820 kg", "meter", 7.50, "USD", 350, 10, 1),
        ("NY-ROPE-20MM", "Nylon Rope 20mm", "Ropes",
         "Industrial-grade nylon rope for maximum strength applications. Excellent abrasion resistance and durability.",
         "Nylon", 20.0, 0.22, "1500 kg", "meter", 12.99, "USD", 200, 10, 2),
        ("MN-ROPE-8MM", "Manila Rope 8mm", "Ropes",
         "Natural fiber rope with traditional look and good grip. Biodegradable and eco-friendly option.",
         "Manila Hemp", 8.0, 0.05, "80 kg", "meter", 1.99, "USD", 1000, 10, 1),
        ("MN-ROPE-12MM", "Manila Rope 12mm", "Ropes",
         "Classic natural rope for decorative and functional use. Excellent grip, ideal for gym climbing ropes.",
         "Manila Hemp", 12.0, 0.10, "180 kg", "meter", 3.25, "USD", 700, 10, 1),
        
        # ===== WIRE & CABLES =====
        ("ST-WIRE-2MM", "Galvanized Steel Wire 2mm", "Wire",
         "Corrosion-resistant galvanized wire for fencing, crafts, and light-duty applications.",
         "Galvanized Steel", 2.0, 0.025, "200 kg", "meter", 1.25, "USD", 2000, 20, 1),
        ("ST-WIRE-4MM", "Galvanized Steel Wire 4mm", "Wire",
         "Medium-gauge galvanized wire perfect for agricultural fencing and construction support.",
         "Galvanized Steel", 4.0, 0.10, "750 kg", "meter", 2.10, "USD", 1200, 20, 1),
        ("ST-WIRE-6MM", "Galvanized Steel Wire 6mm", "Wire",
         "Heavy-duty galvanized wire for structural applications, guy wires, and heavy fencing.",
         "Galvanized Steel", 6.0, 0.22, "1600 kg", "meter", 3.80, "USD", 600, 20, 2),
        ("SS-CABLE-3MM", "Stainless Steel Cable 3mm 7x19", "Wire",
         "Marine-grade stainless steel cable with 7x19 construction for flexibility. Ideal for rigging and balustrades.",
         "Stainless Steel 316", 3.0, 0.05, "550 kg", "meter", 4.50, "USD", 500, 10, 2),
        ("SS-CABLE-5MM", "Stainless Steel Cable 5mm 7x19", "Wire",
         "Premium stainless cable for architectural and marine applications. Excellent corrosion resistance.",
         "Stainless Steel 316", 5.0, 0.13, "1400 kg", "meter", 7.25, "USD", 300, 10, 2),
        ("WR-CABLE-8MM", "Wire Rope 8mm 6x19", "Wire",
         "General purpose wire rope for lifting and hoisting. Galvanized for outdoor use.",
         "Galvanized Steel", 8.0, 0.28, "3200 kg", "meter", 5.99, "USD", 400, 10, 3),
        
        # ===== STORAGE BAGS =====
        ("NY-BAG-L", "Heavy-Duty Nylon Storage Bag Large", "Bags",
         "Extra-large waterproof storage bag (60L capacity) with reinforced handles and YKK zippers. Perfect for equipment.",
         "Ripstop Nylon", None, 0.45, None, "piece", 24.99, "USD", 150, 1, 1),
        ("NY-BAG-M", "Heavy-Duty Nylon Storage Bag Medium", "Bags",
         "Medium waterproof bag (35L capacity) with shoulder strap. Ideal for tools and gear.",
         "Ripstop Nylon", None, 0.32, None, "piece", 18.99, "USD", 250, 1, 1),
        ("NY-BAG-S", "Heavy-Duty Nylon Storage Bag Small", "Bags",
         "Compact waterproof bag (15L capacity) for small tools and accessories. Includes internal pockets.",
         "Ripstop Nylon", None, 0.18, None, "piece", 12.99, "USD", 400, 1, 1),
        ("CV-BAG-TOOL", "Canvas Tool Bag", "Bags",
         "Durable 16oz canvas bag with leather handles. Multiple pockets for organizing hand tools.",
         "Heavy Canvas", None, 0.65, None, "piece", 34.99, "USD", 120, 1, 1),
        ("CV-BAG-ROPE", "Canvas Rope Bag", "Bags",
         "Specialized bag for storing ropes up to 100m. Features drainage grommets and shoulder strap.",
         "Heavy Canvas", None, 0.55, None, "piece", 29.99, "USD", 80, 1, 2),
        ("MESH-BAG-L", "Mesh Storage Bag Large", "Bags",
         "Breathable mesh bag for drying and storing wet equipment. 50L capacity with drawstring closure.",
         "Polyester Mesh", None, 0.15, None, "piece", 8.99, "USD", 300, 1, 1),
        
        # ===== SAFETY EQUIPMENT =====
        ("SF-HARNESS-STD", "Full Body Safety Harness - Standard", "Safety",
         "OSHA compliant full body harness with 5-point adjustment. Includes dorsal D-ring for fall arrest.",
         "Polyester Webbing", None, 1.8, "2200 kg", "piece", 89.99, "USD", 75, 1, 2),
        ("SF-HARNESS-PRO", "Full Body Safety Harness - Professional", "Safety",
         "Premium harness with padding, tool loops, and quick-connect buckles. Multiple attachment points.",
         "Polyester Webbing", None, 2.2, "2500 kg", "piece", 149.99, "USD", 40, 1, 3),
        ("SF-HELMET-A", "Safety Helmet Class A", "Safety",
         "ANSI Type I Class A helmet protecting against impact and electrical hazards up to 2,200V.",
         "ABS Plastic", None, 0.35, None, "piece", 34.99, "USD", 120, 1, 1),
        ("SF-HELMET-PRO", "Safety Helmet with Visor", "Safety",
         "Advanced helmet with integrated clear visor and 4-point chin strap. Ventilated design.",
         "ABS Plastic", None, 0.48, None, "piece", 54.99, "USD", 60, 1, 2),
        ("SF-GOGGLES", "Safety Goggles Anti-Fog", "Safety",
         "Splash and impact resistant goggles with anti-fog coating. Fits over prescription glasses.",
         "Polycarbonate", None, 0.08, None, "piece", 14.99, "USD", 200, 1, 1),
        ("SF-GLOVES-L", "Work Gloves Leather - Large", "Safety",
         "Premium cowhide leather gloves with reinforced palm. Excellent grip and durability.",
         "Cowhide Leather", None, 0.18, None, "pair", 19.99, "USD", 150, 1, 1),
        ("SF-GLOVES-M", "Work Gloves Leather - Medium", "Safety",
         "Premium cowhide leather gloves with reinforced palm. Excellent grip and durability.",
         "Cowhide Leather", None, 0.16, None, "pair", 19.99, "USD", 180, 1, 1),
        
        # ===== HARDWARE & ACCESSORIES =====
        ("HW-HOOK-SS-10", "Snap Hook Stainless Steel 10mm", "Hardware",
         "Marine-grade stainless steel snap hook. Spring-loaded gate with 1000kg working load.",
         "Stainless Steel 316", 10.0, 0.12, "1000 kg WLL", "piece", 8.99, "USD", 300, 5, 1),
        ("HW-HOOK-SS-12", "Snap Hook Stainless Steel 12mm", "Hardware",
         "Heavy-duty snap hook for lifting and rigging. Forged stainless with 1500kg working load.",
         "Stainless Steel 316", 12.0, 0.18, "1500 kg WLL", "piece", 12.99, "USD", 200, 5, 1),
        ("HW-SHACKLE-10", "D-Shackle Galvanized 10mm", "Hardware",
         "Forged steel D-shackle with screw pin. Ideal for connecting chains, wire rope, and straps.",
         "Galvanized Steel", 10.0, 0.15, "1000 kg WLL", "piece", 5.99, "USD", 400, 10, 1),
        ("HW-SHACKLE-16", "D-Shackle Galvanized 16mm", "Hardware",
         "Heavy-duty shackle for industrial rigging applications. Hot-dip galvanized for corrosion resistance.",
         "Galvanized Steel", 16.0, 0.35, "2500 kg WLL", "piece", 11.99, "USD", 250, 10, 1),
        ("HW-THIMBLE-10", "Wire Rope Thimble 10mm", "Hardware",
         "Protects wire rope from wear at connection points. Stamped stainless steel construction.",
         "Stainless Steel", 10.0, 0.03, None, "piece", 2.49, "USD", 500, 20, 1),
        ("HW-THIMBLE-16", "Wire Rope Thimble 16mm", "Hardware",
         "Heavy-duty thimble for larger wire ropes. Essential for eye splice protection.",
         "Stainless Steel", 16.0, 0.06, None, "piece", 3.99, "USD", 350, 20, 1),
        ("HW-CLAMP-8", "Wire Rope Clamp 8mm", "Hardware",
         "U-bolt style wire rope clamp for creating secure loops. Galvanized steel construction.",
         "Galvanized Steel", 8.0, 0.08, None, "piece", 1.99, "USD", 600, 10, 1),
        ("HW-TURNBUCKLE", "Turnbuckle Eye-Eye 10mm", "Hardware",
         "Adjustable turnbuckle for tensioning wire rope and cable. 12-inch take-up length.",
         "Galvanized Steel", 10.0, 0.35, "500 kg WLL", "piece", 14.99, "USD", 150, 5, 2),
        
        # ===== PACKAGING =====
        ("BX-CARD-L", "Heavy-Duty Cardboard Box Large", "Packaging",
         "Double-wall corrugated box (24x18x18 inches). Ideal for shipping heavy items up to 30kg.",
         "Corrugated Cardboard", None, 0.95, None, "piece", 4.99, "USD", 500, 10, 1),
        ("BX-CARD-M", "Heavy-Duty Cardboard Box Medium", "Packaging",
         "Double-wall corrugated box (18x14x12 inches). Suitable for medium loads up to 20kg.",
         "Corrugated Cardboard", None, 0.65, None, "piece", 3.49, "USD", 800, 10, 1),
        ("BX-CARD-S", "Heavy-Duty Cardboard Box Small", "Packaging",
         "Double-wall corrugated box (12x10x8 inches). Perfect for small parts and accessories.",
         "Corrugated Cardboard", None, 0.35, None, "piece", 2.29, "USD", 1200, 10, 1),
        ("TAPE-PACK", "Packing Tape Heavy Duty 48mm", "Packaging",
         "Industrial strength packing tape, 100m roll. Strong adhesive for secure box sealing.",
         "Polypropylene", None, 0.25, None, "roll", 4.99, "USD", 400, 6, 1),
        ("WRAP-STRETCH", "Stretch Wrap 500mm x 300m", "Packaging",
         "Industrial stretch film for pallet wrapping. 23 micron thickness for secure loads.",
         "LLDPE", None, 3.2, None, "roll", 18.99, "USD", 100, 1, 2),
        ("BUBBLE-ROLL", "Bubble Wrap Roll 500mm x 50m", "Packaging",
         "Protective bubble wrap with 10mm bubbles. Ideal for fragile item protection.",
         "Polyethylene", None, 1.5, None, "roll", 24.99, "USD", 80, 1, 1),
    ]
    
    # Insert products
    cursor.executemany(
        """INSERT OR REPLACE INTO products 
        (sku, name, category, description, material, diameter_mm, weight_kg, breaking_strength, 
         unit, unit_price, currency, quantity_on_hand, min_order_qty, lead_time_days) 
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        products
    )
    
    conn.commit()
    conn.close()
    
    print(f"✓ Catalog database created at: {CATALOG_DB_PATH}")
    print(f"✓ Inserted {len(products)} products")


def create_orders_database():
    """Create and populate the orders tracking database."""
    print("\nCreating orders database...")
    
    conn = sqlite3.connect(CATALOG_DB_PATH)
    cursor = conn.cursor()
    
    # Drop existing tables to ensure clean schema
    cursor.execute("DROP TABLE IF EXISTS order_items")
    cursor.execute("DROP TABLE IF EXISTS orders")
    cursor.execute("DROP TABLE IF EXISTS customers")
    
    # Create customers table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS customers (
            customer_id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            company TEXT,
            billing_address TEXT,
            billing_city TEXT,
            billing_country TEXT,
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
            tracking_number TEXT,
            current_location TEXT,
            estimated_delivery TEXT,
            shipping_address TEXT,
            shipping_city TEXT,
            shipping_country TEXT,
            total_amount REAL NOT NULL,
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
            product_sku TEXT,
            product_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            total_price REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (product_sku) REFERENCES products(sku)
        )
    """)
    
    # Sample customers
    customers = [
        ("CUST-001", "John Smith", "john.smith@email.com", "+1-555-0101", 
         "ABC Construction Co.", "123 Builder Lane", "New York", "USA"),
        ("CUST-002", "Sarah Johnson", "sarah.j@techcorp.com", "+1-555-0102",
         "TechCorp Industries", "456 Innovation Ave", "San Francisco", "USA"),
        ("CUST-003", "Michael Brown", "m.brown@marinesupply.com", "+1-555-0103",
         "Marine Supply LLC", "789 Harbor Road", "Miami", "USA"),
        ("CUST-004", "Emily Davis", "emily.davis@warehouse.net", "+1-555-0104",
         "Davis Warehouse Solutions", "321 Storage Blvd", "Chicago", "USA"),
        ("CUST-005", "Robert Wilson", "rwilson@industrialco.com", "+1-555-0105",
         "Industrial Co.", "555 Factory Way", "Houston", "USA"),
    ]
    
    cursor.executemany("""
        INSERT OR REPLACE INTO customers 
        (customer_id, name, email, phone, company, billing_address, billing_city, billing_country)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, customers)
    
    # Sample orders with various statuses
    orders = [
        # John Smith's orders
        ("ORD-2024-0001", "CUST-001", "2024-11-15 09:30:00", "delivered", "TRK-US-001234",
         "Delivered", "2024-11-20", "123 Builder Lane", "New York", "USA", 156.75, "USD", None),
        ("ORD-2024-0015", "CUST-001", "2024-11-28 14:22:00", "in_transit", "TRK-US-005678",
         "Distribution Center - Newark, NJ", "2024-12-03", "123 Builder Lane", "New York", "USA", 289.50, "USD", None),
        ("ORD-2024-0022", "CUST-001", "2024-12-01 08:15:00", "confirmed", None,
         "Warehouse - Processing", "2024-12-06", "123 Builder Lane", "New York", "USA", 445.00, "USD", "Rush order"),
        
        # Sarah Johnson's orders
        ("ORD-2024-0008", "CUST-002", "2024-11-20 11:45:00", "delivered", "TRK-US-002345",
         "Delivered", "2024-11-25", "456 Innovation Ave", "San Francisco", "USA", 523.96, "USD", None),
        ("ORD-2024-0019", "CUST-002", "2024-11-29 16:30:00", "shipped", "TRK-US-006789",
         "In Transit - Phoenix Hub", "2024-12-04", "456 Innovation Ave", "San Francisco", "USA", 178.45, "USD", None),
        
        # Michael Brown's orders
        ("ORD-2024-0003", "CUST-003", "2024-11-17 10:00:00", "delivered", "TRK-US-003456",
         "Delivered", "2024-11-22", "789 Harbor Road", "Miami", "USA", 892.50, "USD", None),
        ("ORD-2024-0012", "CUST-003", "2024-11-25 09:15:00", "out_for_delivery", "TRK-US-004567",
         "Out for Delivery - Miami", "2024-12-01", "789 Harbor Road", "Miami", "USA", 367.80, "USD", None),
        
        # Emily Davis's orders
        ("ORD-2024-0006", "CUST-004", "2024-11-19 13:20:00", "delivered", "TRK-US-007890",
         "Delivered", "2024-11-24", "321 Storage Blvd", "Chicago", "USA", 1245.00, "USD", None),
        ("ORD-2024-0021", "CUST-004", "2024-11-30 10:45:00", "processing", None,
         "Warehouse - Packing", "2024-12-05", "321 Storage Blvd", "Chicago", "USA", 567.25, "USD", None),
        
        # Robert Wilson's orders  
        ("ORD-2024-0010", "CUST-005", "2024-11-22 15:00:00", "delivered", "TRK-US-008901",
         "Delivered", "2024-11-27", "555 Factory Way", "Houston", "USA", 2150.00, "USD", None),
        ("ORD-2024-0016", "CUST-005", "2024-11-28 08:30:00", "cancelled", None,
         "Cancelled", None, "555 Factory Way", "Houston", "USA", 450.00, "USD", "Customer requested cancellation"),
        ("ORD-2024-0023", "CUST-005", "2024-12-01 11:00:00", "pending", None,
         "Awaiting Payment Confirmation", "2024-12-08", "555 Factory Way", "Houston", "USA", 789.99, "USD", None),
    ]
    
    cursor.executemany("""
        INSERT OR REPLACE INTO orders 
        (order_id, customer_id, order_date, status, tracking_number, current_location,
         estimated_delivery, shipping_address, shipping_city, shipping_country, 
         total_amount, currency, notes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, orders)
    
    # Order items
    order_items = [
        # ORD-2024-0001 (John Smith - delivered)
        ("ORD-2024-0001", "PP-ROPE-12MM", "Polypropylene Rope 12mm", 25, 3.75, 93.75),
        ("ORD-2024-0001", "HW-SHACKLE-10", "D-Shackle Galvanized 10mm", 10, 5.99, 59.90),
        ("ORD-2024-0001", "HW-THIMBLE-10", "Wire Rope Thimble 10mm", 5, 2.49, 12.45),
        
        # ORD-2024-0015 (John Smith - in transit)
        ("ORD-2024-0015", "NY-ROPE-14MM", "Nylon Rope 14mm", 30, 7.50, 225.00),
        ("ORD-2024-0015", "HW-HOOK-SS-10", "Snap Hook Stainless Steel 10mm", 6, 8.99, 53.94),
        ("ORD-2024-0015", "HW-THIMBLE-10", "Wire Rope Thimble 10mm", 4, 2.49, 9.96),
        
        # ORD-2024-0022 (John Smith - confirmed)
        ("ORD-2024-0022", "SF-HARNESS-PRO", "Full Body Safety Harness - Professional", 2, 149.99, 299.98),
        ("ORD-2024-0022", "SF-HELMET-PRO", "Safety Helmet with Visor", 2, 54.99, 109.98),
        ("ORD-2024-0022", "SF-GLOVES-L", "Work Gloves Leather - Large", 2, 19.99, 39.98),
        
        # ORD-2024-0008 (Sarah Johnson - delivered)
        ("ORD-2024-0008", "SS-CABLE-5MM", "Stainless Steel Cable 5mm 7x19", 50, 7.25, 362.50),
        ("ORD-2024-0008", "HW-TURNBUCKLE", "Turnbuckle Eye-Eye 10mm", 8, 14.99, 119.92),
        ("ORD-2024-0008", "HW-THIMBLE-16", "Wire Rope Thimble 16mm", 10, 3.99, 39.90),
        
        # ORD-2024-0019 (Sarah Johnson - shipped)
        ("ORD-2024-0019", "NY-BAG-M", "Heavy-Duty Nylon Storage Bag Medium", 5, 18.99, 94.95),
        ("ORD-2024-0019", "CV-BAG-TOOL", "Canvas Tool Bag", 2, 34.99, 69.98),
        ("ORD-2024-0019", "SF-GOGGLES", "Safety Goggles Anti-Fog", 9, 14.99, 134.91),
        
        # ORD-2024-0003 (Michael Brown - delivered)
        ("ORD-2024-0003", "NY-ROPE-20MM", "Nylon Rope 20mm", 50, 12.99, 649.50),
        ("ORD-2024-0003", "SS-CABLE-3MM", "Stainless Steel Cable 3mm 7x19", 40, 4.50, 180.00),
        ("ORD-2024-0003", "HW-SHACKLE-16", "D-Shackle Galvanized 16mm", 5, 11.99, 59.95),
        
        # ORD-2024-0012 (Michael Brown - out for delivery)
        ("ORD-2024-0012", "MN-ROPE-12MM", "Manila Rope 12mm", 80, 3.25, 260.00),
        ("ORD-2024-0012", "CV-BAG-ROPE", "Canvas Rope Bag", 3, 29.99, 89.97),
        ("ORD-2024-0012", "HW-CLAMP-8", "Wire Rope Clamp 8mm", 9, 1.99, 17.91),
        
        # ORD-2024-0006 (Emily Davis - delivered)
        ("ORD-2024-0006", "BX-CARD-L", "Heavy-Duty Cardboard Box Large", 100, 4.99, 499.00),
        ("ORD-2024-0006", "BX-CARD-M", "Heavy-Duty Cardboard Box Medium", 150, 3.49, 523.50),
        ("ORD-2024-0006", "TAPE-PACK", "Packing Tape Heavy Duty 48mm", 24, 4.99, 119.76),
        ("ORD-2024-0006", "WRAP-STRETCH", "Stretch Wrap 500mm x 300m", 5, 18.99, 94.95),
        
        # ORD-2024-0021 (Emily Davis - processing)
        ("ORD-2024-0021", "BUBBLE-ROLL", "Bubble Wrap Roll 500mm x 50m", 10, 24.99, 249.90),
        ("ORD-2024-0021", "BX-CARD-S", "Heavy-Duty Cardboard Box Small", 100, 2.29, 229.00),
        ("ORD-2024-0021", "TAPE-PACK", "Packing Tape Heavy Duty 48mm", 18, 4.99, 89.82),
        
        # ORD-2024-0010 (Robert Wilson - delivered)
        ("ORD-2024-0010", "WR-CABLE-8MM", "Wire Rope 8mm 6x19", 200, 5.99, 1198.00),
        ("ORD-2024-0010", "HW-HOOK-SS-12", "Snap Hook Stainless Steel 12mm", 50, 12.99, 649.50),
        ("ORD-2024-0010", "HW-SHACKLE-16", "D-Shackle Galvanized 16mm", 25, 11.99, 299.75),
        
        # ORD-2024-0016 (Robert Wilson - cancelled)
        ("ORD-2024-0016", "SF-HARNESS-STD", "Full Body Safety Harness - Standard", 5, 89.99, 449.95),
        
        # ORD-2024-0023 (Robert Wilson - pending)
        ("ORD-2024-0023", "ST-WIRE-6MM", "Galvanized Steel Wire 6mm", 150, 3.80, 570.00),
        ("ORD-2024-0023", "HW-THIMBLE-16", "Wire Rope Thimble 16mm", 30, 3.99, 119.70),
        ("ORD-2024-0023", "HW-CLAMP-8", "Wire Rope Clamp 8mm", 50, 1.99, 99.50),
    ]
    
    cursor.executemany("""
        INSERT INTO order_items 
        (order_id, product_sku, product_name, quantity, unit_price, total_price)
        VALUES (?, ?, ?, ?, ?, ?)
    """, order_items)
    
    conn.commit()
    conn.close()
    
    print(f"✓ Created customers table with {len(customers)} customers")
    print(f"✓ Created orders table with {len(orders)} orders")
    print(f"✓ Created order_items table with {len(order_items)} line items")


def create_directories():
    """Create necessary directories for file storage."""
    print("Creating directory structure...")
    
    directories = [
        DATABASE_DIR,
        INVOICES_DIR,
        os.path.join(os.path.dirname(DATABASE_DIR), "templates"),
        os.path.join(DATABASE_DIR, "documents"),
        os.path.join(DATABASE_DIR, "vector_dbs"),
        os.path.join(DATABASE_DIR, "reports"),
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
        
        # Check products data
        cursor.execute("SELECT COUNT(*) FROM products")
        count = cursor.fetchone()[0]
        print(f"✓ Found {count} products in database")
        
        # Check orders tables
        for table in ['customers', 'orders', 'order_items']:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            if cursor.fetchone():
                cursor.execute(f"SELECT COUNT(*) FROM {table}")
                count = cursor.fetchone()[0]
                print(f"✓ {table.title()} table exists ({count} records)")
            else:
                print(f"✗ {table.title()} table not found")
                return False
        
        # Show sample products
        cursor.execute("SELECT sku, name, category, unit_price FROM products LIMIT 3")
        print("\nSample products:")
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]} ({row[2]}) - ${row[3]:.2f}")
        
        # Show sample customers
        cursor.execute("SELECT name, email, company FROM customers LIMIT 3")
        print("\nSample customers:")
        for row in cursor.fetchall():
            print(f"  {row[0]} ({row[1]}) - {row[2]}")
        
        # Show sample orders
        cursor.execute("SELECT order_id, status, total_amount FROM orders LIMIT 3")
        print("\nSample orders:")
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]} - ${row[2]:.2f}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"✗ Error verifying setup: {e}")
        return False


def initialize_vector_database():
    """Initialize the vector database for company documents (RAG)."""
    print("\nInitializing vector database for company documents...")
    
    try:
        # Check if documents exist
        docs_dir = os.path.join(DATABASE_DIR, "documents")
        if not os.path.exists(docs_dir):
            os.makedirs(docs_dir)
            print(f"✓ Created {docs_dir} directory")
            print("  Note: Add company documents (.pdf, .txt, .md) to this directory for RAG functionality")
            return True
        
        # Check if there are any documents
        doc_files = [f for f in os.listdir(docs_dir) if f.endswith(('.pdf', '.txt', '.md'))]
        if not doc_files:
            print(f"  Note: No documents found in {docs_dir}")
            print("  Add company documents for RAG functionality")
            return True
        
        # Initialize vector database
        print(f"  Found {len(doc_files)} document(s) to process")
        initialize_company_vector_db()
        print("✓ Vector database initialized successfully")
        
        return True
        
    except Exception as e:
        print(f"✗ Warning: Vector database initialization failed: {e}")
        print("  The system will still work, but RAG-based company document search will not be available")
        return True  # Non-critical, so return True to continue


def main():
    """Main setup function."""
    print("=" * 80)
    print("EMPLOYEE ASSISTANT CHATBOT - COMPLETE DATABASE INITIALIZATION")
    print("=" * 80)
    print()
    
    try:
        # Step 1: Create directories
        create_directories()
        
        # Step 2: Create catalog database
        create_catalog_database()
        
        # Step 3: Create orders database
        create_orders_database()
        
        # Step 4: Initialize vector database
        initialize_vector_database()
        
        # Step 5: Verify setup
        if verify_setup():
            print("\n" + "=" * 80)
            print("INITIALIZATION COMPLETED SUCCESSFULLY!")
            print("=" * 80)
            print("\nNext steps:")
            print("1. Create .env file and add your Google API key:")
            print("   GOOGLE_API_KEY=your_key_here")
            print("2. Install dependencies (if not already done):")
            print("   pip install -r requirements.txt")
            print("3. Start the application:")
            print("   python api.py")
            print("4. Open your browser to:")
            print("   http://localhost:8000")
            print("\n" + "=" * 80)
        else:
            print("\n" + "=" * 80)
            print("INITIALIZATION FAILED!")
            print("=" * 80)
            sys.exit(1)
            
    except Exception as e:
        print(f"\nERROR during initialization: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
