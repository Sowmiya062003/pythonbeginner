"""
Doraemon 21st Cen Eateries - Restaurant Order Collecting Application
Enterprise Desktop GUI with MSSQL persistence, image cards, dynamic cart,
and ReportLab PDF bill generation.

Modules / Classes:
- DBConnector: Connects to MSSQL, creates schema, handles atomic transactions.
- MenuLoader: Scans image directory, categorizes food items by filename hyphens.
- BillGenerator: Creates professional PDF receipts with restaurant logo.
- UIManager: Main Tkinter GUI application.
"""

import os
import re
import sys
import glob
import datetime
import random
import tkinter as tk
from tkinter import ttk, messagebox

# Third-party imports with fallback handling
try:
    import pyodbc
    HAS_PYODBC = True
except ImportError:
    HAS_PYODBC = False

try:
    from PIL import Image, ImageTk
    HAS_PIL = True
except ImportError:
    HAS_PIL = False

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = False


# ==============================================================================
# 1. DATABASE CONNECTOR CLASS (MSSQL)
# ==============================================================================
class DBConnector:
    """Handles Microsoft SQL Server database operations and atomic order logging."""
    
    def __init__(self, server=".\\SQLEXPRESS", database="DoraemonEateriesDB"):
        self.server = server
        self.database = database
        self.conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={self.server};"
            f"DATABASE={self.database};"
            f"Trusted_Connection=yes;"
            f"TrustServerCertificate=yes;"
        )
        self.master_conn_str = (
            f"DRIVER={{ODBC Driver 17 for SQL Server}};"
            f"SERVER={self.server};"
            f"DATABASE=master;"
            f"Trusted_Connection=yes;"
            f"TrustServerCertificate=yes;"
        )
        self.connected = False
        self.init_database()

    def init_database(self):
        """Ensures database and required tables exist in MSSQL Server."""
        if not HAS_PYODBC:
            print("[Warning] pyodbc not installed. Running in offline DB mode.")
            return

        try:
            # 1. Ensure Database Exists
            with pyodbc.connect(self.master_conn_str, autocommit=True, timeout=5) as conn:
                with conn.cursor() as cursor:
                    cursor.execute(
                        f"IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = '{self.database}') "
                        f"CREATE DATABASE [{self.database}];"
                    )

            # 2. Ensure Tables Exist
            with pyodbc.connect(self.conn_str, autocommit=True, timeout=5) as conn:
                with conn.cursor() as cursor:
                    # MenuItems Table
                    cursor.execute("""
                        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'MenuItems')
                        CREATE TABLE MenuItems (
                            ItemID INT IDENTITY(1,1) PRIMARY KEY,
                            ItemName NVARCHAR(100) NOT NULL UNIQUE,
                            Category NVARCHAR(50) NOT NULL,
                            ImagePath NVARCHAR(260) NOT NULL,
                            Price DECIMAL(10,2) NOT NULL,
                            FileType NVARCHAR(20),
                            FileSize BIGINT
                        );
                    """)
                    
                    # Orders Table
                    cursor.execute("""
                        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'Orders')
                        CREATE TABLE Orders (
                            OrderID INT IDENTITY(1,1) PRIMARY KEY,
                            BillNumber NVARCHAR(100) NOT NULL UNIQUE,
                            CustomerName NVARCHAR(100) NOT NULL,
                            TableNumber NVARCHAR(50) NOT NULL,
                            OrderDate DATETIME NOT NULL,
                            TotalAmount DECIMAL(10,2) NOT NULL
                        );
                    """)

                    # OrderDetails Table
                    cursor.execute("""
                        IF NOT EXISTS (SELECT * FROM sys.tables WHERE name = 'OrderDetails')
                        CREATE TABLE OrderDetails (
                            OrderDetailID INT IDENTITY(1,1) PRIMARY KEY,
                            OrderID INT NOT NULL FOREIGN KEY REFERENCES Orders(OrderID) ON DELETE CASCADE,
                            ItemName NVARCHAR(100) NOT NULL,
                            Quantity INT NOT NULL,
                            Price DECIMAL(10,2) NOT NULL
                        );
                    """)
            
            self.connected = True
            print(f"[DB] Successfully initialized MSSQL Database '{self.database}'.")
        except Exception as e:
            print(f"[DB Error] Failed to connect to MSSQL Server: {e}")
            self.connected = False

    def upsert_menu_item(self, item_name, category, image_path, price, file_type, file_size):
        """Inserts or updates a menu item record in MSSQL."""
        if not self.connected:
            return

        try:
            with pyodbc.connect(self.conn_str, autocommit=True) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        IF EXISTS (SELECT 1 FROM MenuItems WHERE ItemName = ?)
                            UPDATE MenuItems 
                            SET Category = ?, ImagePath = ?, Price = ?, FileType = ?, FileSize = ?
                            WHERE ItemName = ?
                        ELSE
                            INSERT INTO MenuItems (ItemName, Category, ImagePath, Price, FileType, FileSize)
                            VALUES (?, ?, ?, ?, ?, ?)
                    """, (item_name, category, image_path, price, file_type, file_size, item_name,
                          item_name, category, image_path, price, file_type, file_size))
        except Exception as e:
            print(f"[DB Error] Error upserting menu item '{item_name}': {e}")

    def fetch_menu_items(self):
        """Fetches all menu items from MSSQL database."""
        if not self.connected:
            return []

        items = []
        try:
            with pyodbc.connect(self.conn_str) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT ItemName, Category, ImagePath, Price FROM MenuItems ORDER BY Category, ItemName")
                    rows = cursor.fetchall()
                    for r in rows:
                        items.append({
                            "name": r[0],
                            "category": r[1],
                            "image_path": r[2],
                            "price": float(r[3])
                        })
        except Exception as e:
            print(f"[DB Error] Error fetching menu items: {e}")
        return items

    def save_order_transaction(self, bill_number, customer_name, table_number, total_amount, order_items):
        """
        Saves Order and OrderDetails in an atomic transaction (commit/rollback).
        order_items is a list of tuples: [(dish_name, quantity, price), ...]
        """
        if not self.connected:
            return True  # Allow offline UI operation

        conn = None
        try:
            conn = pyodbc.connect(self.conn_str, autocommit=False)
            cursor = conn.cursor()

            # Insert Order Record
            cursor.execute("""
                INSERT INTO Orders (BillNumber, CustomerName, TableNumber, OrderDate, TotalAmount)
                OUTPUT INSERTED.OrderID
                VALUES (?, ?, ?, GETDATE(), ?)
            """, (bill_number, customer_name, table_number, total_amount))
            
            order_id = cursor.fetchone()[0]

            # Insert Order Details Records
            for dish_name, qty, unit_price in order_items:
                cursor.execute("""
                    INSERT INTO OrderDetails (OrderID, ItemName, Quantity, Price)
                    VALUES (?, ?, ?, ?)
                """, (order_id, dish_name, qty, unit_price))

            # Commit Atomic Transaction
            conn.commit()
            print(f"[DB] Transaction committed successfully for Order #{order_id} (Bill: {bill_number}).")
            return True

        except Exception as e:
            if conn:
                conn.rollback()
            print(f"[DB Transaction Error] Rollback executed for Bill {bill_number}: {e}")
            raise e
        finally:
            if conn:
                conn.close()


# ==============================================================================
# 2. MENU LOADER CLASS (IMAGE PROCESSING & CATEGORIZATION)
# ==============================================================================
class MenuLoader:
    """Scans image folder, extracts metadata, categorizes items, and seeds DB."""

    # Standard default prices by category keyword
    DEFAULT_PRICES = {
        "pizza": 250.0,
        "burger": 150.0,
        "roll": 120.0,
        "icecream": 100.0,
        "dessert": 140.0,
        "beverage": 90.0
    }

    def __init__(self, db_connector, search_dirs=None):
        self.db = db_connector
        if search_dirs is None:
            self.search_dirs = [
                os.path.join(os.path.dirname(__file__), "IMAGES"),
                os.path.join(os.path.dirname(__file__), "images"),
                "c:\\Users\\Itsme\\PyCharmMiscProject\\IMAGES",
                "IMAGES"
            ]
        else:
            self.search_dirs = search_dirs

        self.image_dir = self.locate_image_directory()
        self.logo_path = None
        self.menu_items = []
        self.scan_and_populate()

    def locate_image_directory(self):
        """Finds valid IMAGES directory containing files."""
        for d in self.search_dirs:
            if os.path.exists(d) and os.path.isdir(d):
                files = os.listdir(d)
                if any(f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')) for f in files):
                    return os.path.abspath(d)
        return None

    def scan_and_populate(self):
        """Scans image folder and seeds MenuItems DB table."""
        if not self.image_dir:
            print("[MenuLoader Warning] No IMAGES directory found. Creating default items.")
            return

        all_files = os.listdir(self.image_dir)

        # 1. Locate Logo File
        for f in all_files:
            if "logo" in f.lower() and f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                self.logo_path = os.path.join(self.image_dir, f)
                break

        # 2. Parse Food Images
        for f in all_files:
            if "logo" in f.lower() or not f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                continue

            full_path = os.path.join(self.image_dir, f)
            file_type = os.path.splitext(f)[1].replace('.', '').upper()
            file_size = os.path.getsize(full_path)

            # Categorize food items based on naming convention:
            # Word after hyphen (-) represents category
            # Example: "Egg roll- Roll.webp" -> ItemName="Egg roll", Category="Roll"
            name_without_ext = os.path.splitext(f)[0]
            
            # Normalize non-breaking hyphens or normal hyphens
            normalized = name_without_ext.replace('‑', '-').replace('_', ' ')

            if '-' in normalized:
                parts = normalized.split('-', 1)
                raw_name = parts[0].strip().title()
                raw_cat = parts[1].strip().capitalize()
            else:
                raw_name = normalized.strip().title()
                raw_cat = "General"

            # Determine price based on category
            cat_key = raw_cat.lower()
            price = self.DEFAULT_PRICES.get(cat_key, 120.0)

            item = {
                "name": raw_name,
                "category": raw_cat,
                "image_path": full_path,
                "price": price,
                "file_type": file_type,
                "file_size": file_size
            }
            self.menu_items.append(item)

            # Seed into MSSQL Database
            if self.db and self.db.connected:
                self.db.upsert_menu_item(raw_name, raw_cat, full_path, price, file_type, file_size)

        # Fetch synced items from DB if connected
        if self.db and self.db.connected:
            db_items = self.db.fetch_menu_items()
            if db_items:
                self.menu_items = db_items


# ==============================================================================
# 3. BILL GENERATOR CLASS (REPORTLAB PDF CREATION)
# ==============================================================================
class BillGenerator:
    """Generates professionally styled PDF bills using ReportLab."""

    RESTAURANT_NAME = "Doraemon 21st Cen Eateries"

    @staticmethod
    def generate_pdf(bill_number, customer_name, table_number, order_summary, total_amount, logo_path):
        """
        Creates a PDF bill saved as Bill_<BillNumber>_<CustomerName>_<TableNumber>.pdf
        """
        clean_name = re.sub(r'[^a-zA-Z0-9]', '', customer_name)
        clean_table = re.sub(r'[^a-zA-Z0-9]', '', table_number)
        filename = f"Bill_{bill_number}_{clean_name}_T{clean_table}.pdf"
        filepath = os.path.abspath(filename)

        if not HAS_REPORTLAB:
            print("[PDF Error] ReportLab library is missing. Falling back to text bill.")
            return BillGenerator.generate_text_fallback(filepath.replace('.pdf', '.txt'), bill_number, customer_name, table_number, order_summary, total_amount)

        doc = SimpleDocTemplate(filepath, pagesize=letter, leftMargin=36, rightMargin=36, topMargin=36, bottomMargin=36)
        story = []

        styles = getSampleStyleSheet()

        title_style = ParagraphStyle(
            'TitleStyle',
            parent=styles['Heading1'],
            fontName='Helvetica-Bold',
            fontSize=20,
            textColor=colors.HexColor('#2C3E50'),
            alignment=1,  # Centered
            spaceAfter=6
        )

        subtitle_style = ParagraphStyle(
            'SubTitleStyle',
            parent=styles['Normal'],
            fontName='Helvetica-Oblique',
            fontSize=10,
            textColor=colors.HexColor('#7F8C8D'),
            alignment=1,
            spaceAfter=15
        )

        meta_style = ParagraphStyle(
            'MetaStyle',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=10,
            textColor=colors.HexColor('#34495E'),
            leading=14
        )

        # Header Block with Logo & Title
        header_data = []

        if logo_path and os.path.exists(logo_path) and HAS_PIL:
            try:
                logo_img = RLImage(logo_path, width=70, height=70)
                header_text = Paragraph(f"<b>{BillGenerator.RESTAURANT_NAME}</b><br/><font size=9 color='#7F8C8D'>21st Century Taste & Quality Guaranteed</font>", title_style)
                header_data = [[logo_img, header_text]]
            except Exception:
                header_text = Paragraph(f"<b>{BillGenerator.RESTAURANT_NAME}</b>", title_style)
                header_data = [[header_text]]
        else:
            header_text = Paragraph(f"<b>{BillGenerator.RESTAURANT_NAME}</b>", title_style)
            header_data = [[header_text]]

        header_table = Table(header_data, colWidths=[80, 440] if len(header_data[0]) > 1 else [520])
        header_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ]))
        story.append(header_table)
        story.append(Spacer(1, 15))

        # Horizontal Divider Line
        divider = Table([['']], colWidths=[520])
        divider.setStyle(TableStyle([
            ('LINEABOVE', (0, 0), (-1, -1), 1.5, colors.HexColor('#2C3E50')),
        ]))
        story.append(divider)
        story.append(Spacer(1, 10))

        # Customer Metadata Table
        now_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        meta_text_left = Paragraph(
            f"<b>Customer Name:</b> {customer_name}<br/>"
            f"<b>Table Number:</b> {table_number}", meta_style
        )
        meta_text_right = Paragraph(
            f"<b>Bill Number:</b> {bill_number}<br/>"
            f"<b>Date & Time:</b> {now_str}", meta_style
        )

        meta_table = Table([[meta_text_left, meta_text_right]], colWidths=[260, 260])
        meta_table.setStyle(TableStyle([
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('ALIGN', (1, 0), (1, 0), 'RIGHT'),
        ]))
        story.append(meta_table)
        story.append(Spacer(1, 15))

        # Itemized Order Table
        table_data = [["#", "Item Description", "Category", "Qty", "Unit Price", "Total (RS.)"]]

        idx = 1
        for item in order_summary:
            table_data.append([
                str(idx),
                item['name'],
                item['category'],
                str(item['qty']),
                f"RS. {item['price']:.2f}",
                f"RS. {item['total']:.2f}"
            ])
            idx += 1

        # Total Row
        table_data.append(["", "", "", "", "TOTAL BILL:", f"RS. {total_amount:.2f}"])

        order_table = Table(table_data, colWidths=[30, 200, 90, 40, 80, 80])
        order_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2C3E50')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (3, 0), (-1, -1), 'RIGHT'),
            ('GRID', (0, 0), (-1, -2), 0.5, colors.HexColor('#BDC3C7')),
            ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#ECF0F1')),
            ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, -1), (-1, -1), 11),
            ('LINEABOVE', (0, -1), (-1, -1), 1.5, colors.HexColor('#2C3E50')),
        ]))
        story.append(order_table)
        story.append(Spacer(1, 20))

        # Footer
        footer_style = ParagraphStyle(
            'FooterStyle',
            parent=styles['Normal'],
            fontName='Helvetica-Oblique',
            fontSize=10,
            textColor=colors.HexColor('#27AE60'),
            alignment=1
        )
        story.append(Paragraph("Thank you for dining at Doraemon 21st Cen Eateries! Come again! 🙏", footer_style))

        # Build Document
        doc.build(story)
        print(f"[PDF] Bill generated successfully: {filepath}")
        return filepath

    @staticmethod
    def generate_text_fallback(filepath, bill_number, customer_name, table_number, order_summary, total_amount):
        """Fallback text bill generator if ReportLab is missing."""
        lines = []
        lines.append("===================================================\n")
        lines.append(f"          {BillGenerator.RESTAURANT_NAME}          \n")
        lines.append("===================================================\n")
        lines.append(f" Bill Number:   {bill_number}\n")
        lines.append(f" Customer Name: {customer_name}\n")
        lines.append(f" Table Number:  {table_number}\n")
        lines.append(f" Date & Time:   {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        lines.append("---------------------------------------------------\n")
        lines.append(f" {'Item':<18} {'Qty':<6} {'Price':<10} {'Total':>8}\n")
        lines.append("---------------------------------------------------\n")
        for item in order_summary:
            lines.append(f" {item['name']:<18} {item['qty']:<6} RS.{item['price']:<7.2f} RS.{item['total']:>6.2f}\n")
        lines.append("---------------------------------------------------\n")
        lines.append(f" TOTAL AMOUNT:                         RS. {total_amount:>6.2f}\n")
        lines.append("===================================================\n")
        lines.append("       Thank you for dining with us! Come again!    \n")
        lines.append("===================================================\n")

        with open(filepath, "w", encoding="utf-8") as f:
            f.writelines(lines)
        return filepath


# ==============================================================================
# 4. UI MANAGER CLASS (TKINTER GRAPHICAL INTERFACE)
# ==============================================================================
class UIManager:
    """Main Tkinter GUI Application Manager."""

    RESTAURANT_NAME = "Doraemon 21st Cen Eateries"

    def __init__(self, root, db_connector, menu_loader):
        self.root = root
        self.db = db_connector
        self.loader = menu_loader

        self.root.title(f"{self.RESTAURANT_NAME} - Order Management System")
        self.root.geometry("1100x750")
        self.root.minsize(950, 650)

        # Cart State: { "Item Name": { "item": item_dict, "qty": integer } }
        self.cart = {}
        self.image_cache = {}  # Keep references to PhotoImage objects to prevent GC
        self.qty_vars = {}     # Tkinter StringVar for item card quantities

        self.setup_styles()
        self.build_gui()

    def setup_styles(self):
        """Sets up ttk themes and colors."""
        self.style = ttk.Style()
        self.style.theme_use("clam")

        # Custom Palette
        self.BG_DARK = "#2C3E50"
        self.BG_LIGHT = "#ECF0F1"
        self.ACCENT = "#2980B9"
        self.SUCCESS = "#27AE60"
        self.DANGER = "#E74C3C"

    def build_gui(self):
        """Constructs the complete application layout."""
        # 1. Top Branding & Header Banner
        header_frame = tk.Frame(self.root, bg=self.BG_DARK, pady=10, padx=15)
        header_frame.pack(fill=tk.X)

        # Restaurant Logo Display
        if self.loader.logo_path and os.path.exists(self.loader.logo_path) and HAS_PIL:
            try:
                raw_logo = Image.open(self.loader.logo_path)
                resized_logo = raw_logo.resize((55, 55), Image.Resampling.LANCZOS)
                self.logo_img = ImageTk.PhotoImage(resized_logo)
                logo_label = tk.Label(header_frame, image=self.logo_img, bg=self.BG_DARK)
                logo_label.pack(side=tk.LEFT, padx=(0, 12))
            except Exception as e:
                print(f"[UI Warning] Failed to render logo: {e}")

        header_title = tk.Label(
            header_frame,
            text=self.RESTAURANT_NAME,
            font=("Segoe UI", 18, "bold"),
            fg="white",
            bg=self.BG_DARK
        )
        header_title.pack(side=tk.LEFT)

        header_subtitle = tk.Label(
            header_frame,
            text="21st Century Taste & Quality",
            font=("Segoe UI", 10, "italic"),
            fg="#BDC3C7",
            bg=self.BG_DARK
        )
        header_subtitle.pack(side=tk.LEFT, padx=15)

        # 2. Main Content Split Pane
        main_container = ttk.Frame(self.root, padding=10)
        main_container.pack(fill=tk.BOTH, expand=True)

        paned = ttk.PanedWindow(main_container, orient=tk.HORIZONTAL)
        paned.pack(fill=tk.BOTH, expand=True)

        # Left Frame: Customer Details, Category Filters & Food Cards
        left_frame = ttk.Frame(paned, padding=5)
        paned.add(left_frame, weight=3)

        # Right Frame: Order Cart Summary & Actions
        right_frame = ttk.Frame(paned, padding=5)
        paned.add(right_frame, weight=2)

        # --- LEFT PANE COMPONENTS ---
        # Customer Info Frame
        cust_frame = ttk.LabelFrame(left_frame, text=" Customer Information ", padding=8)
        cust_frame.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(cust_frame, text="Customer Name:", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, padx=5, sticky=tk.W)
        self.name_entry = ttk.Entry(cust_frame, width=22, font=("Segoe UI", 10))
        self.name_entry.grid(row=0, column=1, padx=5, sticky=tk.W)

        ttk.Label(cust_frame, text="Table No:", font=("Segoe UI", 9, "bold")).grid(row=0, column=2, padx=(15, 5), sticky=tk.W)
        self.table_entry = ttk.Entry(cust_frame, width=10, font=("Segoe UI", 10))
        self.table_entry.grid(row=0, column=3, padx=5, sticky=tk.W)

        # Category Filter Bar
        filter_frame = ttk.LabelFrame(left_frame, text=" Food Categories ", padding=6)
        filter_frame.pack(fill=tk.X, pady=(0, 8))

        categories = ["All"] + sorted(list(set(item['category'] for item in self.loader.menu_items)))
        for cat in categories:
            btn = tk.Button(
                filter_frame,
                text=cat,
                command=lambda c=cat: self.filter_menu_cards(c),
                bg=self.ACCENT,
                fg="white",
                font=("Segoe UI", 9, "bold"),
                padx=8,
                pady=2,
                relief=tk.FLAT
            )
            btn.pack(side=tk.LEFT, padx=3)

        # Scrollable Cards Canvas Area
        cards_outer_frame = ttk.LabelFrame(left_frame, text=" Menu Items (Select & Quantity) ", padding=8)
        cards_outer_frame.pack(fill=tk.BOTH, expand=True)

        self.canvas = tk.Canvas(cards_outer_frame, bg="#FAFAFA", highlightthickness=0)
        self.scrollbar = ttk.Scrollbar(cards_outer_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        self.cards_inner_frame = ttk.Frame(self.canvas)

        self.cards_inner_frame.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )
        self.canvas.create_window((0, 0), window=self.cards_inner_frame, anchor=tk.NW)
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        # Render Food Cards
        self.render_food_cards(self.loader.menu_items)

        # --- RIGHT PANE COMPONENTS (CART & BILLING) ---
        cart_frame = ttk.LabelFrame(right_frame, text=" Live Order Summary & Receipt ", padding=8)
        cart_frame.pack(fill=tk.BOTH, expand=True)

        # Cart Treeview
        self.cart_tree = ttk.Treeview(
            cart_frame,
            columns=("Item", "Cat", "Qty", "Price", "Total"),
            show="headings",
            height=14
        )
        self.cart_tree.heading("Item", text="Dish")
        self.cart_tree.heading("Cat", text="Category")
        self.cart_tree.heading("Qty", text="Qty")
        self.cart_tree.heading("Price", text="Price")
        self.cart_tree.heading("Total", text="Total")

        self.cart_tree.column("Item", width=130, anchor=tk.W)
        self.cart_tree.column("Cat", width=80, anchor=tk.W)
        self.cart_tree.column("Qty", width=45, anchor=tk.CENTER)
        self.cart_tree.column("Price", width=65, anchor=tk.E)
        self.cart_tree.column("Total", width=75, anchor=tk.E)
        self.cart_tree.pack(fill=tk.BOTH, expand=True, side=tk.TOP, pady=(0, 8))

        # Total Price Banner
        self.total_var = tk.StringVar(value="TOTAL BILL: RS. 0.00")
        total_banner = tk.Label(
            cart_frame,
            textvariable=self.total_var,
            font=("Segoe UI", 13, "bold"),
            fg=self.BG_DARK,
            bg="#E8F8F5",
            pady=6,
            relief=tk.SOLID,
            bd=1
        )
        total_banner.pack(fill=tk.X, pady=(0, 10))

        # Action Buttons
        btn_frame = ttk.Frame(cart_frame)
        btn_frame.pack(fill=tk.X)

        remove_btn = tk.Button(
            btn_frame,
            text="Delete Item",
            command=self.delete_selected_cart_item,
            bg=self.DANGER,
            fg="white",
            font=("Segoe UI", 9, "bold"),
            padx=8,
            pady=4,
            relief=tk.FLAT
        )
        remove_btn.pack(side=tk.LEFT, padx=3)

        clear_btn = tk.Button(
            btn_frame,
            text="Clear Cart",
            command=self.clear_cart,
            bg="#7F8C8D",
            fg="white",
            font=("Segoe UI", 9, "bold"),
            padx=8,
            pady=4,
            relief=tk.FLAT
        )
        clear_btn.pack(side=tk.LEFT, padx=3)

        place_btn = tk.Button(
            btn_frame,
            text="Save DB Order",
            command=self.place_order_db,
            bg=self.ACCENT,
            fg="white",
            font=("Segoe UI", 9, "bold"),
            padx=8,
            pady=4,
            relief=tk.FLAT
        )
        place_btn.pack(side=tk.RIGHT, padx=3)

        download_btn = tk.Button(
            btn_frame,
            text="Download PDF Bill",
            command=self.download_pdf_bill,
            bg=self.SUCCESS,
            fg="white",
            font=("Segoe UI", 9, "bold"),
            padx=8,
            pady=4,
            relief=tk.FLAT
        )
        download_btn.pack(side=tk.RIGHT, padx=3)

    def render_food_cards(self, items):
        """Renders food items as visual Cards in a multi-column grid."""
        for widget in self.cards_inner_frame.winfo_children():
            widget.destroy()

        cols = 2  # 2 Cards per row
        row = 0
        col = 0

        for item in items:
            item_name = item['name']
            card = tk.Frame(
                self.cards_inner_frame,
                bg="white",
                bd=1,
                relief=tk.SOLID,
                padx=8,
                pady=8
            )
            card.grid(row=row, column=col, padx=8, pady=8, sticky="nsew")

            # Load Item Thumbnail Image
            img_path = item.get('image_path', '')
            if img_path and os.path.exists(img_path) and HAS_PIL:
                try:
                    raw_img = Image.open(img_path)
                    thumb_img = raw_img.resize((100, 100), Image.Resampling.LANCZOS)
                    photo = ImageTk.PhotoImage(thumb_img)
                    self.image_cache[item_name] = photo
                    img_label = tk.Label(card, image=photo, bg="white")
                    img_label.pack(side=tk.TOP, pady=(0, 5))
                except Exception:
                    placeholder = tk.Label(card, text="[No Image]", bg="#BDC3C7", width=12, height=5)
                    placeholder.pack(side=tk.TOP, pady=(0, 5))
            else:
                placeholder = tk.Label(card, text="[No Image]", bg="#BDC3C7", width=12, height=5)
                placeholder.pack(side=tk.TOP, pady=(0, 5))

            # Details
            name_lbl = tk.Label(card, text=item_name, font=("Segoe UI", 10, "bold"), bg="white", wraplength=140)
            name_lbl.pack(side=tk.TOP)

            cat_lbl = tk.Label(card, text=f"[{item['category']}]", font=("Segoe UI", 8, "italic"), fg="#7F8C8D", bg="white")
            cat_lbl.pack(side=tk.TOP)

            price_lbl = tk.Label(card, text=f"RS. {item['price']:.2f}", font=("Segoe UI", 9, "bold"), fg=self.SUCCESS, bg="white")
            price_lbl.pack(side=tk.TOP, pady=(2, 5))

            # Quantity Control Frame (+ / - / Entry)
            ctrl_frame = tk.Frame(card, bg="white")
            ctrl_frame.pack(side=tk.TOP, pady=4)

            qty_var = self.qty_vars.get(item_name, tk.StringVar(value="1"))
            self.qty_vars[item_name] = qty_var

            minus_btn = tk.Button(
                ctrl_frame,
                text="-",
                command=lambda name=item_name: self.adjust_qty(name, -1),
                width=2,
                bg="#E67E22",
                fg="white",
                font=("Segoe UI", 9, "bold"),
                relief=tk.FLAT
            )
            minus_btn.pack(side=tk.LEFT, padx=2)

            qty_entry = tk.Entry(ctrl_frame, textvariable=qty_var, width=4, font=("Segoe UI", 9), justify="center")
            qty_entry.pack(side=tk.LEFT, padx=2)

            plus_btn = tk.Button(
                ctrl_frame,
                text="+",
                command=lambda name=item_name: self.adjust_qty(name, 1),
                width=2,
                bg=self.SUCCESS,
                fg="white",
                font=("Segoe UI", 9, "bold"),
                relief=tk.FLAT
            )
            plus_btn.pack(side=tk.LEFT, padx=2)

            # Add to Cart Button
            add_btn = tk.Button(
                card,
                text="Add to Cart",
                command=lambda it=item: self.add_to_cart(it),
                bg=self.ACCENT,
                fg="white",
                font=("Segoe UI", 9, "bold"),
                padx=6,
                pady=2,
                relief=tk.FLAT
            )
            add_btn.pack(side=tk.TOP, pady=(4, 0))

            col += 1
            if col >= cols:
                col = 0
                row += 1

    def adjust_qty(self, item_name, delta):
        """Increments or decrements item quantity entry."""
        var = self.qty_vars.get(item_name)
        if var:
            try:
                curr = int(var.get())
                new_qty = max(1, curr + delta)
                var.set(str(new_qty))
            except ValueError:
                var.set("1")

    def filter_menu_cards(self, category):
        """Filters displayed food cards by selected category."""
        if category == "All":
            self.render_food_cards(self.loader.menu_items)
        else:
            filtered = [i for i in self.loader.menu_items if i['category'].lower() == category.lower()]
            self.render_food_cards(filtered)

    def add_to_cart(self, item):
        """Adds or updates item in the order cart."""
        item_name = item['name']
        qty_str = self.qty_vars[item_name].get().strip()

        if not qty_str.isdigit() or int(qty_str) <= 0:
            messagebox.showerror("Quantity Error", "Please enter a valid positive whole number for quantity.")
            return

        qty = int(qty_str)
        if item_name in self.cart:
            self.cart[item_name]['qty'] += qty
        else:
            self.cart[item_name] = {"item": item, "qty": qty}

        self.update_cart_display()
        messagebox.showinfo("Cart Updated", f"Added {qty} x {item_name} to cart!")

    def update_cart_display(self):
        """Refreshes the Cart Treeview and running total amount."""
        for item in self.cart_tree.get_children():
            self.cart_tree.delete(item)

        total = 0.0
        for name, data in self.cart.items():
            it = data['item']
            q = data['qty']
            line_total = it['price'] * q
            total += line_total
            self.cart_tree.insert("", tk.END, values=(name, it['category'], q, f"RS. {it['price']:.2f}", f"RS. {line_total:.2f}"))

        self.total_var.set(f"TOTAL BILL: RS. {total:.2f}")

    def delete_selected_cart_item(self):
        """Deletes selected item from cart."""
        selected = self.cart_tree.selection()
        if not selected:
            messagebox.showwarning("Selection Warning", "Please select an item from the cart to delete.")
            return

        values = self.cart_tree.item(selected, "values")
        item_name = values[0]

        if item_name in self.cart:
            del self.cart[item_name]
            self.update_cart_display()

    def clear_cart(self):
        """Clears all items in cart."""
        if messagebox.askyesno("Clear Cart", "Are you sure you want to clear the cart?"):
            self.cart.clear()
            self.update_cart_display()

    def generate_bill_number(self, cust_name, table_num):
        """Generates a unique bill number combining date, table, initials, and random ID."""
        date_str = datetime.datetime.now().strftime("%Y%m%d")
        initials = "".join([part[0].upper() for part in cust_name.split() if part]) or "XX"
        rand_num = random.randint(1000, 9999)
        return f"BILL-{date_str}-T{table_num}-{initials}-{rand_num}"

    def validate_customer_details(self):
        """Validates customer name and table number."""
        name = self.name_entry.get().strip()
        table = self.table_entry.get().strip()

        if not name:
            messagebox.showerror("Input Error", "Please enter the Customer Name.")
            self.name_entry.focus()
            return None, None

        if not table:
            messagebox.showerror("Input Error", "Please enter the Table Number.")
            self.table_entry.focus()
            return None, None

        if not self.cart:
            messagebox.showerror("Cart Empty", "Please add items to cart before placing an order.")
            return None, None

        return name, table

    def get_order_summary_list(self):
        """Builds summary list of dictionaries for bill generation."""
        summary = []
        total = 0.0
        for name, data in self.cart.items():
            it = data['item']
            q = data['qty']
            line_total = it['price'] * q
            total += line_total
            summary.append({
                "name": name,
                "category": it['category'],
                "qty": q,
                "price": it['price'],
                "total": line_total
            })
        return summary, total

    def place_order_db(self):
        """Saves current order to MSSQL Database."""
        name, table = self.validate_customer_details()
        if not name or not table:
            return

        summary, total = self.get_order_summary_list()
        bill_num = self.generate_bill_number(name, table)

        # Order items tuple for DB: [(dish_name, qty, price), ...]
        db_items = [(item['name'], item['qty'], item['price']) for item in summary]

        try:
            self.db.save_order_transaction(bill_num, name, table, total, db_items)
            messagebox.showinfo("Order Saved", f"Order #{bill_num} saved successfully to MSSQL Database!")
        except Exception as e:
            messagebox.showerror("Database Error", f"Failed to save order transaction to MSSQL: {e}")

    def download_pdf_bill(self):
        """Saves current order to MSSQL and exports PDF Bill."""
        name, table = self.validate_customer_details()
        if not name or not table:
            return

        summary, total = self.get_order_summary_list()
        bill_num = self.generate_bill_number(name, table)

        # 1. Save to MSSQL DB
        db_items = [(item['name'], item['qty'], item['price']) for item in summary]
        try:
            self.db.save_order_transaction(bill_num, name, table, total, db_items)
        except Exception as e:
            print(f"[DB Warning] Could not save order to DB before PDF download: {e}")

        # 2. Generate PDF Bill
        pdf_path = BillGenerator.generate_pdf(
            bill_number=bill_num,
            customer_name=name,
            table_number=table,
            order_summary=summary,
            total_amount=total,
            logo_path=self.loader.logo_path
        )

        messagebox.showinfo("PDF Generated", f"Bill downloaded successfully!\nFile Location: {pdf_path}")


# ==============================================================================
# MAIN ENTRY POINT
# ==============================================================================
def main():
    db = DBConnector(server=".\\SQLEXPRESS", database="DoraemonEateriesDB")
    loader = MenuLoader(db_connector=db)

    root = tk.Tk()
    app = UIManager(root, db_connector=db, menu_loader=loader)
    root.mainloop()


if __name__ == "__main__":
    main()
