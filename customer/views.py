from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponseRedirect
from pathlib import Path
import json

DATA_FILE = Path(__file__).resolve().parent.parent / "owner" / "data.json"

# ---------- Utilities ----------
def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"users": {}, "user_data": {}}

def get_all_products():
    data = load_data()
    all_products = []
    for _, udata in data["user_data"].items():
        all_products.extend(udata.get("products", []))
    return all_products

def get_all_categories_and_subcategories():
    data = load_data()
    categories = {}
    for _, udata in data.get("user_data", {}).items():
        for p in udata.get("products", []):
            cat = p.get("category")
            sub = p.get("subcategory")
            if cat:
                if cat not in categories:
                    categories[cat] = set()
                if sub:
                    categories[cat].add(sub)
    for cat in categories:
        categories[cat] = list(categories[cat])
    return categories

# ---------- Auth ----------
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user:
            login(request, user)
            return redirect("customer_home")
        else:
            messages.error(request, "Invalid username or password")
    return render(request, "customer/login.html")

def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect("customer_register")
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken")
            return redirect("customer_register")
        User.objects.create_user(username=username, password=password)
        messages.success(request, "Account created successfully! Please login.")
        return redirect("customer_login")
    return render(request, "customer/register.html")

def logout_view(request):
    logout(request)
    return redirect("customer_login")

# ---------- Shop ----------
def home(request):
    all_products = get_all_products()
    categories = get_categories_with_products()
    cart = request.session.get("cart", [])
    cart_count = sum(item['quantity'] for item in cart)
    
    return render(request, "customer/home.html", {
        "products": all_products,
        "categories": categories,
        "cart_count": cart_count
    })



def get_categories_with_products():
    data = load_data()
    user_data = data.get("user_data", {})
    result = {}

    for udata in user_data.values():
        sub_data = udata.get("subcategories", {})
        for cat, items in sub_data.items():
            if cat not in result:
                result[cat] = {}
            for item in items:
                sub = item["subcategory"]
                if sub not in result[cat]:
                    result[cat][sub] = []
                result[cat][sub].append({
                    "name": item["name"],
                    "image_path": item.get("image_path", ""),
                    "price": item.get("price", 0),
                })
    return result
def products_by_category(request, cat_name):
    filtered_products = [p for p in get_all_products() if p.get("category") == cat_name]
    categories = get_all_categories_and_subcategories()
    cart = request.session.get("cart", [])
    cart_count = sum(item['quantity'] for item in cart)
    return render(request, "customer/home.html", {
        "products": filtered_products,
        "categories": categories,
        "all_products": get_all_products(),
        "cart_count": cart_count
    })


def products_by_subcategory(request, sub_name):
    """
    Display products for a given subcategory name.
    """
    data = load_data()
    all_products = []

    # Loop through all users
    for _, udata in data.get("user_data", {}).items():
        # Each user has 'products' list
        for p in udata.get("products", []):
            # Match subcategory
            if p.get("subcategory") == sub_name:
                all_products.append({
                    "name": p.get("name"),
                    "subcategory": p.get("subcategory"),
                    "category": next((cat for cat, sublist in udata.get("subcategories", {}).items() if p in sublist), ""),
                    "price": p.get("price"),
                    "image_path": p.get("image_path", p.get("image"))
                })

    # Load categories for navbar
    categories = {}
    for _, udata in data.get("user_data", {}).items():
        for cat in udata.get("categories", []):
            categories[cat] = sorted(list({p["subcategory"] for p in udata.get("subcategories", {}).get(cat, [])}))

    # Cart count
    cart = request.session.get("cart", [])
    cart_count = sum(item['quantity'] for item in cart)

    return render(request, "customer/home.html", {
        "products": all_products,
        "categories": categories,
        "all_products": get_all_products(),
        "cart_count": cart_count
    })



def product_detail(request, product_name):
    product = next((p for p in get_all_products() if p.get("name") == product_name), None)
    categories = get_all_categories_and_subcategories()
    cart = request.session.get("cart", [])
    cart_count = sum(item['quantity'] for item in cart)
    return render(request, "customer/product_detail.html", {
        "product": product,
        "categories": categories,
        "all_products": get_all_products(),
        "cart_count": cart_count
    })

