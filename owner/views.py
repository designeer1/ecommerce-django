import json
import os
import uuid
from pathlib import Path
from django.conf import settings
from django.shortcuts import render, redirect

# -------------------- Data persistence --------------------
DATA_FILE = Path(__file__).parent / 'data.json'

def load_data():
    if DATA_FILE.exists():
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {"users": {}, "user_data": {}}

def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f)

data = load_data()
users = data['users']
user_data = data['user_data']


# -------------------- Authentication --------------------
def login_view(request):
    if request.method == "POST":
        email = request.POST.get("email")
        password = request.POST.get("password")
        if email in users and users[email]["password"] == password:
            request.session["username"] = users[email]["username"]
            request.session["email"] = email
            if email not in user_data:
                user_data[email] = {
                    "categories": ["mens", "women", "baby"],
                    "subcategories": {cat: [] for cat in ["mens", "women", "baby"]},
                    "products": []
                }
                save_data(data)
            return redirect("dashboard")
        else:
            return render(request, "login.html", {"msg": "Invalid email or password"})
    return render(request, "login.html", {"msg": ""})

def register_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        email = request.POST.get("email")
        password = request.POST.get("password")
        if email in users:
            return render(request, "register.html", {"msg": "Email already registered"})
        if not username or not email or not password:
            return render(request, "register.html", {"msg": "All fields are required"})
        users[email] = {"username": username, "password": password}
        user_data[email] = {
            "categories": ["mens", "women", "baby"],
            "subcategories": {cat: [] for cat in ["mens", "women", "baby"]},
            "products": []
        }
        save_data(data)
        return redirect("login")
    return render(request, "register.html", {"msg": ""})

def dashboard(request):
    return render(request, "dashboard.html")

def logout(request):
    request.session.flush()
    return redirect("dashboard")


#------------search_view------------------------------
def search_view(request):
    email = request.session.get("email")
    if not email:
        return redirect("login")

    query = request.GET.get("q", "").lower()
    results = []

    if query:
        products = user_data[email]["products"]
        categories = user_data[email]["categories"]
        subcategories = user_data[email]["subcategories"]

        for p in products:
            product_name = p["name"].lower()
            subcat_name = p.get("subcategory", "").lower()

            # 🔹 Case 1: Match by product name
            if query in product_name:
                results.append(p)
                continue

            # 🔹 Case 2: Match by subcategory name
            if query in subcat_name:
                results.append(p)
                continue

            # 🔹 Case 3: Match by category name (check parent category of product)
            for cat in categories:
                if query in cat.lower():
                    # include product if it belongs to this category
                    if subcat_name in [s["subcategory"].lower() for s in subcategories[cat]]:
                        results.append(p)
                        break

    return render(request, "search_results.html", {"query": query, "results": results})




# -------------------- Category --------------------
def manage_category(request):
    email = request.session.get("email")
    if not email:
        return redirect("login")

    categories = user_data[email]["categories"]

    if request.method == "POST":
        new_cat = request.POST.get("category")
        if new_cat and new_cat not in categories:
            categories.append(new_cat)
            user_data[email]["subcategories"][new_cat] = []
            save_data(data)
        return redirect("manage_category")

    return render(request, "manage_category.html", {"categories": categories})


def delete_category(request, cat_name):
    email = request.session.get("email")
    if not email:
        return redirect("login")

    categories = user_data[email]["categories"]
    subcategories = user_data[email]["subcategories"]

    if cat_name in categories:
        categories.remove(cat_name)
        del subcategories[cat_name]
        save_data(data)

    return redirect("manage_category")


def edit_category(request, old_name):
    email = request.session.get("email")
    if not email:
        return redirect("login")

    categories = user_data[email]["categories"]
    subcategories = user_data[email]["subcategories"]

    if request.method == "POST":
        new_name = request.POST.get("category")
        if old_name in categories and new_name:
            index = categories.index(old_name)
            categories[index] = new_name
            subcategories[new_name] = subcategories.pop(old_name)
            save_data(data)
        return redirect("manage_category")

    return render(request, "edit_category.html", {"old_name": old_name})


