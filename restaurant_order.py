"""
Python Restaurant Order Collecting Application (GUI Edition)
Built using Tkinter for interactive order collection, validation,
order summary display, and downloading itemized receipts.
"""

import os
import datetime
import tkinter as tk
from tkinter import ttk, messagebox

# ==========================================
# 01. DEFINE MENU ITEMS & DATA STRUCTURES
# ==========================================
MENU = {
    "Pizza": 250.0,
    "Burger": 150.0,
    "Pasta": 200.0,
    "Salad": 100.0,
    "Fries": 80.0,
    "Ice Cream": 120.0,
    "Cold Coffee": 90.0
}

# Order dictionary to store item quantities: { "Pizza": 2, "Burger": 1 }
current_order = {}


# ==========================================
# 02. HELPER & EVENT HANDLER FUNCTIONS
# ==========================================

def add_item_to_order():
    """Adds selected dish and quantity to the current order after validation."""
    customer_name = name_entry.get().strip()
    table_num = table_entry.get().strip()

    # Validate Customer Details
    if not customer_name:
        messagebox.showerror("Input Error", "Please enter the Customer Name.")
        name_entry.focus()
        return

    if not table_num:
        messagebox.showerror("Input Error", "Please enter the Table Number.")
        table_entry.focus()
        return

    dish = dish_combobox.get().strip()
    qty_str = qty_entry.get().strip()

    # Validate Dish Selection
    if dish not in MENU:
        messagebox.showerror("Input Error", f"'{dish}' is not a valid menu item.")
        return

    # Validate Quantity (Must be positive integer)
    if not qty_str.isdigit() or int(qty_str) <= 0:
        messagebox.showerror("Input Error", "Please enter a valid positive whole number for quantity.")
        qty_entry.focus()
        return

    qty = int(qty_str)

    # Update order dictionary
    current_order[dish] = current_order.get(dish, 0) + qty

    # Update GUI Order Summary
    update_order_treeview()

    # Reset selection inputs
    qty_entry.delete(0, tk.END)
    qty_entry.insert(0, "1")
    messagebox.showinfo("Item Added", f"Added {qty} x {dish} to your order.")


def remove_selected_item():
    """Removes the selected item from the current order."""
    selected_item = order_tree.selection()
    if not selected_item:
        messagebox.showwarning("Selection Error", "Please select an item from the order summary to remove.")
        return

    item_values = order_tree.item(selected_item, "values")
    dish_name = item_values[0]

    if dish_name in current_order:
        del current_order[dish_name]
        update_order_treeview()
        messagebox.showinfo("Item Removed", f"Removed '{dish_name}' from the order.")


def update_order_treeview():
    """Refreshes the Treeview display and updates the total bill label."""
    # Clear existing Treeview items
    for item in order_tree.get_children():
        order_tree.delete(item)

    total_bill = 0.0

    # Populate Treeview with current order items
    for dish, qty in current_order.items():
        price = MENU[dish]
        item_total = price * qty
        total_bill += item_total
        order_tree.insert("", tk.END, values=(dish, qty, f"RS. {price:.2f}", f"RS. {item_total:.2f}"))

    # Update Total Bill Label
    total_label.config(text=f"Total Bill: RS. {total_bill:.2f}")


def place_order():
    """Finalizes and validates the current order."""
    customer_name = name_entry.get().strip()
    table_num = table_entry.get().strip()

    if not customer_name or not table_num:
        messagebox.showerror("Order Error", "Please enter Customer Name and Table Number before placing an order.")
        return

    if not current_order:
        messagebox.showerror("Order Error", "Your order is empty. Please add items before placing an order.")
        return

    messagebox.showinfo("Order Placed", f"Order placed successfully for {customer_name} (Table #{table_num})!")


