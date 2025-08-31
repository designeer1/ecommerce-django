from django.shortcuts import render, redirect,get_object_or_404
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
# views.py
def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user:
            # Ensure user has a CustomerProfile
            profile, created = CustomerProfile.objects.get_or_create(user=user)
            login(request, user)
            return redirect("customer_home")
        else:
            messages.error(request, "Invalid username or password")
    return render(request, "customer/login.html")

# views.py - Update the register_view function
# views.py - Update the register_view function
def register_view(request):
    if request.method == "POST":
        # Get form data
        username = request.POST.get("username")
        password = request.POST.get("password")
        confirm_password = request.POST.get("confirm_password")
        email = request.POST.get("email")
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        phone_number = request.POST.get("phone_number")
        date_of_birth = request.POST.get("date_of_birth")
        profile_picture = request.FILES.get('profile_picture')
        
        # Validate passwords match
        if password != confirm_password:
            messages.error(request, "Passwords do not match")
            return render(request, "customer/register.html")
            
        # Check if username already exists
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already taken")
            return render(request, "customer/register.html")
            
        # Check if email already exists
        if User.objects.filter(email=email).exists():
            messages.error(request, "Email already registered")
            return render(request, "customer/register.html")
            
        try:
            # Create user with all fields
            user = User.objects.create_user(
                username=username, 
                password=password,
                email=email,
                first_name=first_name,
                last_name=last_name
            )
            
            # Create customer profile
            profile = CustomerProfile.objects.create(
                user=user,
                phone_number=phone_number,
                date_of_birth=date_of_birth if date_of_birth else None
            )
            
            # Handle profile picture if provided
            if profile_picture:
                profile.profile_picture = profile_picture
                profile.save()
            
            # Log the user in after registration
            user = authenticate(request, username=username, password=password)
            if user:
                login(request, user)
                messages.success(request, "Account created successfully!")
                return redirect("customer_home")
            else:
                messages.error(request, "Authentication failed after registration")
                return redirect("customer_login")
                
        except Exception as e:
            messages.error(request, f"Error creating account: {str(e)}")
            return render(request, "customer/register.html")
    
    # If GET request or form invalid, show registration form
    return render(request, "customer/register.html")

def logout_view(request):
    logout(request)
    return redirect("customer_login")


# views.py - Add these imports at the top
from django.contrib.auth.decorators import login_required
from .forms import ProfileUpdateForm

# Add this view function
# views.py
@login_required
def profile_settings(request):
    profile = CustomerProfile.objects.get(user=request.user)
    
    if request.method == 'POST':
        form = ProfileUpdateForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, 'Your profile has been updated!')
            return redirect('profile_settings')
    else:
        form = ProfileUpdateForm(instance=profile)
    
    return render(request, 'customer/profile_settings.html', {
        'form': form
    })
# views.py
# views.py
from django.contrib.auth.decorators import login_required

@login_required
def profile_view(request):
    try:
        profile = CustomerProfile.objects.get(user=request.user)
    except CustomerProfile.DoesNotExist:
        profile = CustomerProfile.objects.create(user=request.user)
    
    # Get user's recent orders
    recent_orders = CustomerOrder.objects.filter(user=request.user).order_by('-order_date')[:5]
    
    return render(request, 'customer/profile.html', {
        'profile': profile,
        'recent_orders': recent_orders,
        'user': request.user
    })

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

