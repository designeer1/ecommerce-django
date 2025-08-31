from pathlib import Path
import json
from datetime import datetime
from .models import CustomerProfile

DATA_FILE = Path(__file__).resolve().parent.parent / "owner" / "data.json"

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

def categories_processor(request):
    """Provides categories, subcategories, and all products with category info to templates."""
    data = load_data()
    categories = {}
    all_products = []

    for _, udata in data.get("user_data", {}).items():
        # Build categories and subcategories
        for cat in udata.get("categories", []):
            subcats = sorted(list({p["subcategory"] for p in udata.get("subcategories", {}).get(cat, [])}))
            categories[cat] = subcats

        # Collect all products with category info
        for cat_name, items in udata.get("subcategories", {}).items():
            for item in items:
                all_products.append({
                    "name": item["name"],
                    "subcategory": item.get("subcategory", ""),
                    "category": cat_name,  # Add category field
                    "image_path": item.get("image_path", item.get("image", "")),
                    "price": item.get("price", 0),
                })

    return {"categories": categories, "all_products": all_products}

def cart_count(request):
    """Provides cart count to all templates."""
    cart = request.session.get("cart", {})
    if not isinstance(cart, dict):  # Ensure cart is a dictionary
        cart = {}
        request.session["cart"] = cart
        request.session.modified = True
    total_items = sum(cart.values()) if cart else 0
    return {"cart_count": total_items}

def current_year(request):
    return {'now': datetime.now()}

def global_context(request):
    categories = get_categories_with_products()
    all_products = get_all_products()
    cart = request.session.get("cart", {})
    if not isinstance(cart, dict):  # Ensure cart is a dictionary
        cart = {}
        request.session["cart"] = cart
        request.session.modified = True
    cart_count = sum(cart.values()) if cart else 0
    
    return {
        'categories': categories,
        'all_products': all_products,
        'cart_count': cart_count,
    }

def profile_picture(request):
    context = {}
    if request.user.is_authenticated:
        try:
            profile = CustomerProfile.objects.get(user=request.user)
            context['user_profile'] = profile
        except CustomerProfile.DoesNotExist:
            # Create profile if it doesn't exist
            profile = CustomerProfile.objects.create(user=request.user)
            context['user_profile'] = profile
    return context