def generate_bill():
    """Step 03: Bill Generation - Formats receipt and saves to bill.txt."""
    customer_name = name_entry.get().strip()
    table_num = table_entry.get().strip()

    # Validate before bill download
    if not customer_name or not table_num:
        messagebox.showerror("Bill Generation Error", "Customer Name and Table Number are required to download the bill.")
        return

    if not current_order:
        messagebox.showerror("Bill Generation Error", "Cannot generate bill for an empty order.")
        return

    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    total_bill = 0.0
    bill_lines = []
    bill_lines.append("===================================================\n")
    bill_lines.append("             PYTHON RESTAURANT RECEIPT             \n")
    bill_lines.append("===================================================\n")
    bill_lines.append(f" Date & Time:   {now}\n")
    bill_lines.append(f" Customer Name: {customer_name}\n")
    bill_lines.append(f" Table Number:  {table_num}\n")
    bill_lines.append("---------------------------------------------------\n")
    bill_lines.append(f" {'Item':<18} {'Qty':<6} {'Unit Price':<12} {'Total':>8}\n")
    bill_lines.append("---------------------------------------------------\n")

    for dish, qty in current_order.items():
        unit_price = MENU[dish]
        item_total = unit_price * qty
        total_bill += item_total
        bill_lines.append(f" {dish:<18} {qty:<6} RS. {unit_price:<9.2f} RS. {item_total:>6.2f}\n")

    bill_lines.append("---------------------------------------------------\n")
    bill_lines.append(f" TOTAL BILL AMOUNT:                    RS. {total_bill:>6.2f}\n")
    bill_lines.append("===================================================\n")
    bill_lines.append("       Thank you for dining with us! Come again!    \n")
    bill_lines.append("===================================================\n")

    # Save receipt to bill.txt
    file_path = os.path.abspath("bill.txt")
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            f.writelines(bill_lines)
        messagebox.showinfo("Bill Saved", f"Bill has been downloaded successfully!\nSaved to: {file_path}")
    except Exception as e:
        messagebox.showerror("File Error", f"Failed to save bill file: {e}")


def reset_order():
    """Resets customer details, selection inputs, and current order."""
    if messagebox.askyesno("Reset Order", "Are you sure you want to clear the order and reset fields?"):
        current_order.clear()
        name_entry.delete(0, tk.END)
        table_entry.delete(0, tk.END)
        qty_entry.delete(0, tk.END)
        qty_entry.insert(0, "1")
        update_order_treeview()


# ==========================================
# 03. TKINTER GUI INITIALIZATION & LAYOUT
# ==========================================
root = tk.Tk()
root.title("Python Restaurant - Order Collecting System")
root.geometry("780x680")
root.minsize(700, 600)

# Apply standard Theme & Custom Styles
style = ttk.Style()
style.theme_use("clam")

# Custom Colors & Fonts
TITLE_BG = "#2C3E50"
ACCENT_BLUE = "#2980B9"
GREEN_BTN = "#27AE60"
RED_BTN = "#C0392B"

# Header Banner
header_frame = tk.Frame(root, bg=TITLE_BG, pady=12)
header_frame.pack(fill=tk.X)

header_title = tk.Label(
    header_frame,
    text="PYTHON RESTAURANT ORDER SYSTEM",
    font=("Segoe UI", 16, "bold"),
    fg="white",
    bg=TITLE_BG
)
header_title.pack()

# Main Container Frame
main_frame = ttk.Frame(root, padding="15")
main_frame.pack(fill=tk.BOTH, expand=True)

# ------------------------------------------
# Customer Details Frame
# ------------------------------------------
cust_frame = ttk.LabelFrame(main_frame, text=" 1. Customer Details ", padding="10")
cust_frame.pack(fill=tk.X, pady=(0, 10))