# views.py - Update the payment_success function
def payment_success(request):
    invoice = request.session.get("invoice", {})
    address = request.session.get("address", {})
    
    # Check if we have valid order data
    order_id = invoice.get('order_id')
    
    if not order_id:
        messages.error(request, "No order information found. Please contact support.")
        return redirect("customer_home")
    
    # Save order to database if user is authenticated
    if request.user.is_authenticated and invoice and address:
        # Check if order already exists to avoid duplicates
        if not CustomerOrder.objects.filter(order_id=order_id).exists():
            CustomerOrder.objects.create(
                user=request.user,
                order_id=order_id,
                products=invoice.get('products', []),
                total_amount=invoice.get('total', 0),
                discount_amount=invoice.get('discount', 0),
                grand_total=invoice.get('grand_total', 0),
                shipping_address=address
            )
    
    # Clear cart after successful payment
    request.session["cart"] = []
    request.session["notified_products"] = []
    request.session.modified = True
    
    return render(request, "customer/payment_success.html", {
        "invoice": invoice,
        "address": address,
        "order_id": order_id  # Pass order_id to template
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
    if not request.user.is_authenticated:
        messages.error(request, "Please login to track orders")
        return redirect("customer_login")

    if order_id:
        order = get_object_or_404(CustomerOrder, order_id=order_id, user=request.user)
        timeline = order.get_status_timeline()

        return render(request, "customer/track_order.html", {
            "show_tracking": True,
            "order_id": order_id,
            "specific_order": order,
            "timeline": timeline,
        })

    # fallback → show order history list
    orders = CustomerOrder.objects.filter(user=request.user).order_by('-order_date')
    return render(request, "customer/track_order.html", {
        "show_tracking": False,
        "orders": orders,
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

# Add this import at the top
from django.core.paginator import Paginator

def order_history(request):
    if not request.user.is_authenticated:
        messages.error(request, "Please login to view your order history")
        return redirect("customer_login")
    
    orders = CustomerOrder.objects.filter(user=request.user).order_by('-order_date')
    
    # Add pagination (10 orders per page)
    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get product images for each order
    all_products = get_all_products()
    for order in page_obj:
        for product in order.products:
            # Find the product image
            for p in all_products:
                if p["name"] == product["name"]:
                    product["image_path"] = p.get("image_path", "/media/products/default.png")
                    break
            else:
                product["image_path"] = "/media/products/default.png"
    
    return render(request, "customer/order_history.html", {
        "page_obj": page_obj,
        "orders_count": orders.count()
    })
# customer/views.py
from .models import NewProductNotification

def notifications_view(request):
    if not request.user.is_authenticated:
        return JsonResponse({'count': 0, 'notifications': []})
    
    # Get unread notifications
    unread_notifications = NewProductNotification.objects.filter(
        is_active=True
    ).exclude(
        notified_users=request.user
    )
    
    count = unread_notifications.count()
    
    # Prepare notification data
    notifications = []
    for notification in unread_notifications[:5]:  # Limit to 5 most recent
        # Find the product details
        product = next((p for p in get_all_products() if p.get("name") == notification.product_name), None)
        if product:
            notifications.append({
                'id': notification.id,
                'product_name': notification.product_name,
                'added_date': notification.added_date.strftime('%Y-%m-%d %H:%M'),
                'image_path': product.get('image_path', '/media/products/default.png'),
                'product_url': reverse('product_detail', args=[notification.product_name])
            })
    
    return JsonResponse({
        'count': count,
        'notifications': notifications
    })

def mark_notification_read(request, notification_id):
    if not request.user.is_authenticated:
        return JsonResponse({'success': False})
    
    try:
        notification = NewProductNotification.objects.get(id=notification_id)
        notification.notified_users.add(request.user)
        return JsonResponse({'success': True})
    except NewProductNotification.DoesNotExist:
        return JsonResponse({'success': False})

# customer/views.py
def all_notifications_view(request):
    if not request.user.is_authenticated:
        return redirect('customer_login')
    
    # Get all notifications (both read and unread)
    all_notifications = NewProductNotification.objects.filter(is_active=True)
    
    # Mark all as read for this user
    for notification in all_notifications.exclude(notified_users=request.user):
        notification.notified_users.add(request.user)
    
    # Prepare notification data with product details
    notifications_with_details = []
    for notification in all_notifications:
        product = next((p for p in get_all_products() if p.get("name") == notification.product_name), None)
        if product:
            is_read = notification.notified_users.filter(id=request.user.id).exists()
            notifications_with_details.append({
                'notification': notification,
                'product': product,
                'is_read': is_read,
                'product_url': reverse('product_detail', args=[notification.product_name])
            })
    
    return render(request, 'customer/all_notifications.html', {
        'notifications': notifications_with_details
    })

