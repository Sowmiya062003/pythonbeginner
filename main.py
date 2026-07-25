"""
main.py - Application entry point for Doraemon 21st Cen Eateries Web App.

Startup sequence:
  1. Initialize MSSQL schema (order_DB.py)
  2. Scan IMAGES folder and sync MenuItems table (menu_loader.py)
  3. Launch Flask web server (ui_manager.py) on http://127.0.0.1:5000

Routes available:
  /          -> Customer ordering web app
  /admin     -> Admin live order queue dashboard
  /api/menu  -> JSON menu list
  /api/orders -> POST place an order
  /api/download_bill/<bill_number> -> Download PDF bill
"""

import logging
import sys
import os

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("main")


def main():
    logger.info("=" * 60)
    logger.info("  Doraemon 21st Cen Eateries — Startup Sequence")
    logger.info("=" * 60)

    # Step 1: Verify DB connection
    logger.info("[1/3] Initializing database schema...")
    try:
        from order_DB import db_connector
        if db_connector.connected:
            logger.info("      OK - MSSQL connected. Tables ready.")
        else:
            logger.warning("      WARNING - MSSQL offline. Orders will not be persisted.")
    except Exception as e:
        logger.error(f"      ERROR - DB init error: {e}")
        sys.exit(1)

    # Step 2: Load and sync menu from IMAGES folder
    logger.info("[2/3] Scanning IMAGES folder and syncing menu...")
    try:
        from menu_loader import menu_loader
        count = len(menu_loader.menu_items)
        logo_found = "Yes" if menu_loader.logo_path else "No"
        logger.info(f"      OK - {count} menu item(s) loaded. Logo found: {logo_found}")
        if menu_loader.image_dir:
            logger.info(f"      IMAGES dir: {menu_loader.image_dir}")
    except Exception as e:
        logger.error(f"      ERROR - Menu loader error: {e}")
        logger.warning("      Continuing without menu items...")

    # Step 3: Start Flask web server
    logger.info("[3/3] Starting Flask web server...")
    logger.info("")
    logger.info("  Customer App  -> http://127.0.0.1:5000/")
    logger.info("  Admin Portal  -> http://127.0.0.1:5000/admin")
    logger.info("  Menu API      -> http://127.0.0.1:5000/api/menu")
    logger.info("")
    logger.info("  Press CTRL+C to stop the server.")
    logger.info("=" * 60)

    try:
        from ui_manager import app
        app.run(
            host="127.0.0.1",
            port=5000,
            debug=False,
            use_reloader=False
        )
    except Exception as e:
        logger.error(f"ERROR - Failed to start Flask server: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
