"""
menu_loader.py - Image processing and auto-categorization module.
Reads IMAGES folder, parses hyphens for item names and categories,
and populates MSSQL database via order_DB.py.
"""

import os
import logging
from order_DB import db_connector

logger = logging.getLogger("menu_loader")


class MenuLoader:
    """Scans image directory, parses item names and categories, and syncs DB."""

    DEFAULT_PRICES = {
        "pizza": 250.0,
        "burger": 150.0,
        "roll": 120.0,
        "icecream": 100.0,
        "dessert": 140.0,
        "beverage": 90.0
    }

    def __init__(self, db=db_connector, search_dirs=None):
        self.db = db
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
        self.logo_filename = None
        self.menu_items = []
        self.scan_and_populate()

    def locate_image_directory(self):
        """Finds valid IMAGES directory containing image files."""
        for d in self.search_dirs:
            if os.path.exists(d) and os.path.isdir(d):
                files = os.listdir(d)
                if any(f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')) for f in files):
                    return os.path.abspath(d)
        return None

    def scan_and_populate(self):
        """Scans image folder, extracts metadata, and populates MSSQL database."""
        if not self.image_dir:
            logger.warning("No IMAGES directory found.")
            return

        all_files = os.listdir(self.image_dir)

        # 1. Locate Logo File
        for f in all_files:
            if "logo" in f.lower() and f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                self.logo_path = os.path.join(self.image_dir, f)
                self.logo_filename = f
                break

        # 2. Parse Food Images
        for f in all_files:
            if "logo" in f.lower() or not f.lower().endswith(('.png', '.jpg', '.jpeg', '.webp')):
                continue

            full_path = os.path.join(self.image_dir, f)
            file_type = os.path.splitext(f)[1].replace('.', '').upper()
            file_size = os.path.getsize(full_path)

            name_without_ext = os.path.splitext(f)[0]
            normalized = name_without_ext.replace('‑', '-').replace('_', ' ')

            if '-' in normalized:
                parts = normalized.split('-', 1)
                raw_name = parts[0].strip().title()
                raw_cat = parts[1].strip().capitalize()
            else:
                raw_name = normalized.strip().title()
                raw_cat = "General"

            cat_key = raw_cat.lower()
            price = self.DEFAULT_PRICES.get(cat_key, 120.0)

            item = {
                "name": raw_name,
                "category": raw_cat,
                "image_filename": f,
                "image_path": full_path,
                "price": price,
                "file_type": file_type,
                "file_size": file_size
            }
            self.menu_items.append(item)

            if self.db and self.db.connected:
                self.db.upsert_menu_item(raw_name, raw_cat, full_path, price, file_type, file_size)

        if self.db and self.db.connected:
            db_items = self.db.fetch_menu_items()
            if db_items:
                path_to_filename = {item['image_path']: item['image_filename'] for item in self.menu_items}
                for item in db_items:
                    item['image_filename'] = path_to_filename.get(item['image_path'], os.path.basename(item['image_path']))
                self.menu_items = db_items

        logger.info(f"Loaded {len(self.menu_items)} menu items into MenuLoader.")


menu_loader = MenuLoader()
