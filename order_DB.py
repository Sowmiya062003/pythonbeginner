"""
order_DB.py - Database operations module for Doraemon 21st Cen Eateries.
Handles MSSQL connection, table initialization, FCFS token generation,
atomic order transactions, and status updates.
"""

import logging
import datetime

try:
    import pyodbc
    HAS_PYODBC = True
except ImportError:
    HAS_PYODBC = False

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("order_DB")


class DBConnector:
    """Handles MSSQL Database connections and transactions."""

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
            logger.warning("pyodbc is not installed. Running in offline DB mode.")
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
                            TokenNumber INT NOT NULL,
                            CustomerName NVARCHAR(100) NOT NULL,
                            TableNumber NVARCHAR(50) NOT NULL,
                            OrderDate DATETIME NOT NULL,
                            TotalAmount DECIMAL(10,2) NOT NULL,
                            Status NVARCHAR(30) DEFAULT 'Preparing'
                        );
                    """)

                    # Ensure TokenNumber column exists if Orders table existed previously
                    cursor.execute("""
                        IF NOT EXISTS (
                            SELECT * FROM sys.columns 
                            WHERE object_id = OBJECT_ID('Orders') AND name = 'TokenNumber'
                        )
                        ALTER TABLE Orders ADD TokenNumber INT NOT NULL DEFAULT 1;
                    """)

                    # Ensure Status column exists
                    cursor.execute("""
                        IF NOT EXISTS (
                            SELECT * FROM sys.columns 
                            WHERE object_id = OBJECT_ID('Orders') AND name = 'Status'
                        )
                        ALTER TABLE Orders ADD Status NVARCHAR(30) DEFAULT 'Preparing';
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
            logger.info(f"Successfully initialized MSSQL Database '{self.database}'.")
        except Exception as e:
            logger.error(f"Failed to initialize MSSQL Server: {e}")
            self.connected = False

    def upsert_menu_item(self, item_name, category, image_path, price, file_type, file_size):
        """Inserts or updates a menu item in MSSQL."""
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
            logger.error(f"Error upserting menu item '{item_name}': {e}")

    def fetch_menu_items(self):
        """Fetches all menu items from MSSQL database."""
        if not self.connected:
            return []

        items = []
        try:
            with pyodbc.connect(self.conn_str) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT ItemName, Category, ImagePath, Price FROM MenuItems ORDER BY Category, ItemName")
                    for r in cursor.fetchall():
                        items.append({
                            "name": r[0],
                            "category": r[1],
                            "image_path": r[2],
                            "price": float(r[3])
                        })
        except Exception as e:
            logger.error(f"Error fetching menu items: {e}")
        return items

    def get_next_token_number(self):
        """Computes sequential First-Come-First-Serve (FCFS) token number for today."""
        if not self.connected:
            return 1

        try:
            with pyodbc.connect(self.conn_str) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT ISNULL(MAX(TokenNumber), 0) + 1 
                        FROM Orders 
                        WHERE CAST(OrderDate AS DATE) = CAST(GETDATE() AS DATE)
                    """)
                    row = cursor.fetchone()
                    return row[0] if row else 1
        except Exception as e:
            logger.error(f"Error generating token number: {e}")
            return 1

    def save_order_transaction(self, bill_number, customer_name, table_number, total_amount, order_items):
        """
        Saves Order and OrderDetails in an atomic transaction (commit/rollback).
        Returns assigned token_number.
        """
        token_num = self.get_next_token_number()

        if not self.connected:
            logger.info(f"Offline mode: Order {bill_number} simulated with Token #{token_num}.")
            return token_num

        conn = None
        try:
            conn = pyodbc.connect(self.conn_str, autocommit=False)
            cursor = conn.cursor()

            # Insert Order Record
            cursor.execute("""
                INSERT INTO Orders (BillNumber, TokenNumber, CustomerName, TableNumber, OrderDate, TotalAmount, Status)
                OUTPUT INSERTED.OrderID
                VALUES (?, ?, ?, ?, GETDATE(), ?, 'Preparing')
            """, (bill_number, token_num, customer_name, table_number, total_amount))

            order_id = cursor.fetchone()[0]

            # Insert Line Items
            for dish_name, qty, unit_price in order_items:
                cursor.execute("""
                    INSERT INTO OrderDetails (OrderID, ItemName, Quantity, Price)
                    VALUES (?, ?, ?, ?)
                """, (order_id, dish_name, qty, unit_price))

            # Commit Transaction
            conn.commit()
            logger.info(f"Transaction committed: Order #{order_id}, Bill {bill_number}, Token #{token_num}.")
            return token_num

        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Rollback executed for Bill {bill_number}: {e}")
            raise e
        finally:
            if conn:
                conn.close()

    def fetch_all_orders(self):
        """Fetches order queue for Admin Dashboard."""
        if not self.connected:
            return []

        orders = []
        try:
            with pyodbc.connect(self.conn_str) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT OrderID, BillNumber, TokenNumber, CustomerName, TableNumber, OrderDate, TotalAmount, Status
                        FROM Orders
                        ORDER BY OrderID DESC
                    """)
                    order_rows = cursor.fetchall()

                    for r in order_rows:
                        order_id = r[0]

                        # Fetch line items
                        cursor.execute("""
                            SELECT ItemName, Quantity, Price 
                            FROM OrderDetails 
                            WHERE OrderID = ?
                        """, (order_id,))

                        details = []
                        for d in cursor.fetchall():
                            details.append({
                                "name": d[0],
                                "qty": d[1],
                                "price": float(d[2]),
                                "total": float(d[1] * d[2])
                            })

                        orders.append({
                            "order_id": r[0],
                            "bill_number": r[1],
                            "token_number": r[2],
                            "customer_name": r[3],
                            "table_number": r[4],
                            "order_date": r[5].strftime("%Y-%m-%d %H:%M:%S") if isinstance(r[5], datetime.datetime) else str(r[5]),
                            "total_amount": float(r[6]),
                            "status": r[7] or "Preparing",
                            "items": details
                        })
        except Exception as e:
            logger.error(f"Error fetching admin orders queue: {e}")
        return orders

    def update_order_status(self, order_id, status):
        """Updates the status of an order in MSSQL."""
        if not self.connected:
            return False

        try:
            with pyodbc.connect(self.conn_str, autocommit=True) as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE Orders SET Status = ? WHERE OrderID = ?
                    """, (status, order_id))
                    logger.info(f"Updated Order #{order_id} status to '{status}'.")
                    return True
        except Exception as e:
            logger.error(f"Error updating order status for #{order_id}: {e}")
            return False


# Singleton Instance
db_connector = DBConnector()