# ---------- Cart ----------
def add_to_cart(request, product_name):
    cart = request.session.get("cart", [])
    for item in cart:
        if item["name"] == product_name:
            item["quantity"] += 1
            break
    else:
        cart.append({"name": product_name, "quantity": 1})
    request.session["cart"] = cart
    request.session["cart_seen"] = False
    request.session.modified = True
    return redirect("customer_home")

def remove_from_cart(request, product_name):
    cart = request.session.get("cart", [])
    cart = [item for item in cart if item["name"] != product_name]
    request.session["cart"] = cart
    request.session.modified = True
    return redirect("customer_cart")

def cart_view(request):
    data = load_data()
    cart = request.session.get("cart", [])
    all_products = get_all_products()
    cart_products = []
    for item in cart:
        for p in all_products:
            if p["name"] == item["name"]:
                cart_products.append({
                    "name": p["name"],
                    "price": p["price"],
                    "image_path": p["image_path"],
                    "quantity": item["quantity"]
                })
    request.session["cart_seen"] = True
    return render(request, "customer/cart.html", {"products": cart_products})

def cart_table_view(request):
    cart = request.session.get("cart", [])
    all_products = get_all_products()
    cart_products = []
    grand_total = 0
    for item in cart:
        for p in all_products:
            if p["name"] == item["name"]:
                total_price = item["quantity"] * float(p["price"])
                grand_total += total_price
                cart_products.append({
                    "name": p["name"],
                    "price": p["price"],
                    "image_path": p["image_path"],
                    "quantity": item["quantity"],
                    "total_price": total_price
                })
    return render(request, "customer/cart_table.html", {"products": cart_products, "grand_total": grand_total})

def increment_cart_item(request, product_name):
    cart = request.session.get("cart", [])
    for item in cart:
        if item["name"] == product_name:
            item["quantity"] += 1
            break
    request.session["cart"] = cart
    request.session.modified = True
    return HttpResponseRedirect(reverse("cart_table"))

def decrement_cart_item(request, product_name):
    cart = request.session.get("cart", [])
    for item in cart:
        if item["name"] == product_name:
            if item["quantity"] > 1:
                item["quantity"] -= 1
            else:
                cart.remove(item)
            break
    request.session["cart"] = cart
    request.session.modified = True
    return HttpResponseRedirect(reverse("cart_table"))

# views.py
def checkout_address(request):
    if request.method == "POST":
        request.session["address"] = {
            "full_name": request.POST.get("full_name"),
            "address": request.POST.get("address"),
            "city": request.POST.get("city"),
            "pincode": request.POST.get("pincode"),
            "phone": request.POST.get("phone"),
        }
        request.session.modified = True
        return redirect("checkout_payment")
    return render(request, "customer/checkout_address.html")

# Show products by category
def products_by_category(request, category_name):
    all_products = get_all_products()
    filtered = [p for p in all_products if p.get("category")==category_name]
    return render(request, "customer/home.html", {"products": filtered})

# Show single product
def product_detail(request, product_name):
    all_products = get_all_products()
    product = next((p for p in all_products if p.get("name") == product_name), None)

    if product:
        # Main product
        product["rating"] = product.get("rating", 5)
        product["description"] = product.get(
            "description",
            f"This is a high-quality {product['name']}. Crafted with premium materials, it offers comfort, style, and durability. Perfect for daily wear or special occasions."
        )

        # Related products from same subcategory
        related_products = [
            {**p, "rating": p.get("rating", 5)}
            for p in all_products
            if p.get("subcategory") == product.get("subcategory") and p.get("name") != product_name
        ]
    else:
        related_products = []

    return render(request, "customer/product_detail.html", {
        "product": product,
        "related_products": related_products
    })


import razorpay
from django.conf import settings