ttk.Label(cust_frame, text="Customer Name:", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
name_entry = ttk.Entry(cust_frame, width=25, font=("Segoe UI", 10))
name_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

ttk.Label(cust_frame, text="Table Number:", font=("Segoe UI", 10, "bold")).grid(row=0, column=2, padx=(20, 5), pady=5, sticky=tk.W)
table_entry = ttk.Entry(cust_frame, width=10, font=("Segoe UI", 10))
table_entry.grid(row=0, column=3, padx=5, pady=5, sticky=tk.W)

# ------------------------------------------
# Menu Display & Selection Frame (Paned Window)
# ------------------------------------------
content_pane = ttk.PanedWindow(main_frame, orient=tk.HORIZONTAL)
content_pane.pack(fill=tk.BOTH, expand=True, pady=5)

# Left Pane: Menu Table
menu_frame = ttk.LabelFrame(content_pane, text=" Restaurant Menu ", padding="10")
content_pane.add(menu_frame, weight=1)

menu_tree = ttk.Treeview(menu_frame, columns=("Item", "Price"), show="headings", height=8)
menu_tree.heading("Item", text="Dish Name")
menu_tree.heading("Price", text="Price (INR)")
menu_tree.column("Item", width=140, anchor=tk.W)
menu_tree.column("Price", width=90, anchor=tk.E)
menu_tree.pack(fill=tk.BOTH, expand=True)

# Populate Menu Treeview
for item, price in MENU.items():
    menu_tree.insert("", tk.END, values=(item, f"RS. {price:.2f}"))

# Right Pane: Order Selection & Controls
order_select_frame = ttk.LabelFrame(content_pane, text=" 2. Add to Order ", padding="10")
content_pane.add(order_select_frame, weight=1)

ttk.Label(order_select_frame, text="Select Dish:", font=("Segoe UI", 10, "bold")).grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
dish_combobox = ttk.Combobox(order_select_frame, values=list(MENU.keys()), state="readonly", width=18, font=("Segoe UI", 10))
dish_combobox.set(list(MENU.keys())[0])  # Default selection
dish_combobox.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

ttk.Label(order_select_frame, text="Quantity:", font=("Segoe UI", 10, "bold")).grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
qty_entry = ttk.Entry(order_select_frame, width=10, font=("Segoe UI", 10))
qty_entry.insert(0, "1")
qty_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

add_btn = tk.Button(
    order_select_frame,
    text="+ Add Item",
    command=add_item_to_order,
    bg=ACCENT_BLUE,
    fg="white",
    font=("Segoe UI", 10, "bold"),
    padx=10,
    pady=4,
    relief=tk.FLAT
)
add_btn.grid(row=2, column=0, columnspan=2, pady=12)

# ------------------------------------------
# Order Summary Frame
# ------------------------------------------
summary_frame = ttk.LabelFrame(main_frame, text=" 3. Order Summary & Receipt ", padding="10")
summary_frame.pack(fill=tk.BOTH, expand=True, pady=10)

order_tree = ttk.Treeview(summary_frame, columns=("Item", "Qty", "UnitPrice", "Total"), show="headings", height=6)
order_tree.heading("Item", text="Item Name")
order_tree.heading("Qty", text="Qty")
order_tree.heading("UnitPrice", text="Unit Price")
order_tree.heading("Total", text="Total Price")

order_tree.column("Item", width=160, anchor=tk.W)
order_tree.column("Qty", width=60, anchor=tk.CENTER)
order_tree.column("UnitPrice", width=100, anchor=tk.E)
order_tree.column("Total", width=100, anchor=tk.E)
order_tree.pack(fill=tk.BOTH, expand=True, side=tk.LEFT)

# Scrollbar for Order Summary
scrollbar = ttk.Scrollbar(summary_frame, orient=tk.VERTICAL, command=order_tree.yview)
order_tree.configure(yscroll=scrollbar.set)
scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

# Bottom Bar: Total Price & Action Buttons
bottom_frame = ttk.Frame(main_frame)
bottom_frame.pack(fill=tk.X, pady=(5, 0))

total_label = tk.Label(bottom_frame, text="Total Bill: RS. 0.00", font=("Segoe UI", 13, "bold"), fg="#2C3E50")
total_label.pack(side=tk.LEFT, padx=5)

# Action Buttons Frame
actions_frame = ttk.Frame(bottom_frame)
actions_frame.pack(side=tk.RIGHT)

remove_btn = tk.Button(
    actions_frame,
    text="Remove Item",
    command=remove_selected_item,
    bg="#E67E22",
    fg="white",
    font=("Segoe UI", 9, "bold"),
    padx=8,
    pady=3,
    relief=tk.FLAT
)
remove_btn.pack(side=tk.LEFT, padx=4)

place_btn = tk.Button(
    actions_frame,
    text="Place Order",
    command=place_order,
    bg=GREEN_BTN,
    fg="white",
    font=("Segoe UI", 9, "bold"),
    padx=8,
    pady=3,
    relief=tk.FLAT
)
place_btn.pack(side=tk.LEFT, padx=4)

download_btn = tk.Button(
    actions_frame,
    text="Download Bill",
    command=generate_bill,
    bg="#27AE60",
    fg="white",
    font=("Segoe UI", 9, "bold"),
    padx=8,
    pady=3,
    relief=tk.FLAT
)
download_btn.pack(side=tk.LEFT, padx=4)

reset_btn = tk.Button(
    actions_frame,
    text="Reset All",
    command=reset_order,
    bg=RED_BTN,
    fg="white",
    font=("Segoe UI", 9, "bold"),
    padx=8,
    pady=3,
    relief=tk.FLAT
)
reset_btn.pack(side=tk.LEFT, padx=4)

# Launch Tkinter Event Loop
if __name__ == "__main__":
    root.mainloop()
