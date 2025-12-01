"""
Report Agent - Handles sales and inventory report generation with PDF output.

This agent provides two tools:
1. generate_sales_report - Sales analytics and revenue reports with PDF + charts
2. generate_inventory_report - Stock levels and inventory status reports with PDF + charts
"""

import sqlite3
import os
import io
from typing import Optional
from datetime import datetime, timedelta
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from langchain.agents import create_agent
from agents.base_agent import BaseAgent
from models.schemas import QueryRequest, AgentResponse
from config import CATALOG_DB_PATH, GOOGLE_API_KEY

# PDF and Chart generation
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT

# Create reports directory if it doesn't exist
REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


class ReportAgent(BaseAgent):
    """Agent for generating sales and inventory reports with PDF output."""
    
    def __init__(self):
        super().__init__(
            name="ReportAgent",
            description="Generates sales analytics and inventory reports as PDFs with charts"
        )
        self.db_path = CATALOG_DB_PATH
        self._setup_agent()
    
    def can_handle(self, query: str) -> bool:
        return True
    
    def _get_db_connection(self):
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _create_pie_chart(self, data: dict, title: str, filename: str) -> str:
        """Create a pie chart and save as image."""
        fig, ax = plt.subplots(figsize=(8, 6))
        labels = list(data.keys())
        values = list(data.values())
        
        # Use nice colors
        colors = plt.cm.Set3(range(len(labels)))
        
        wedges, texts, autotexts = ax.pie(
            values, 
            labels=labels, 
            autopct='%1.1f%%',
            colors=colors,
            startangle=90
        )
        ax.set_title(title, fontsize=14, fontweight='bold')
        
        filepath = os.path.join(REPORTS_DIR, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        return filepath
    
    def _create_bar_chart(self, labels: list, values: list, title: str, ylabel: str, filename: str) -> str:
        """Create a bar chart and save as image."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Truncate long labels
        short_labels = [l[:20] + '...' if len(l) > 20 else l for l in labels]
        
        bars = ax.bar(range(len(values)), values, color=plt.cm.Blues(0.7))
        ax.set_xticks(range(len(short_labels)))
        ax.set_xticklabels(short_labels, rotation=45, ha='right')
        ax.set_ylabel(ylabel)
        ax.set_title(title, fontsize=14, fontweight='bold')
        
        # Add value labels on bars
        for bar, val in zip(bars, values):
            height = bar.get_height()
            ax.annotate(f'${val:,.0f}' if ylabel == 'Revenue ($)' else f'{val:,}',
                       xy=(bar.get_x() + bar.get_width() / 2, height),
                       xytext=(0, 3),
                       textcoords="offset points",
                       ha='center', va='bottom', fontsize=9)
        
        plt.tight_layout()
        filepath = os.path.join(REPORTS_DIR, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        return filepath
    
    def _create_horizontal_bar_chart(self, labels: list, values: list, title: str, xlabel: str, filename: str) -> str:
        """Create a horizontal bar chart and save as image."""
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Truncate long labels
        short_labels = [l[:25] + '...' if len(l) > 25 else l for l in labels]
        
        y_pos = range(len(values))
        bars = ax.barh(y_pos, values, color=plt.cm.Greens(0.6))
        ax.set_yticks(y_pos)
        ax.set_yticklabels(short_labels)
        ax.set_xlabel(xlabel)
        ax.set_title(title, fontsize=14, fontweight='bold')
        ax.invert_yaxis()  # Top item first
        
        # Add value labels
        for bar, val in zip(bars, values):
            width = bar.get_width()
            ax.annotate(f'{val:,}',
                       xy=(width, bar.get_y() + bar.get_height() / 2),
                       xytext=(3, 0),
                       textcoords="offset points",
                       ha='left', va='center', fontsize=9)
        
        plt.tight_layout()
        filepath = os.path.join(REPORTS_DIR, filename)
        plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
        plt.close()
        return filepath
    
    def _setup_agent(self):
        """Set up the LangChain agent with tools."""
        
        @tool
        def generate_sales_report(
            period: str = "30days",
            category: Optional[str] = None
        ) -> str:
            """
            Generate a sales analytics report as PDF with charts.
            
            Args:
                period: Time period for the report - "7days", "30days", "90days", or "all"
                category: Optional product category filter (e.g., "Ropes", "Wire", "Bags", "Safety", "Packaging")
                
            Returns:
                Path to the generated PDF report with sales data and visualizations
            """
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            try:
                # Calculate date range
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
                
                # Build category filter
                category_filter = ""
                params = [start_date_str]
                if category:
                    category_filter = "AND p.category = ?"
                    params.append(category)
                
                # Total revenue and orders
                cursor.execute(f"""
                    SELECT 
                        COUNT(DISTINCT o.order_id) as total_orders,
                        SUM(o.total_amount) as total_revenue,
                        AVG(o.total_amount) as avg_order_value
                    FROM orders o
                    WHERE o.order_date >= ?
                """, (start_date_str,))
                
                summary = cursor.fetchone()
                total_orders = summary['total_orders'] or 0
                total_revenue = summary['total_revenue'] or 0
                avg_order_value = summary['avg_order_value'] or 0
                
                # Orders by status
                cursor.execute(f"""
                    SELECT status, COUNT(*) as count
                    FROM orders
                    WHERE order_date >= ?
                    GROUP BY status
                    ORDER BY count DESC
                """, (start_date_str,))
                
                status_breakdown = cursor.fetchall()
                
                # Top selling products
                cursor.execute(f"""
                    SELECT 
                        oi.product_name,
                        p.category,
                        SUM(oi.quantity) as total_quantity,
                        SUM(oi.total_price) as total_revenue
                    FROM order_items oi
                    JOIN orders o ON oi.order_id = o.order_id
                    JOIN products p ON oi.product_sku = p.sku
                    WHERE o.order_date >= ?
                    {category_filter}
                    GROUP BY oi.product_sku
                    ORDER BY total_revenue DESC
                    LIMIT 5
                """, params)
                
                top_products = cursor.fetchall()
                
                # Revenue by category
                cursor.execute(f"""
                    SELECT 
                        p.category,
                        SUM(oi.total_price) as category_revenue,
                        SUM(oi.quantity) as total_units
                    FROM order_items oi
                    JOIN orders o ON oi.order_id = o.order_id
                    JOIN products p ON oi.product_sku = p.sku
                    WHERE o.order_date >= ?
                    GROUP BY p.category
                    ORDER BY category_revenue DESC
                """, (start_date_str,))
                
                category_breakdown = cursor.fetchall()
                
                # Top customers
                cursor.execute(f"""
                    SELECT 
                        c.name,
                        c.company,
                        COUNT(o.order_id) as order_count,
                        SUM(o.total_amount) as total_spent
                    FROM orders o
                    JOIN customers c ON o.customer_id = c.customer_id
                    WHERE o.order_date >= ?
                    GROUP BY c.customer_id
                    ORDER BY total_spent DESC
                    LIMIT 5
                """, (start_date_str,))
                
                top_customers = cursor.fetchall()
                
                # Generate charts
                timestamp = now.strftime("%Y%m%d_%H%M%S")
                
                # 1. Revenue by Category Pie Chart
                if category_breakdown:
                    cat_data = {row['category']: row['category_revenue'] for row in category_breakdown}
                    pie_chart_path = self._create_pie_chart(
                        cat_data, 
                        "Revenue by Category", 
                        f"sales_pie_{timestamp}.png"
                    )
                else:
                    pie_chart_path = None
                
                # 2. Top Products Bar Chart
                if top_products:
                    product_labels = [p['product_name'] for p in top_products]
                    product_values = [p['total_revenue'] for p in top_products]
                    bar_chart_path = self._create_bar_chart(
                        product_labels,
                        product_values,
                        "Top 5 Products by Revenue",
                        "Revenue ($)",
                        f"sales_bar_{timestamp}.png"
                    )
                else:
                    bar_chart_path = None
                
                # 3. Order Status Pie Chart
                if status_breakdown:
                    status_data = {row['status'].replace('_', ' ').title(): row['count'] for row in status_breakdown}
                    status_chart_path = self._create_pie_chart(
                        status_data,
                        "Orders by Status",
                        f"sales_status_{timestamp}.png"
                    )
                else:
                    status_chart_path = None
                
                # Create PDF
                category_label = f"_{category}" if category else ""
                pdf_filename = f"sales_report{category_label}_{timestamp}.pdf"
                pdf_path = os.path.join(REPORTS_DIR, pdf_filename)
                
                doc = SimpleDocTemplate(pdf_path, pagesize=letter)
                styles = getSampleStyleSheet()
                
                # Custom styles
                title_style = ParagraphStyle(
                    'CustomTitle',
                    parent=styles['Title'],
                    fontSize=24,
                    spaceAfter=30,
                    textColor=colors.HexColor('#2E86AB')
                )
                heading_style = ParagraphStyle(
                    'CustomHeading',
                    parent=styles['Heading2'],
                    fontSize=16,
                    spaceAfter=12,
                    textColor=colors.HexColor('#A23B72')
                )
                
                elements = []
                
                # Title
                title = f"Sales Report{' - ' + category if category else ''}"
                elements.append(Paragraph(title, title_style))
                elements.append(Paragraph(f"Period: {period_label} | Generated: {now.strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
                elements.append(Spacer(1, 20))
                
                # Summary Table
                elements.append(Paragraph("Revenue Summary", heading_style))
                summary_data = [
                    ['Metric', 'Value'],
                    ['Total Orders', str(total_orders)],
                    ['Total Revenue', f'${total_revenue:,.2f}'],
                    ['Average Order Value', f'${avg_order_value:,.2f}']
                ]
                summary_table = Table(summary_data, colWidths=[3*inch, 3*inch])
                summary_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E86AB')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F0F0F0')),
                    ('GRID', (0, 0), (-1, -1), 1, colors.white),
                ]))
                elements.append(summary_table)
                elements.append(Spacer(1, 20))
                
                # Category Revenue Chart
                if pie_chart_path and os.path.exists(pie_chart_path):
                    elements.append(Paragraph("Revenue Distribution by Category", heading_style))
                    elements.append(Image(pie_chart_path, width=5*inch, height=4*inch))
                    elements.append(Spacer(1, 20))
                
                # Top Products Chart
                if bar_chart_path and os.path.exists(bar_chart_path):
                    elements.append(Paragraph("Top 5 Products by Revenue", heading_style))
                    elements.append(Image(bar_chart_path, width=6*inch, height=4*inch))
                    elements.append(Spacer(1, 20))
                
                # Order Status Chart
                if status_chart_path and os.path.exists(status_chart_path):
                    elements.append(Paragraph("Order Status Distribution", heading_style))
                    elements.append(Image(status_chart_path, width=5*inch, height=4*inch))
                    elements.append(Spacer(1, 20))
                
                # Top Products Table
                if top_products:
                    elements.append(Paragraph("Top 5 Products Details", heading_style))
                    products_data = [['Product', 'Category', 'Units Sold', 'Revenue']]
                    for p in top_products:
                        products_data.append([
                            p['product_name'][:30],
                            p['category'],
                            str(p['total_quantity']),
                            f"${p['total_revenue']:,.2f}"
                        ])
                    products_table = Table(products_data, colWidths=[2.5*inch, 1.5*inch, 1*inch, 1.5*inch])
                    products_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#A23B72')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FFF5F5')),
                        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#DDDDDD')),
                    ]))
                    elements.append(products_table)
                    elements.append(Spacer(1, 20))
                
                # Top Customers Table
                if top_customers:
                    elements.append(Paragraph("Top 5 Customers", heading_style))
                    customers_data = [['Name', 'Company', 'Orders', 'Total Spent']]
                    for c in top_customers:
                        customers_data.append([
                            c['name'],
                            c['company'][:20],
                            str(c['order_count']),
                            f"${c['total_spent']:,.2f}"
                        ])
                    customers_table = Table(customers_data, colWidths=[2*inch, 2*inch, 1*inch, 1.5*inch])
                    customers_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E86AB')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F5FEFF')),
                        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#DDDDDD')),
                    ]))
                    elements.append(customers_table)
                
                # Build PDF
                doc.build(elements)
                
                # Clean up chart images
                for chart_path in [pie_chart_path, bar_chart_path, status_chart_path]:
                    if chart_path and os.path.exists(chart_path):
                        try:
                            os.remove(chart_path)
                        except:
                            pass
                
                # Return summary + path
                result = f"""
📊 **Sales Report Generated Successfully!**

**PDF Location:** `{pdf_path}`

---

## Quick Summary

| Metric | Value |
|--------|-------|
| Period | {period_label} |
| Total Orders | {total_orders} |
| Total Revenue | ${total_revenue:,.2f} |
| Average Order Value | ${avg_order_value:,.2f} |

The PDF report includes:
✅ Revenue summary table
✅ Revenue by category pie chart
✅ Top 5 products bar chart
✅ Order status distribution chart
✅ Detailed products and customers tables

Open the PDF file to view the complete report with visualizations!
"""
                return result
                
            except Exception as e:
                return f"Error generating sales report: {str(e)}"
            finally:
                conn.close()
        
        @tool
        def generate_inventory_report(
            category: Optional[str] = None,
            low_stock_threshold: int = 100
        ) -> str:
            """
            Generate an inventory status report as PDF with charts.
            
            Args:
                category: Optional product category filter (e.g., "Ropes", "Wire", "Bags", "Safety", "Packaging")
                low_stock_threshold: Quantity threshold to flag as low stock (default: 100)
                
            Returns:
                Path to the generated PDF report with inventory data and visualizations
            """
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            try:
                now = datetime.now()
                
                # Build category filter
                category_filter = ""
                params = []
                if category:
                    category_filter = "WHERE category = ?"
                    params.append(category)
                
                # Overall inventory summary
                cursor.execute(f"""
                    SELECT 
                        COUNT(*) as total_products,
                        SUM(quantity_on_hand) as total_units,
                        SUM(quantity_on_hand * unit_price) as total_value
                    FROM products
                    {category_filter}
                """, params)
                
                summary = cursor.fetchone()
                total_products = summary['total_products'] or 0
                total_units = summary['total_units'] or 0
                total_value = summary['total_value'] or 0
                
                # Inventory by category
                cursor.execute("""
                    SELECT 
                        category,
                        COUNT(*) as product_count,
                        SUM(quantity_on_hand) as total_stock,
                        SUM(quantity_on_hand * unit_price) as stock_value
                    FROM products
                    GROUP BY category
                    ORDER BY stock_value DESC
                """)
                
                category_breakdown = cursor.fetchall()
                
                # Low stock items
                low_stock_filter = f"WHERE quantity_on_hand < ?" if not category else f"WHERE quantity_on_hand < ? AND category = ?"
                low_stock_params = [low_stock_threshold] if not category else [low_stock_threshold, category]
                
                cursor.execute(f"""
                    SELECT sku, name, category, quantity_on_hand, unit_price
                    FROM products
                    {low_stock_filter}
                    ORDER BY quantity_on_hand ASC
                """, low_stock_params)
                
                low_stock_items = cursor.fetchall()
                
                # High stock items (top 5)
                cursor.execute(f"""
                    SELECT sku, name, category, quantity_on_hand, unit_price
                    FROM products
                    {category_filter}
                    ORDER BY quantity_on_hand DESC
                    LIMIT 5
                """, params)
                
                high_stock_items = cursor.fetchall()
                
                # Most valuable inventory items
                cursor.execute(f"""
                    SELECT sku, name, category, quantity_on_hand, unit_price,
                           (quantity_on_hand * unit_price) as stock_value
                    FROM products
                    {category_filter}
                    ORDER BY stock_value DESC
                    LIMIT 5
                """, params)
                
                valuable_items = cursor.fetchall()
                
                # Generate charts
                timestamp = now.strftime("%Y%m%d_%H%M%S")
                
                # 1. Stock by Category Pie Chart
                if category_breakdown:
                    cat_stock_data = {row['category']: row['total_stock'] for row in category_breakdown}
                    stock_pie_path = self._create_pie_chart(
                        cat_stock_data,
                        "Stock Distribution by Category",
                        f"inventory_stock_pie_{timestamp}.png"
                    )
                else:
                    stock_pie_path = None
                
                # 2. Inventory Value by Category Bar Chart
                if category_breakdown:
                    cat_labels = [row['category'] for row in category_breakdown]
                    cat_values = [row['stock_value'] for row in category_breakdown]
                    value_bar_path = self._create_bar_chart(
                        cat_labels,
                        cat_values,
                        "Inventory Value by Category",
                        "Value ($)",
                        f"inventory_value_bar_{timestamp}.png"
                    )
                else:
                    value_bar_path = None
                
                # 3. Top 5 Products by Stock Level
                if high_stock_items:
                    product_labels = [item['name'] for item in high_stock_items]
                    product_values = [item['quantity_on_hand'] for item in high_stock_items]
                    stock_bar_path = self._create_horizontal_bar_chart(
                        product_labels,
                        product_values,
                        "Top 5 Products by Stock Level",
                        "Units in Stock",
                        f"inventory_top_stock_{timestamp}.png"
                    )
                else:
                    stock_bar_path = None
                
                # Create PDF
                category_label = f"_{category}" if category else ""
                pdf_filename = f"inventory_report{category_label}_{timestamp}.pdf"
                pdf_path = os.path.join(REPORTS_DIR, pdf_filename)
                
                doc = SimpleDocTemplate(pdf_path, pagesize=letter)
                styles = getSampleStyleSheet()
                
                # Custom styles
                title_style = ParagraphStyle(
                    'CustomTitle',
                    parent=styles['Title'],
                    fontSize=24,
                    spaceAfter=30,
                    textColor=colors.HexColor('#2E7D32')
                )
                heading_style = ParagraphStyle(
                    'CustomHeading',
                    parent=styles['Heading2'],
                    fontSize=16,
                    spaceAfter=12,
                    textColor=colors.HexColor('#1565C0')
                )
                alert_style = ParagraphStyle(
                    'AlertStyle',
                    parent=styles['Heading2'],
                    fontSize=16,
                    spaceAfter=12,
                    textColor=colors.HexColor('#C62828')
                )
                
                elements = []
                
                # Title
                title = f"Inventory Report{' - ' + category if category else ''}"
                elements.append(Paragraph(title, title_style))
                elements.append(Paragraph(f"Generated: {now.strftime('%Y-%m-%d %H:%M')} | Low Stock Threshold: {low_stock_threshold} units", styles['Normal']))
                elements.append(Spacer(1, 20))
                
                # Summary Table
                elements.append(Paragraph("Inventory Summary", heading_style))
                summary_data = [
                    ['Metric', 'Value'],
                    ['Total Products', str(total_products)],
                    ['Total Units in Stock', f'{total_units:,}'],
                    ['Total Inventory Value', f'${total_value:,.2f}']
                ]
                summary_table = Table(summary_data, colWidths=[3*inch, 3*inch])
                summary_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E7D32')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, 0), 12),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                    ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#E8F5E9')),
                    ('GRID', (0, 0), (-1, -1), 1, colors.white),
                ]))
                elements.append(summary_table)
                elements.append(Spacer(1, 20))
                
                # Stock Distribution Chart
                if stock_pie_path and os.path.exists(stock_pie_path):
                    elements.append(Paragraph("Stock Distribution by Category", heading_style))
                    elements.append(Image(stock_pie_path, width=5*inch, height=4*inch))
                    elements.append(Spacer(1, 20))
                
                # Inventory Value Chart
                if value_bar_path and os.path.exists(value_bar_path):
                    elements.append(Paragraph("Inventory Value by Category", heading_style))
                    elements.append(Image(value_bar_path, width=6*inch, height=4*inch))
                    elements.append(Spacer(1, 20))
                
                # Top Stock Chart
                if stock_bar_path and os.path.exists(stock_bar_path):
                    elements.append(Paragraph("Top 5 Products by Stock Level", heading_style))
                    elements.append(Image(stock_bar_path, width=6*inch, height=4*inch))
                    elements.append(Spacer(1, 20))
                
                # Low Stock Alert Table
                elements.append(Paragraph(f"⚠️ Low Stock Alert ({len(low_stock_items)} items below {low_stock_threshold} units)", alert_style))
                if low_stock_items:
                    low_stock_data = [['SKU', 'Product', 'Category', 'Stock', 'Status']]
                    for item in low_stock_items[:10]:  # Limit to 10 items
                        status = "CRITICAL" if item['quantity_on_hand'] < 50 else "LOW"
                        low_stock_data.append([
                            item['sku'],
                            item['name'][:25],
                            item['category'],
                            str(item['quantity_on_hand']),
                            status
                        ])
                    low_stock_table = Table(low_stock_data, colWidths=[1.2*inch, 2*inch, 1.2*inch, 0.8*inch, 1*inch])
                    low_stock_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#C62828')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#FFEBEE')),
                        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#DDDDDD')),
                    ]))
                    elements.append(low_stock_table)
                else:
                    elements.append(Paragraph("✅ No items below the low stock threshold!", styles['Normal']))
                elements.append(Spacer(1, 20))
                
                # Category Breakdown Table
                if category_breakdown:
                    elements.append(Paragraph("Stock by Category", heading_style))
                    cat_data = [['Category', 'Products', 'Units', 'Value']]
                    for cat in category_breakdown:
                        cat_data.append([
                            cat['category'],
                            str(cat['product_count']),
                            f"{cat['total_stock']:,}",
                            f"${cat['stock_value']:,.2f}"
                        ])
                    cat_table = Table(cat_data, colWidths=[2*inch, 1.5*inch, 1.5*inch, 1.5*inch])
                    cat_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1565C0')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#E3F2FD')),
                        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#DDDDDD')),
                    ]))
                    elements.append(cat_table)
                    elements.append(Spacer(1, 20))
                
                # Most Valuable Inventory Table
                if valuable_items:
                    elements.append(Paragraph("Most Valuable Inventory (Top 5)", heading_style))
                    valuable_data = [['Product', 'Units', 'Unit Price', 'Total Value']]
                    for item in valuable_items:
                        stock_value = item['quantity_on_hand'] * item['unit_price']
                        valuable_data.append([
                            item['name'][:30],
                            str(item['quantity_on_hand']),
                            f"${item['unit_price']:.2f}",
                            f"${stock_value:,.2f}"
                        ])
                    valuable_table = Table(valuable_data, colWidths=[2.5*inch, 1*inch, 1.25*inch, 1.75*inch])
                    valuable_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#7B1FA2')),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 10),
                        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#F3E5F5')),
                        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#DDDDDD')),
                    ]))
                    elements.append(valuable_table)
                
                # Build PDF
                doc.build(elements)
                
                # Clean up chart images
                for chart_path in [stock_pie_path, value_bar_path, stock_bar_path]:
                    if chart_path and os.path.exists(chart_path):
                        try:
                            os.remove(chart_path)
                        except:
                            pass
                
                # Return summary + path
                result = f"""
📦 **Inventory Report Generated Successfully!**

**PDF Location:** `{pdf_path}`

---

## Quick Summary

| Metric | Value |
|--------|-------|
| Total Products | {total_products} |
| Total Units in Stock | {total_units:,} |
| Total Inventory Value | ${total_value:,.2f} |
| Low Stock Items | {len(low_stock_items)} (below {low_stock_threshold} units) |

The PDF report includes:
✅ Inventory summary table
✅ Stock distribution pie chart
✅ Inventory value by category bar chart
✅ Top products by stock level chart
✅ Low stock alert table
✅ Category breakdown table
✅ Most valuable inventory items

Open the PDF file to view the complete report with visualizations!
"""
                return result
                
            except Exception as e:
                return f"Error generating inventory report: {str(e)}"
            finally:
                conn.close()
        
        # Store tools
        self.tools = [generate_sales_report, generate_inventory_report]
        
        # Create the LLM
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            google_api_key=GOOGLE_API_KEY,
            temperature=0.3
        )
        
        # System prompt for the agent
        system_prompt = """You are a Report Generation Assistant for a warehouse supply company.

Your role is to generate business reports as professional PDF documents with charts and visualizations.

You have access to two tools:
1. **generate_sales_report**: Generates a PDF report with sales analytics, revenue charts, top products bar graph, and customer insights
   - Parameters: period ("7days", "30days", "90days", "all"), category (optional)
   - Output: PDF file with pie charts, bar charts, and data tables
   
2. **generate_inventory_report**: Generates a PDF report with stock levels, inventory charts, and low stock alerts
   - Parameters: category (optional), low_stock_threshold (default: 100)
   - Output: PDF file with stock distribution charts, value graphs, and alert tables

IMPORTANT INSTRUCTIONS:
- When the user asks for a "sales report" → Call generate_sales_report immediately with default parameters (period="30days")
- When the user asks for an "inventory report" → Call generate_inventory_report immediately with default parameters
- If the user specifies a time period like "all time", "last 7 days", "30 days" → Use that as the period parameter
- If the user says "all" or "all time" → Use period="all"
- DO NOT keep asking clarifying questions. Use sensible defaults and generate the report.
- After generating, tell the user where the PDF was saved.

Default behavior:
- If no period specified for sales → Use "30days"
- If no category specified → Don't filter by category (leave it as None)
- If no threshold specified for inventory → Use 100"""
        
        # Create agent using langchain
        self.agent = create_agent(llm, self.tools, system_prompt=system_prompt)
    
    async def process(self, query: str, context: dict = None) -> dict:
        """
        Process a report generation query.
        
        Args:
            query: The user's query about reports
            context: Optional context with chat history
            
        Returns:
            dict with response and metadata
        """
        try:
            # Build messages with conversation history for context
            messages = []
            
            # Add conversation history if available
            if context and context.get("history"):
                for msg in context["history"][-6:]:  # Last 6 messages for context
                    role = msg.get("role", "user")
                    content = msg.get("content", "")
                    if role == "user":
                        messages.append({"role": "user", "content": content})
                    else:
                        messages.append({"role": "assistant", "content": content})
            
            # Add current query
            messages.append({"role": "user", "content": query})
            
            # Invoke the agent with messages format
            result = await self.agent.ainvoke({
                "messages": messages
            })
            
            # Extract the output from messages
            result_messages = result.get("messages", [])
            if result_messages:
                last_message = result_messages[-1]
                response = last_message.content if hasattr(last_message, 'content') else str(last_message)
            else:
                response = "I couldn't generate the report."
            
            return {
                "success": True,
                "response": response,
                "agent": self.name,
                "tools_used": ["generate_sales_report", "generate_inventory_report"]
            }
            
        except Exception as e:
            print(f"[ReportAgent] Error: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "success": False,
                "response": f"I encountered an error while generating the report: {str(e)}",
                "agent": self.name,
                "error": str(e)
            }
    
    async def process_query(self, request: QueryRequest) -> AgentResponse:
        """Process a report query - required by BaseAgent."""
        # Pass metadata context to process
        context = request.metadata if request.metadata else {}
        result = await self.process(request.query, context)
        return AgentResponse(
            agent_name=self.name,
            response=result.get("response", ""),
            success=result.get("success", False),
            data=result
        )


# For testing
if __name__ == "__main__":
    import asyncio
    from models.schemas import QueryRequest
    
    async def test_agent():
        agent = ReportAgent()
        
        # Test sales report
        print("\n=== Test 1: Sales Report ===")
        request = QueryRequest(query="Generate a sales report for the last 30 days")
        result = await agent.process_query(request)
        print(result.response)
        
        # Test inventory report
        print("\n=== Test 2: Inventory Report ===")
        request = QueryRequest(query="Show me the inventory report with low stock items")
        result = await agent.process_query(request)
        print(result.response)
    
    asyncio.run(test_agent())
