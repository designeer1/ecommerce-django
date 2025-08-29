from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponseRedirect, HttpResponse, JsonResponse
from pathlib import Path
import json
import razorpay
from django.conf import settings
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from .models import CustomerProfile, CustomerOrder

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
    seen_products = set()

    for _, udata in data.get("user_data", {}).items():
        subcategories = udata.get("subcategories", {})
        for cat, products in subcategories.items():
            for p in products:
                product_name = p.get("name")
                if product_name and product_name not in seen_products:
                    all_products.append({
                        "name": product_name,
                        "category": p.get("category", cat),
                        "subcategory": p.get("subcategory", ""),
                        "price": float(p.get("price", 0)),
                        "image_path": p.get("image", "/media/products/default.png"),
                        "description": p.get("description", ""),
                        "rating": p.get("rating", 5)
                    })
                    seen_products.add(product_name)

        for p in udata.get("products", []):
            product_name = p.get("name")
            if product_name and product_name not in seen_products:
                all_products.append({
                    "name": product_name,
                    "category": p.get("category", ""),
                    "subcategory": p.get("subcategory", ""),
                    "price": float(p.get("price", 0)),
                    "image_path": p.get("image_path", "/media/products/default.png"),
                    "description": p.get("description", ""),
                    "rating": p.get("rating", 5)
                })
                seen_products.add(product_name)

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
        subcategories = udata.get("subcategories", {})
        for cat, products in subcategories.items():
            if cat not in categories:
                categories[cat] = set()
            for p in products:
                sub = p.get("subcategory")
                if sub:
                    categories[cat].add(sub)
    for cat in categories:
        categories[cat] = list(categories[cat])
    return categories

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
                    "image_path": item.get("image", "/media/products/default.png"),
                    "price": item.get("price", 0),
                })
    return result

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
        profile_picture = request.FILES.get('profile_picture')
        
        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return redirect("customer_register")
            
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken")
            return redirect("customer_register")
            
        user = User.objects.create_user(username=username, password=password)
        
        profile, created = CustomerProfile.objects.get_or_create(user=user)
        if profile_picture:
            profile.profile_picture = profile_picture
            profile.save()
        
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
    cart_count = len(cart)
    new_product_added = request.session.get("new_product_added", None)
    if new_product_added:
        del request.session["new_product_added"]
        request.session.modified = True
    
    return render(request, "customer/home.html", {
        "products": all_products,
        "categories": categories,
        "cart_count": cart_count,
        "new_product_added": new_product_added
    })

def products_by_category(request, cat_name):
    filtered_products = [p for p in get_all_products() if p.get("category") == cat_name]
    categories = get_all_categories_and_subcategories()
    cart = request.session.get("cart", [])
    cart_count = len(cart)
    return render(request, "customer/home.html", {
        "products": filtered_products,
        "categories": categories,
        "all_products": get_all_products(),
        "cart_count": cart_count
    })

def products_by_subcategory(request, sub_name):
    data = load_data()
    all_products = []
    for _, udata in data.get("user_data", {}).items():
        for p in udata.get("products", []):
            if p.get("subcategory") == sub_name:
                all_products.append({
                    "name": p.get("name"),
                    "subcategory": p.get("subcategory"),
                    "category": p.get("category", ""),
                    "price": p.get("price"),
                    "image_path": p.get("image_path", "/media/products/default.png")
                })
        subcategories = udata.get("subcategories", {})
        for cat, products in subcategories.items():
            for p in products:
                if p.get("subcategory") == sub_name:
                    all_products.append({
                        "name": p.get("name"),
                        "subcategory": p.get("subcategory"),
                        "category": cat,
                        "price": p.get("price"),
                        "image_path": p.get("image", "/media/products/default.png")
                    })
    categories = get_all_categories_and_subcategories()
    cart = request.session.get("cart", [])
    cart_count = len(cart)
    return render(request, "customer/home.html", {
        "products": all_products,
        "categories": categories,
        "all_products": get_all_products(),
        "cart_count": cart_count
    })