def checkout_payment(request):
    cart = request.session.get("cart", [])
    all_products = get_all_products()

    total = 0
    cart_products = []

    for item in cart:
        for p in all_products:
            if p["name"] == item["name"]:
                price = float(p["price"])
                quantity = item["quantity"]
                item_total = price * quantity
                total += item_total
                cart_products.append({
                    "name": p["name"],
                    "price": price,
                    "quantity": quantity,
                    "total": item_total,
                    "image_path": p.get("image_path", "")
                })

    # Default values
    discount = 0
    grand_total = total
    coupon_applied = False
    coupon_code = ""

    # If user submitted coupon
    if request.method == "POST":
        coupon_code = request.POST.get("coupon_code", "").strip()
        if coupon_code == "DISCOUNT20":
            discount = 0.2 * total
            grand_total = total - discount
            coupon_applied = True

    # Razorpay requires amount in paise
    amount_in_paise = int(grand_total * 100)

    # Create Razorpay order
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_SECRET_KEY))
    razorpay_order = client.order.create({
        "amount": amount_in_paise,
        "currency": "INR",
        "payment_capture": 1
    })

    # Save invoice to session
    request.session["invoice"] = {
        "products": cart_products,
        "total": total,
        "discount": discount,
        "grand_total": grand_total,
        "order_id": razorpay_order['id']
    }

    return render(request, "customer/checkout_payment.html", {
        "cart_products": cart_products,
        "total": total,
        "discount": discount,
        "grand_total": grand_total,
        "razorpay_key": settings.RAZORPAY_KEY_ID,
        "razorpay_order_id": razorpay_order["id"],
        "amount": amount_in_paise,
        "coupon_applied": coupon_applied,
        "coupon_code": coupon_code
    })

def place_order(request):
    if request.method == "POST":
        # Save order logic here or process payment
        request.session["cart"] = []
        messages.success(request, "Order placed successfully!")
        return redirect("customer_home")
    return redirect("checkout_payment")
def payment_success(request):
    invoice = request.session.get("invoice", {})
    address = request.session.get("address", {})

    # Optional: clear cart
    request.session["cart"] = []
    request.session.modified = True

    return render(request, "customer/payment_success.html", {
        "invoice": invoice,
        "address": address
    })

from django.http import HttpResponse
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

def download_invoice_pdf(request):
    invoice = request.session.get("invoice")
    address = request.session.get("address")

    if not invoice or not address:
        return HttpResponse("No invoice data found.", status=404)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="invoice.pdf"'

    c = canvas.Canvas(response, pagesize=letter)
    width, height = letter

    # Title
    c.setFont("Helvetica-Bold", 20)
    c.drawString(72, height - 72, "Payment Successful - Invoice")

    # Shipping Address
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, height - 120, "Shipping Address:")
    c.setFont("Helvetica", 12)
    y = height - 140
    for line in [
        address.get("full_name", ""),
        address.get("address", ""),
        f"{address.get('city', '')}, {address.get('pincode', '')}",
        f"Phone: {address.get('phone', '')}"
    ]:
        c.drawString(72, y, line)
        y -= 20

    # Invoice Details header
    y -= 20
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, y, "Invoice Details:")
    y -= 20

    # Table headers
    c.setFont("Helvetica-Bold", 12)
    c.drawString(72, y, "Product")
    c.drawString(300, y, "Qty")
    c.drawString(370, y, "Price (₹)")
    y -= 15
    c.line(72, y, 500, y)
    y -= 15

    c.setFont("Helvetica", 12)
    for item in invoice.get("items", []):
        c.drawString(72, y, item.get("name", ""))
        c.drawString(300, y, str(item.get("quantity", 1)))
        c.drawString(370, y, f"₹{item.get('total_price', 0)}")
        y -= 20

    y -= 10
    c.setFont("Helvetica-Bold", 12)
    c.drawString(250, y, "Total:")
    c.drawString(370, y, f"₹{invoice.get('total', 0)}")
    y -= 20

    c.drawString(250, y, "Discount:")
    c.drawString(370, y, f"₹{invoice.get('discount', 0)}")
    y -= 20

    c.drawString(250, y, "Grand Total:")
    c.drawString(370, y, f"₹{invoice.get('grand_total', 0)}")
    y -= 40

    c.drawString(72, y, f"Order ID: {invoice.get('order_id', '')}")

    c.showPage()
    c.save()

    return response
def track_order(request, order_id):
    # Mock order statuses for demo
    statuses = [
        "Order Placed",
        "Processing",
        "Shipped",
        "Out for Delivery",
        "Delivered"
    ]

    # Simulate current status index (e.g. "Processing")
    current_status_index = 1

    return render(request, "customer/track_order.html", {
        "order_id": order_id,
        "statuses": statuses,
        "current_status_index": current_status_index,
    })

def order_success(request):
    order_id = "order_R9KM15eIvDUlE2"  # Replace with real order ID from your order/payment processing
    # other context like invoice_items, totals, etc.

    context = {
        "order_id": order_id,
        # other context variables
    }
    return render(request, "customer/order_success.html", context)