# -------------------- Subcategory --------------------
def manage_subcategory(request):
    email = request.session.get("email")
    if not email:
        return redirect("login")

    categories = user_data[email]["categories"]
    subcategories = user_data[email]["subcategories"]

    if request.method == "POST":
        category = request.POST.get("category")
        product_name = request.POST.get("name")
        subcategory_name = request.POST.get("subcategory")
        price = request.POST.get("price")
        image = request.FILES.get("image")

        if category in subcategories and product_name and subcategory_name:
            if not any(sc["name"] == product_name for sc in subcategories[category]):
                if image:
                    image_dir = os.path.join(settings.MEDIA_ROOT, 'products')
                    os.makedirs(image_dir, exist_ok=True)
                    ext = os.path.splitext(image.name)[1]
                    unique_filename = f"{uuid.uuid4().hex}{ext}"
                    image_path = os.path.join(image_dir, unique_filename)
                    with open(image_path, 'wb+') as dest:
                        for chunk in image.chunks():
                            dest.write(chunk)
                    relative_path = f"/media/products/{unique_filename}"
                else:
                    relative_path = "/media/products/default.png"

                subcategories[category].append({
                    "name": product_name,
                    "subcategory": subcategory_name,
                    "price": float(price),
                    "image": relative_path
                })

                user_data[email]['products'].append({
                    "name": product_name,
                    "subcategory": subcategory_name,
                    "price": float(price),
                    "image_path": relative_path
                })
                save_data(data)

        return redirect("manage_subcategory")

    return render(request, "subcategory.html", {
        "categories": categories,
        "subcategories": subcategories
    })

def delete_subcategory(request, category, name):
    email = request.session.get("email")
    if not email:
        return redirect("login")

    subcategories = user_data[email]["subcategories"]
    products = user_data[email]["products"]

    if category in subcategories:
        subcategories[category] = [sc for sc in subcategories[category] if sc["name"] != name]

    user_data[email]["products"] = [p for p in products if p["name"] != name]

    save_data(data)
    return redirect("manage_subcategory")


def edit_subcategory(request, cat_name, old_subcat_name):
    email = request.session.get("email")
    if not email:
        return redirect("login")

    categories = user_data[email]["categories"]
    subcategories = user_data[email]["subcategories"]

    if request.method == "POST":
        new_subcat_name = request.POST.get("subcategory")
        new_category = request.POST.get("category")
        if (cat_name in subcategories and old_subcat_name in subcategories[cat_name]
            and new_subcat_name and new_category in subcategories):

            subcategories[cat_name].remove(old_subcat_name)
            if new_subcat_name not in subcategories[new_category]:
                subcategories[new_category].append(new_subcat_name)
            save_data(data)
        return redirect("manage_subcategory")

    return render(request, "edit_subcategory.html", {
        "categories": categories,
        "current_category": cat_name,
        "old_subcat_name": old_subcat_name
    })


# -------------------- Products --------------------
def manage_products(request):
    email = request.session.get("email")
    if not email:
        return redirect("login")

    products = user_data[email]["products"]
    return render(request, "products.html", {"products": products})


def delete_product(request, product_name):
    email = request.session.get("email")
    if not email:
        return redirect("login")

    products = user_data[email]["products"]
    for i, p in enumerate(products):
        if p["name"] == product_name:
            if p.get("image_path") and "/default.png" not in p["image_path"]:
                full_path = os.path.join(settings.MEDIA_ROOT, p["image_path"].replace("/media/", ""))
                if os.path.exists(full_path):
                    os.remove(full_path)
            del products[i]
            save_data(data)
            break
    return redirect("manage_products")


def edit_product(request, old_name):
    email = request.session.get("email")
    if not email:
        return redirect("login")

    products = user_data[email]["products"]
    product = next((p for p in products if p["name"] == old_name), None)
    if not product:
        return redirect("manage_products")

    if request.method == "POST":
        new_name = request.POST.get("name")
        price = request.POST.get("price")
        image = request.FILES.get("image")

        if new_name and price:
            product["name"] = new_name
            product["price"] = float(price)

            if image:
                if product.get("image_path") and "/default.png" not in product["image_path"]:
                    full_path = os.path.join(settings.MEDIA_ROOT, product["image_path"].replace("/media/", ""))
                    if os.path.exists(full_path):
                        os.remove(full_path)

                image_dir = os.path.join(settings.MEDIA_ROOT, 'products')
                os.makedirs(image_dir, exist_ok=True)

                ext = os.path.splitext(image.name)[1]
                unique_filename = f"{uuid.uuid4().hex}{ext}"
                image_path = os.path.join(image_dir, unique_filename)
                with open(image_path, 'wb+') as dest:
                    for chunk in image.chunks():
                        dest.write(chunk)

                product["image_path"] = f"/media/products/{unique_filename}"

            save_data(data)
        return redirect("manage_products")

    return render(request, "edit_product.html", {"product": product})


# customer/views.py
def get_all_categories_and_subcategories():
    data = load_data()
    categories = {}

    for _, udata in data.get("user_data", {}).items():
        # Iterate the 'subcategories' dictionary
        subcats_dict = udata.get("subcategories", {})
        for cat_name, products_list in subcats_dict.items():
            if products_list:  # skip empty categories
                if cat_name not in categories:
                    categories[cat_name] = set()
                for p in products_list:
                    sub_name = p.get("subcategory")
                    if sub_name:
                        categories[cat_name].add(sub_name)

    # Convert sets to sorted lists for template
    for cat in categories:
        categories[cat] = sorted(list(categories[cat]))

    return categories