def product_detail(request, product_name):
    product = next((p for p in get_all_products() if p.get("name") == product_name), None)
    if product:
        product["rating"] = product.get("rating", 5)
        product["description"] = product.get(
            "description",
            f"This is a high-quality {product['name']}. Crafted with premium materials, it offers comfort, style, and durability. Perfect for daily wear or special occasions."
        )
        related_products = [
            {**p, "rating": p.get("rating", 5)}
            for p in get_all_products()
            if p.get("subcategory") == product.get("subcategory") and p.get("name") != product_name
        ]
    else:
        related_products = []
    categories = get_all_categories_and_subcategories()
    cart = request.session.get("cart", [])
    cart_count = len(cart)
    return render(request, "customer/product_detail.html", {
        "product": product,
        "related_products": related_products,
        "categories": categories,
        "all_products": get_all_products(),
        "cart_count": cart_count
    })

# ---------- Cart ----------
def add_to_cart(request, product_name):
    cart = request.session.get("cart", [])
    notified_products = request.session.get("notified_products", [])
    
    product_exists = False
    for item in cart:
        if item["name"] == product_name:
            item["quantity"] += 1
            product_exists = True
            break
    if not product_exists:
        cart.append({"name": product_name, "quantity": 1})
        if product_name not in notified_products:
            request.session["new_product_added"] = product_name
            notified_products.append(product_name)
            request.session["notified_products"] = notified_products
        else:
            request.session["new_product_added"] = None
    else:
        request.session["new_product_added"] = None
    
    request.session["cart"] = cart
    request.session["cart_seen"] = False
    request.session.modified = True
    return redirect("customer_home")

def remove_from_cart(request, product_name):
    cart = request.session.get("cart", [])
    cart = [item for item in cart if item["name"] != product_name]
    notified_products = request.session.get("notified_products", [])
    if product_name in notified_products:
        notified_products.remove(product_name)
        request.session["notified_products"] = notified_products
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
    return render(request, "customer/cart.html", {
        "products": cart_products
    })

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
    return render(request, "customer/cart_table.html", {
        "products": cart_products,
        "grand_total": grand_total
    })

def increment_cart_item(request, product_name):
    cart = request.session.get("cart", [])
    for item in cart:
        if item["name"] == product_name:
            item["quantity"] += 1
            break
    request.session["cart"] = cart
    request.session["new_product_added"] = None
    request.session.modified = True
    return HttpResponseRedirect(reverse("customer_cart"))

def decrement_cart_item(request, product_name):
    cart = request.session.get("cart", [])
    for item in cart:
        if item["name"] == product_name:
            if item["quantity"] > 1:
                item["quantity"] -= 1
            else:
                cart.remove(item)
                notified_products = request.session.get("notified_products", [])
                if product_name in notified_products:
                    notified_products.remove(product_name)
                    request.session["notified_products"] = notified_products
            break
    request.session["cart"] = cart
    request.session["new_product_added"] = None
    request.session.modified = True
    return HttpResponseRedirect(reverse("customer_cart"))

def checkout_address(request):
    cart = request.session.get("cart", [])
    if not cart:
        return redirect("customer_cart")

    previous_addresses = request.session.get("previous_addresses", [])
    if request.session.get("address"):
        previous_addresses = [request.session["address"]] + previous_addresses[:2]
        request.session["previous_addresses"] = previous_addresses
        request.session.modified = True

    if request.method == "POST":
        if 'full_name' in request.POST:
            new_address = {
                "full_name": request.POST.get("full_name"),
                "address": request.POST.get("address"),
                "city": request.POST.get("city"),
                "pincode": request.POST.get("pincode"),
                "phone": request.POST.get("phone"),
            }
            previous_addresses.insert(0, new_address)
            request.session["previous_addresses"] = previous_addresses[:3]
            request.session["address"] = new_address
            request.session.modified = True
            return JsonResponse({"success": True})
        elif 'selected_address_index' in request.POST:
            index = int(request.POST.get("selected_address_index"))
            if 0 <= index < len(previous_addresses):
                request.session["address"] = previous_addresses[index]
                request.session.modified = True
                return JsonResponse({"success": True})
            return JsonResponse({"success": False, "error": "Invalid address selection"})
        elif 'delete_address_index' in request.POST:
            index = int(request.POST.get("delete_address_index"))
            if 0 <= index < len(previous_addresses):
                deleted_address = previous_addresses.pop(index)
                request.session["previous_addresses"] = previous_addresses
                request.session.modified = True
                if request.session.get("address") == deleted_address and previous_addresses:
                    request.session["address"] = previous_addresses[0]
                elif not previous_addresses:
                    request.session["address"] = None
                return JsonResponse({"success": True})
            return JsonResponse({"success": False, "error": "Invalid address index"})
        return JsonResponse({"success": False, "error": "Invalid request"})

    return render(request, "customer/checkout_address.html", {
        "previous_addresses": previous_addresses,
        "selected_address": request.session.get("address")
    })

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

    discount = 0
    grand_total = total
    coupon_applied = False
    coupon_code = ""

    if request.method == "POST":
        coupon_code = request.POST.get("coupon_code", "").strip()
        if coupon_code == "DISCOUNT20":
            discount = 0.2 * total
            grand_total = total - discount
            coupon_applied = True

    amount_in_paise = int(grand_total * 100)
    client = razorpay.Client(auth=(settings.RAZORPAY_KEY_ID, settings.RAZORPAY_SECRET_KEY))
    razorpay_order = client.order.create({
        "amount": amount_in_paise,
        "currency": "INR",
        "payment_capture": 1
    })

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
        request.session["notified_products"] = []
        request.session["cart"] = []
        messages.success(request, "Order placed successfully!")
        return redirect("customer_home")
    return redirect("checkout_payment")

