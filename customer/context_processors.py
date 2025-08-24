from pathlib import Path
import json

DATA_FILE = Path(__file__).resolve().parent.parent / "owner" / "data.json"

def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    return {"users": {}, "user_data": {}}

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
    cart = request.session.get("cart", [])
    total_items = sum(item["quantity"] for item in cart)
    return {"cart_count": total_items}
# yourapp/context_processors.py
from datetime import datetime

def current_year(request):
    return {'now': datetime.now()}
