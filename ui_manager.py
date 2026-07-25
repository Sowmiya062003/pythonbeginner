"""
ui_manager.py - Web interface router and Flask app module.
Serves customer web interface, image assets, REST APIs, and handles confirmation popups.
"""

import os
import random
import datetime
import logging
from flask import Flask, jsonify, render_template_string, request, send_from_directory, send_file
from order_DB import db_connector
from menu_loader import menu_loader
from bill_generator import BillGenerator
from admin_restaurant import admin_bp

logger = logging.getLogger("ui_manager")

app = Flask(__name__)
app.register_blueprint(admin_bp)

CUSTOMER_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Doraemon 21st Cen Eateries - Menu & Ordering</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #0f172a;
            --card-bg: #1e293b;
            --accent: #38bdf8;
            --accent-green: #22c55e;
            --accent-red: #ef4444;
            --accent-orange: #f97316;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border-color: #334155;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Outfit', sans-serif; }
        body { background-color: var(--bg-dark); color: var(--text-main); min-height: 100vh; display: flex; flex-direction: column; }

        header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 15px 30px;
            background: var(--card-bg);
            border-bottom: 1px solid var(--border-color);
            position: sticky;
            top: 0;
            z-index: 100;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }

        .header-brand { display: flex; align-items: center; gap: 15px; }
        .logo-img { width: 55px; height: 55px; border-radius: 12px; object-fit: cover; border: 2px solid var(--accent); }
        h1 { font-size: 1.6rem; font-weight: 700; color: var(--accent); letter-spacing: 0.5px; }
        .tagline { font-size: 0.85rem; color: var(--text-muted); font-style: italic; }

        .admin-link {
            color: var(--accent-orange);
            text-decoration: none;
            font-weight: 600;
            border: 1px solid var(--accent-orange);
            padding: 6px 14px;
            border-radius: 8px;
            transition: all 0.2s ease;
        }
        .admin-link:hover { background: var(--accent-orange); color: #fff; }

        .main-container {
            display: grid;
            grid-template-columns: 1fr 380px;
            gap: 25px;
            padding: 25px;
            max-width: 1400px;
            margin: 0 auto;
            width: 100%;
            flex: 1;
        }

        /* CUSTOMER INFO & CATEGORIES */
        .info-bar {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            padding: 15px 20px;
            margin-bottom: 20px;
            display: flex;
            gap: 20px;
            align-items: center;
        }

        .input-group { display: flex; flex-direction: column; gap: 4px; flex: 1; }
        .input-group label { font-size: 0.85rem; font-weight: 600; color: var(--text-muted); }
        .input-group input {
            background: var(--bg-dark);
            border: 1px solid var(--border-color);
            color: var(--text-main);
            padding: 8px 12px;
            border-radius: 8px;
            font-size: 0.95rem;
            outline: none;
        }
        .input-group input:focus { border-color: var(--accent); }

        .filter-bar {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
            overflow-x: auto;
            padding-bottom: 5px;
        }
        .filter-btn {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            color: var(--text-muted);
            padding: 8px 18px;
            border-radius: 20px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s ease;
            white-space: nowrap;
        }
        .filter-btn.active, .filter-btn:hover { background: var(--accent); color: #000; border-color: var(--accent); }

        /* FOOD CARDS GRID */
        .food-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
            gap: 20px;
        }

        .food-card {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            overflow: hidden;
            display: flex;
            flex-direction: column;
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }
        .food-card:hover { transform: translateY(-4px); box-shadow: 0 8px 25px rgba(0,0,0,0.4); border-color: var(--accent); }

        .food-img { width: 100%; height: 150px; object-fit: cover; }
        .food-details { padding: 15px; display: flex; flex-direction: column; gap: 8px; flex: 1; }
        .food-title { font-size: 1.05rem; font-weight: 600; }
        .food-badge { font-size: 0.75rem; background: rgba(56, 189, 248, 0.15); color: var(--accent); padding: 2px 8px; border-radius: 6px; width: fit-content; font-weight: 600; }
        .food-price { font-size: 1.1rem; font-weight: 700; color: var(--accent-green); margin-top: auto; }

        .qty-controls {
            display: flex;
            align-items: center;
            justify-content: space-between;
            background: var(--bg-dark);
            border-radius: 8px;
            padding: 4px;
            margin-top: 8px;
        }
        .qty-btn {
            width: 30px; height: 30px; border-radius: 6px; border: none; background: var(--card-bg); color: var(--text-main); font-weight: 700; cursor: pointer; display: flex; align-items: center; justify-content: center;
        }
        .qty-btn:hover { background: var(--accent); color: #000; }
        .qty-val { font-weight: 600; width: 35px; text-align: center; border: none; background: transparent; color: var(--text-main); }

        .add-cart-btn {
            background: var(--accent);
            color: #000;
            border: none;
            padding: 8px;
            border-radius: 8px;
            font-weight: 700;
            cursor: pointer;
            margin-top: 8px;
            transition: opacity 0.2s ease;
        }
        .add-cart-btn:hover { opacity: 0.9; }

        /* CART PANEL */
        .cart-panel {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 20px;
            display: flex;
            flex-direction: column;
            height: fit-content;
            max-height: calc(100vh - 120px);
            position: sticky;
            top: 100px;
        }

        .cart-header { font-size: 1.2rem; font-weight: 700; border-bottom: 1px solid var(--border-color); padding-bottom: 10px; margin-bottom: 15px; }
        .cart-list { list-style: none; display: flex; flex-direction: column; gap: 12px; overflow-y: auto; max-height: 320px; padding-right: 5px; }

        .cart-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            background: var(--bg-dark);
            padding: 10px 12px;
            border-radius: 8px;
            border: 1px solid var(--border-color);
        }

        .cart-item-name { font-weight: 600; font-size: 0.95rem; }
        .cart-item-sub { font-size: 0.8rem; color: var(--text-muted); }

        .delete-icon { color: var(--accent-red); cursor: pointer; font-size: 1.1rem; padding: 2px 6px; }

        .cart-summary {
            border-top: 1px solid var(--border-color);
            padding-top: 15px;
            margin-top: 15px;
            display: flex;
            flex-direction: column;
            gap: 12px;
        }
        .total-row { display: flex; justify-content: space-between; font-size: 1.2rem; font-weight: 700; color: var(--accent-green); }

        .place-order-btn {
            background: var(--accent-green);
            color: #fff;
            border: none;
            padding: 12px;
            border-radius: 10px;
            font-size: 1.05rem;
            font-weight: 700;
            cursor: pointer;
            transition: all 0.2s ease;
        }
        .place-order-btn:hover { background: #16a34a; }

        /* MODAL POPUPS */
        .modal-overlay {
            position: fixed;
            top: 0; left: 0; width: 100vw; height: 100vh;
            background: rgba(0,0,0,0.7);
            display: none;
            align-items: center;
            justify-content: center;
            z-index: 1000;
            backdrop-filter: blur(4px);
        }

        .modal-box {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            padding: 25px 30px;
            border-radius: 16px;
            max-width: 420px;
            width: 90%;
            text-align: center;
            display: flex;
            flex-direction: column;
            gap: 18px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }

        .modal-title { font-size: 1.3rem; font-weight: 700; color: var(--accent); }
        .modal-body { font-size: 0.95rem; color: var(--text-main); line-height: 1.4; }

        .modal-btns { display: flex; gap: 12px; justify-content: center; }
        .modal-btn { padding: 10px 24px; border-radius: 8px; border: none; font-weight: 700; cursor: pointer; font-size: 0.95rem; }
        .btn-yes { background: var(--accent-green); color: #fff; }
        .btn-no { background: var(--accent-red); color: #fff; }
        .btn-ok { background: var(--accent); color: #000; width: 100%; }
    </style>
</head>
<body>

    <header>
        <div class="header-brand">
            <img src="/images/{{ logo_filename }}" alt="Logo" class="logo-img">
            <div>
                <h1>Doraemon 21st Cen Eateries</h1>
                <div class="tagline">21st Century Taste & Quality Guaranteed</div>
            </div>
        </div>
        <a href="/admin" class="admin-link">🔑 Admin Portal</a>
    </header>

    <div class="main-container">
        <!-- LEFT SECTION: MENU & CARDS -->
        <div>
            <div class="info-bar">
                <div class="input-group">
                    <label>Customer Name *</label>
                    <input type="text" id="custName" placeholder="Enter your name">
                </div>
                <div class="input-group">
                    <label>Table Number *</label>
                    <input type="text" id="tableNum" placeholder="e.g. 5">
                </div>
            </div>

            <div class="filter-bar" id="categoryFilters">
                <button class="filter-btn active" onclick="filterCategory('All')">All</button>
            </div>

            <div class="food-grid" id="foodGrid">
                <!-- Food Cards Injected Here -->
            </div>
        </div>

        <!-- RIGHT SECTION: CART PANEL -->
        <div class="cart-panel">
            <div class="cart-header">🛒 Order Summary</div>
            <ul class="cart-list" id="cartList">
                <li style="color: var(--text-muted); font-size: 0.9rem;">Your cart is empty.</li>
            </ul>

            <div class="cart-summary">
                <div class="total-row">
                    <span>Total Amount:</span>
                    <span id="totalAmount">RS. 0.00</span>
                </div>
                <button class="place-order-btn" onclick="promptOrderConfirmation()">Place Order</button>
            </div>
        </div>
    </div>

    <!-- CONFIRMATION POPUP MODAL -->
    <div class="modal-overlay" id="confirmModal">
        <div class="modal-box">
            <div class="modal-title">Confirm Order</div>
            <div class="modal-body">Are you sure you want to place this order?</div>
            <div class="modal-btns">
                <button class="modal-btn btn-yes" onclick="executeOrderPlacement()">Yes</button>
                <button class="modal-btn btn-no" onclick="closeConfirmModal()">No</button>
            </div>
        </div>
    </div>

    <!-- THANK YOU POPUP MODAL -->
    <div class="modal-overlay" id="thankYouModal">
        <div class="modal-box">
            <div class="modal-title">🎉 Order Placed Successfully!</div>
            <div class="modal-body" id="thankYouMessage">
                Thanks for ordering with us! We'll let you know once your order is ready.
            </div>
            <div class="modal-btns">
                <button class="modal-btn btn-ok" onclick="closeThankYouModal()">OK</button>
            </div>
        </div>
    </div>

    <script>
        let menuItems = [];
        let cart = {};
        let lastBillNumber = '';

        async function loadMenu() {
            try {
                const res = await fetch('/api/menu');
                menuItems = await res.json();
                renderCategoryFilters();
                renderFoodCards(menuItems);
            } catch (err) {
                console.error("Error loading menu:", err);
            }
        }

        function renderCategoryFilters() {
            const cats = ['All', ...new Set(menuItems.map(i => i.category))];
            const filterBar = document.getElementById('categoryFilters');
            filterBar.innerHTML = cats.map(c => `
                <button class="filter-btn ${c === 'All' ? 'active' : ''}" onclick="filterCategory('${c}', this)">${c}</button>
            `).join('');
        }

        function filterCategory(cat, btn) {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            if(btn) btn.classList.add('active');

            if (cat === 'All') {
                renderFoodCards(menuItems);
            } else {
                renderFoodCards(menuItems.filter(i => i.category.toLowerCase() === cat.toLowerCase()));
            }
        }

        function renderFoodCards(items) {
            const grid = document.getElementById('foodGrid');
            grid.innerHTML = items.map(item => `
                <div class="food-card">
                    <img src="/images/${item.image_filename}" alt="${item.name}" class="food-img">
                    <div class="food-details">
                        <div class="food-title">${item.name}</div>
                        <span class="food-badge">${item.category}</span>
                        <div class="food-price">RS. ${item.price.toFixed(2)}</div>
                        <div class="qty-controls">
                            <button class="qty-btn" onclick="adjustCardQty('${item.name}', -1)">−</button>
                            <input type="text" class="qty-val" id="qty-${item.name}" value="1" readonly>
                            <button class="qty-btn" onclick="adjustCardQty('${item.name}', 1)">+</button>
                        </div>
                        <button class="add-cart-btn" onclick="addToCart('${item.name}')">+ Add to Cart</button>
                    </div>
                </div>
            `).join('');
        }

        function adjustCardQty(itemName, delta) {
            const input = document.getElementById(`qty-${itemName}`);
            if (input) {
                let val = parseInt(input.value) || 1;
                input.value = Math.max(1, val + delta);
            }
        }

        function addToCart(itemName) {
            const item = menuItems.find(i => i.name === itemName);
            const input = document.getElementById(`qty-${itemName}`);
            const qty = parseInt(input ? input.value : 1) || 1;

            if (cart[itemName]) {
                cart[itemName].qty += qty;
            } else {
                cart[itemName] = { item: item, qty: qty };
            }
            updateCartUI();
        }

        function updateCartUI() {
            const list = document.getElementById('cartList');
            const keys = Object.keys(cart);
            let total = 0;

            if (keys.length === 0) {
                list.innerHTML = '<li style="color: var(--text-muted); font-size: 0.9rem;">Your cart is empty.</li>';
                document.getElementById('totalAmount').innerText = 'RS. 0.00';
                return;
            }

            list.innerHTML = keys.map(key => {
                const entry = cart[key];
                const lineTotal = entry.item.price * entry.qty;
                total += lineTotal;
                return `
                    <li class="cart-item">
                        <div>
                            <div class="cart-item-name">${entry.item.name}</div>
                            <div class="cart-item-sub">RS. ${entry.item.price.toFixed(2)} × ${entry.qty} = RS. ${lineTotal.toFixed(2)}</div>
                        </div>
                        <span class="delete-icon" onclick="removeFromCart('${key}')">🗑️</span>
                    </li>
                `;
            }).join('');

            document.getElementById('totalAmount').innerText = `RS. ${total.toFixed(2)}`;
        }

        function removeFromCart(itemName) {
            delete cart[itemName];
            updateCartUI();
        }

        /* CONFIRMATION POPUP FLOW */
        function promptOrderConfirmation() {
            const name = document.getElementById('custName').value.trim();
            const table = document.getElementById('tableNum').value.trim();

            if (!name) {
                alert("Please enter your Customer Name before placing an order.");
                document.getElementById('custName').focus();
                return;
            }
            if (!table) {
                alert("Please enter your Table Number before placing an order.");
                document.getElementById('tableNum').focus();
                return;
            }
            if (Object.keys(cart).length === 0) {
                alert("Your cart is empty. Please add food items to cart.");
                return;
            }

            document.getElementById('confirmModal').style.display = 'flex';
        }

        function closeConfirmModal() {
            document.getElementById('confirmModal').style.display = 'none';
        }

        async function executeOrderPlacement() {
            closeConfirmModal();

            const name = document.getElementById('custName').value.trim();
            const table = document.getElementById('tableNum').value.trim();
            const items = Object.values(cart).map(c => ({
                name: c.item.name,
                category: c.item.category,
                qty: c.qty,
                price: c.item.price
            }));

            try {
                const res = await fetch('/api/orders', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        customer_name: name,
                        table_number: table,
                        items: items
                    })
                });

                const data = await res.json();
                if (data.success) {
                    lastBillNumber = data.bill_number;
                    document.getElementById('thankYouMessage').innerHTML = `
                        <b>TOKEN #${data.token_number}</b><br/>
                        Thanks for ordering with us! We'll let you know once your order is ready.<br/><br/>
                        <a href="/api/download_bill/${data.bill_number}" target="_blank" style="color: var(--accent); font-weight:700;">📄 Download PDF Bill (${data.bill_number})</a>
                    `;
                    document.getElementById('thankYouModal').style.display = 'flex';

                    // Clear Cart & inputs
                    cart = {};
                    updateCartUI();
                } else {
                    alert("Error placing order: " + data.message);
                }
            } catch (err) {
                alert("Network error placing order.");
            }
        }

        function closeThankYouModal() {
            document.getElementById('thankYouModal').style.display = 'none';
        }

        loadMenu();
    </script>
</body>
</html>
"""


@app.route("/")
def index():
    """Renders Customer Web App."""
    return render_template_string(CUSTOMER_HTML, logo_filename=menu_loader.logo_filename or "")


@app.route("/images/<path:filename>")
def serve_image(filename):
    """Serves image assets from IMAGES folder."""
    if menu_loader.image_dir and os.path.exists(os.path.join(menu_loader.image_dir, filename)):
        return send_from_directory(menu_loader.image_dir, filename)
    return "Image not found", 404


@app.route("/api/menu", methods=["GET"])
def get_menu():
    """Returns JSON list of menu items."""
    return jsonify(menu_loader.menu_items)


@app.route("/api/orders", methods=["POST"])
def place_order_api():
    """Saves order to MSSQL, generates PDF bill, and returns Token number."""
    data = request.json or {}
    cust_name = data.get("customer_name", "").strip()
    table_num = data.get("table_number", "").strip()
    items = data.get("items", [])

    if not cust_name or not table_num or not items:
        return jsonify({"success": False, "message": "Missing required fields"}), 400

    # Validate quantities
    order_tuples = []
    summary_items = []
    total_amount = 0.0

    for item in items:
        dish_name = item.get("name")
        qty = int(item.get("qty", 1))
        price = float(item.get("price", 0.0))
        cat = item.get("category", "Food")

        if qty <= 0:
            return jsonify({"success": False, "message": f"Invalid quantity for {dish_name}"}), 400

        line_total = price * qty
        total_amount += line_total

        order_tuples.append((dish_name, qty, price))
        summary_items.append({
            "name": dish_name,
            "category": cat,
            "qty": qty,
            "price": price,
            "total": line_total
        })

    # Generate unique bill number
    date_str = datetime.datetime.now().strftime("%Y%m%d")
    initials = "".join([p[0].upper() for p in cust_name.split() if p]) or "XX"
    rand_id = random.randint(1000, 9999)
    bill_number = f"BILL-{date_str}-T{table_num}-{initials}-{rand_id}"

    try:
        # Save to MSSQL DB (Returns FCFS token_number)
        token_num = db_connector.save_order_transaction(bill_number, cust_name, table_num, total_amount, order_tuples)

        # Generate PDF Bill
        pdf_path = BillGenerator.generate_pdf(
            bill_number=bill_number,
            token_number=token_num,
            customer_name=cust_name,
            table_number=table_num,
            order_summary=summary_items,
            total_amount=total_amount,
            logo_path=menu_loader.logo_path
        )

        return jsonify({
            "success": True,
            "bill_number": bill_number,
            "token_number": token_num,
            "pdf_filename": os.path.basename(pdf_path)
        })

    except Exception as e:
        logger.error(f"Error placing order API: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/download_bill/<bill_number>")
def download_bill(bill_number):
    """Serves PDF bill file download."""
    for f in os.listdir(os.getcwd()):
        if f.startswith(f"Bill_{bill_number}_") and f.endswith(".pdf"):
            return send_file(os.path.abspath(f), as_attachment=True)
    return "Bill file not found", 404