def payment_success(request):
    invoice = request.session.get("invoice", {})
    address = request.session.get("address", {})
    
    # Save order to database if user is authenticated
    if request.user.is_authenticated and invoice and address:
        # Check if order already exists to avoid duplicates
        if not CustomerOrder.objects.filter(order_id=invoice.get('order_id')).exists():
            CustomerOrder.objects.create(
                user=request.user,
                order_id=invoice.get('order_id'),
                products=invoice.get('products', []),
                total_amount=invoice.get('total', 0),
                discount_amount=invoice.get('discount', 0),
                grand_total=invoice.get('grand_total', 0),
                shipping_address=address
            )
    
    request.session["cart"] = []
    request.session["notified_products"] = []
    request.session.modified = True
    return render(request, "customer/payment_success.html", {
        "invoice": invoice,
        "address": address
    })

def download_invoice_pdf(request):
    invoice = request.session.get("invoice")
    address = request.session.get("address")

    if not invoice or not address:
        return HttpResponse("No invoice data found.", status=404)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="invoice.pdf"'

    c = canvas.Canvas(response, pagesize=letter)
    width, height = letter

    c.setFont("Helvetica-Bold", 20)
    c.drawString(72, height - 72, "Payment Successful - Invoice")

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

    y -= 20
    c.setFont("Helvetica-Bold", 14)
    c.drawString(72, y, "Invoice Details:")
    y -= 20

    c.setFont("Helvetica-Bold", 12)
    c.drawString(72, y, "Product")
    c.drawString(300, y, "Qty")
    c.drawString(370, y, "Price (₹)")
    y -= 15
    c.line(72, y, 500, y)
    y -= 15

    c.setFont("Helvetica", 12)
    for item in invoice.get("products", []):
        c.drawString(72, y, item.get("name", ""))
        c.drawString(300, y, str(item.get("quantity", 1)))
        c.drawString(370, y, f"₹{item.get('total', 0)}")
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

def track_order(request, order_id=None):
    # If order_id is provided, show tracking for that specific order
    if order_id:
        statuses = [
            "Order Placed",
            "Processing",
            "Shipped",
            "Out for Delivery",
            "Delivered"
        ]
        current_status_index = 1
        
        # Try to get the order from database
        try:
            order = CustomerOrder.objects.get(order_id=order_id)
        except CustomerOrder.DoesNotExist:
            order = None
        
        return render(request, "customer/track_order.html", {
            "order_id": order_id,
            "statuses": statuses,
            "current_status_index": current_status_index,
            "specific_order": order,
            "show_tracking": True
        })
    
    # If no order_id provided, show order history
    if not request.user.is_authenticated:
        messages.error(request, "Please login to view your order history")
        return redirect("customer_login")
    
    orders = CustomerOrder.objects.filter(user=request.user).order_by('-order_date')
    
    return render(request, "customer/track_order.html", {
        "orders": orders,
        "show_tracking": False
    })
def order_success(request):
    order_id = "order_R9KM15eIvDUlE2"
    return render(request, "customer/order_success.html", {
        "order_id": order_id
    })

def order_history(request):
    if not request.user.is_authenticated:
        messages.error(request, "Please login to view your order history")
        return redirect("customer_login")
    
    orders = CustomerOrder.objects.filter(user=request.user).order_by('-order_date')
    
    return render(request, "customer/order_history.html", {
        "orders": orders
    })