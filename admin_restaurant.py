"""
admin_restaurant.py - Admin dashboard module for Doraemon 21st Cen Eateries.
Provides Blueprint/routes for viewing live order queue (FCFS basis) and updating status.
"""

import logging
from flask import Blueprint, jsonify, render_template_string, request
from order_DB import db_connector

logger = logging.getLogger("admin_restaurant")

admin_bp = Blueprint("admin_restaurant", __name__)

ADMIN_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Admin Dashboard - Doraemon 21st Cen Eateries</title>
    <link href="https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;600;700&display=swap" rel="stylesheet">
    <style>
        :root {
            --bg-dark: #0f172a;
            --card-bg: #1e293b;
            --accent: #38bdf8;
            --accent-green: #22c55e;
            --accent-orange: #f97316;
            --accent-purple: #a855f7;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
            --border-color: #334155;
        }

        * { margin: 0; padding: 0; box-sizing: border-box; font-family: 'Outfit', sans-serif; }
        body { background-color: var(--bg-dark); color: var(--text-main); min-height: 100vh; padding: 20px; }

        header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 15px 25px;
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 12px;
            margin-bottom: 25px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.3);
        }

        .header-brand { display: flex; align-items: center; gap: 15px; }
        .logo-img { width: 50px; height: 50px; border-radius: 10px; object-fit: cover; }
        h1 { font-size: 1.5rem; font-weight: 700; color: var(--accent); }
        .subtitle { font-size: 0.85rem; color: var(--text-muted); }

        .live-badge {
            background: rgba(34, 197, 94, 0.15);
            color: var(--accent-green);
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
            display: flex;
            align-items: center;
            gap: 8px;
            border: 1px solid rgba(34, 197, 94, 0.3);
        }
        .pulse { width: 8px; height: 8px; background: var(--accent-green); border-radius: 50%; animation: pulse 1.5s infinite; }
        @keyframes pulse { 0% { opacity: 0.4; } 50% { opacity: 1; } 100% { opacity: 0.4; } }

        .orders-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
            gap: 20px;
        }

        .order-card {
            background: var(--card-bg);
            border: 1px solid var(--border-color);
            border-radius: 14px;
            padding: 18px;
            display: flex;
            flex-direction: column;
            gap: 12px;
            box-shadow: 0 4px 15px rgba(0,0,0,0.2);
            position: relative;
        }

        .card-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-bottom: 1px solid var(--border-color);
            padding-bottom: 10px;
        }

        .token-tag {
            background: var(--accent-purple);
            color: #fff;
            font-weight: 700;
            padding: 4px 10px;
            border-radius: 8px;
            font-size: 0.9rem;
        }

        .cust-info { display: flex; flex-direction: column; }
        .cust-name { font-size: 1.1rem; font-weight: 600; }
        .cust-table { font-size: 0.85rem; color: var(--text-muted); }

        .items-list {
            list-style: none;
            display: flex;
            flex-direction: column;
            gap: 6px;
            margin: 8px 0;
            max-height: 140px;
            overflow-y: auto;
        }

        .item-row {
            display: flex;
            justify-content: space-between;
            font-size: 0.9rem;
            color: var(--text-muted);
        }

        .card-footer {
            display: flex;
            justify-content: space-between;
            align-items: center;
            border-top: 1px solid var(--border-color);
            padding-top: 10px;
        }

        .total-price { font-weight: 700; font-size: 1.1rem; color: var(--accent-green); }

        .status-select {
            background: var(--bg-dark);
            color: var(--text-main);
            border: 1px solid var(--border-color);
            padding: 6px 12px;
            border-radius: 6px;
            font-weight: 600;
            cursor: pointer;
        }

        .nav-link {
            color: var(--accent);
            text-decoration: none;
            font-weight: 600;
            font-size: 0.9rem;
            margin-right: 15px;
        }
        .nav-link:hover { text-decoration: underline; }
    </style>
</head>
<body>

    <header>
        <div class="header-brand">
            <img src="/images/{{ logo_filename }}" alt="Logo" class="logo-img">
            <div>
                <h1>Doraemon 21st Cen Eateries - Admin Portal</h1>
                <div class="subtitle">Live Kitchen Order Queue (First-Come-First-Serve Basis)</div>
            </div>
        </div>
        <div>
            <a href="/" class="nav-link">← Go to Customer App</a>
            <span class="live-badge"><div class="pulse"></div> Live Sync Active</span>
        </div>
    </header>

    <div id="ordersContainer" class="orders-grid">
        <p style="color: var(--text-muted);">Loading active order queue...</p>
    </div>

    <script>
        async function fetchOrders() {
            try {
                const res = await fetch('/admin/api/orders');
                const orders = await res.json();

                const container = document.getElementById('ordersContainer');
                if (orders.length === 0) {
                    container.innerHTML = '<p style="color: var(--text-muted); grid-column: 1/-1;">No orders in queue yet.</p>';
                    return;
                }

                container.innerHTML = orders.map(order => `
                    <div class="order-card">
                        <div class="card-header">
                            <div class="cust-info">
                                <div class="cust-name">${order.customer_name}</div>
                                <div class="cust-table">Table #${order.table_number} | ${order.order_date}</div>
                            </div>
                            <div class="token-tag">TOKEN #${order.token_number}</div>
                        </div>

                        <ul class="items-list">
                            ${order.items.map(i => `
                                <li class="item-row">
                                    <span>${i.name} x ${i.qty}</span>
                                    <span>RS. ${i.total.toFixed(2)}</span>
                                </li>
                            `).join('')}
                        </ul>

                        <div class="card-footer">
                            <div class="total-price">RS. ${order.total_amount.toFixed(2)}</div>
                            <select class="status-select" onchange="updateStatus(${order.order_id}, this.value)">
                                <option value="Preparing" ${order.status === 'Preparing' ? 'selected' : ''}>Preparing</option>
                                <option value="Ready" ${order.status === 'Ready' ? 'selected' : ''}>Ready</option>
                                <option value="Served" ${order.status === 'Served' ? 'selected' : ''}>Served</option>
                            </select>
                        </div>
                    </div>
                `).join('');

            } catch (err) {
                console.error("Error fetching orders:", err);
            }
        }

        async function updateStatus(orderId, newStatus) {
            try {
                const res = await fetch(`/admin/api/orders/${orderId}/status`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ status: newStatus })
                });
                const data = await res.json();
                if (data.success) {
                    console.log(`Order #${orderId} status updated to ${newStatus}`);
                }
            } catch (err) {
                alert("Failed to update status.");
            }
        }

        // Auto-refresh order queue every 5 seconds
        fetchOrders();
        setInterval(fetchOrders, 5000);
    </script>
</body>
</html>
"""


@admin_bp.route("/admin")
def admin_dashboard():
    """Renders Admin Web Dashboard."""
    from menu_loader import menu_loader
    return render_template_string(ADMIN_HTML, logo_filename=menu_loader.logo_filename or "")


@admin_bp.route("/admin/api/orders", methods=["GET"])
def get_orders():
    """Returns order queue JSON for admin dashboard."""
    orders = db_connector.fetch_all_orders()
    return jsonify(orders)


@admin_bp.route("/admin/api/orders/<int:order_id>/status", methods=["POST"])
def update_status(order_id):
    """API endpoint to update order status."""
    data = request.json or {}
    new_status = data.get("status")

    if not new_status or new_status not in ["Preparing", "Ready", "Served"]:
        return jsonify({"success": False, "message": "Invalid status"}), 400

    success = db_connector.update_order_status(order_id, new_status)
    return jsonify({"success": success})
