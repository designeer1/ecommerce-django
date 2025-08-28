# views.py
import json
import os
import uuid
from pathlib import Path
from django.conf import settings
from django.shortcuts import render, redirect
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.http import require_GET
import logging
from django.db.models import Q
from django.urls import reverse

# Models and Forms
from .models import Category, SubCategory, Product
from .forms import CategoryForm, SubCategoryForm

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# -------------------- Data persistence --------------------
DATA_FILE = Path(__file__).parent / 'data.json'

def load_data():
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                logger.debug(f"Loaded data: {data}")
                return data
        except Exception as e:
            logger.error(f"Error loading data.json: {str(e)}")
            logger.warning("Returning default data due to error")
            default_data = {"users": {}, "user_data": {}}
            save_data(default_data)
            return default_data
    logger.warning("data.json does not exist, creating default")
    default_data = {"users": {}, "user_data": {}}
    save_data(default_data)
    return default_data

def save_data(data):
    try:
        with open(DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)
        logger.debug("Successfully saved data.json")
    except Exception as e:
        logger.error(f"Error saving data.json: {str(e)}")

# -------------------- Image Validation --------------------
def validate_image(image):
    valid_extensions = ['.jpg', '.jpeg', '.png']
    ext = os.path.splitext(image.name)[1].lower()
    if ext not in valid_extensions:
        raise ValidationError("Only JPG and PNG files are allowed.")
    if image.size > 5 * 1024 * 1024:  # 5MB limit
        raise ValidationError("Image file too large (max 5MB).")

# -------------------- Authentication --------------------
def login_view(request):
    data = load_data()
    users = data['users']
    user_data = data['user_data']
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
    data = load_data()
    users = data['users']
    user_data = data['user_data']
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
        logger.debug(f"Saved data after registration: {data}")
        return redirect("login")
    return render(request, "register.html", {"msg": ""})

def dashboard(request):
    return render(request, "dashboard.html")

def logout(request):
    request.session.pop("email", None)
    request.session.pop("username", None)
    return redirect("dashboard")

# -------------------- Search --------------------
def search_view(request):
    data = load_data()
    email = request.session.get("email")
    if not email:
        return redirect("login")

    query = request.GET.get("q", "").lower()
    results = []

    if query:
        user_data_email = data['user_data'].get(email, {})
        products = user_data_email.get("products", [])
        categories = user_data_email.get("categories", [])
        subcategories = user_data_email.get("subcategories", {})

        for p in products:
            product_name = p["name"].lower()
            subcat_name = p.get("subcategory", "").lower()
            description = p.get("description", "").lower()

            if query in product_name or query in subcat_name or query in description:
                results.append(p)
            else:
                for cat in categories:
                    if query in cat.lower():
                        if subcat_name in [s["subcategory"].lower() for s in subcategories.get(cat, [])]:
                            results.append(p)
                            break

    return render(request, "search_results.html", {"query": query, "results": results})

@require_GET
def search_products(request):
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        query = request.GET.get('q', '').strip().lower()
        if len(query) < 2:
            return JsonResponse({'results': []})

        matched_products = Product.objects.filter(name__icontains=query)[:10]
        results = []

        for product in matched_products:
            results.append({
                'id': product.pk,
                'name': product.name,
                'category': product.subcategory.category.name if product.subcategory and product.subcategory.category else 'N/A',
                'subcategory': product.subcategory.name if product.subcategory else 'N/A',
                'price': str(product.price),
                'description': product.__str__(),
                'image_path': product.image.url if product.image else '/static/images/no-image.png'
            })

        return JsonResponse({'results': results})

    return JsonResponse({'error': 'Invalid request'}, status=400)

# -------------------- Category --------------------
def manage_category(request):
    q = request.GET.get("q", "")
    sort = request.GET.get("sort", "")

    categories = Category.objects.all()

    if q:
        categories = categories.filter(
            Q(name__icontains=q) | Q(description__icontains=q)
        )

    if sort:
        categories = categories.order_by(sort)
    else:
        categories = categories.order_by("-id")  # latest first

    paginator = Paginator(categories, 5)  # 5 per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    form = CategoryForm()
    data = load_data()
    email = request.session.get("email")
    
    # Check for import status in session
    import_status = request.session.pop('import_status', None)

    if request.method == "POST":
        form = CategoryForm(request.POST, request.FILES)
        if form.is_valid():
            category = form.save()
            if email and email in data['user_data']:
                # Sync category with data.json
                user_data_email = data['user_data'][email]
                if "categories" not in user_data_email:
                    user_data_email["categories"] = []
                if "subcategories" not in user_data_email:
                    user_data_email["subcategories"] = {}
                if category.name not in user_data_email["categories"]:
                    user_data_email["categories"].append(category.name)
                    user_data_email["subcategories"][category.name] = []
                    save_data(data)
            return redirect("manage_category")

    return render(request, "manage_category.html", {
        "page_obj": page_obj,
        "form": form,
        "q": q,
        "sort": sort,
        "import_status": import_status,  # Pass import status to template
    })

def delete_category(request, cat_name):
    try:
        category = Category.objects.get(name=cat_name)
        category.delete()
        data = load_data()
        email = request.session.get("email")
        if email and email in data['user_data']:
            user_data_email = data['user_data'][email]
            if cat_name in user_data_email.get("categories", []):
                user_data_email["categories"].remove(cat_name)
            if cat_name in user_data_email.get("subcategories", {}):
                del user_data_email["subcategories"][cat_name]
            save_data(data)
    except Category.DoesNotExist:
        pass
    return redirect("manage_category")

def edit_category(request, cat_name):
    try:
        category = Category.objects.get(name=cat_name)
    except Category.DoesNotExist:
        return redirect("manage_category")

    data = load_data()
    email = request.session.get("email")

    if request.method == "POST":
        form = CategoryForm(request.POST, request.FILES, instance=category)
        if form.is_valid():
            old_name = cat_name
            category = form.save()
            if email and email in data['user_data']:
                user_data_email = data['user_data'][email]
                if old_name != category.name:
                    if old_name in user_data_email.get("categories", []):
                        user_data_email["categories"].remove(old_name)
                        user_data_email["categories"].append(category.name)
                    if old_name in user_data_email.get("subcategories", {}):
                        user_data_email["subcategories"][category.name] = user_data_email["subcategories"].pop(old_name)
                    save_data(data)
            return redirect("manage_category")
    else:
        form = CategoryForm(instance=category)

    return render(request, "edit_category.html", {"form": form})

def search_categories(request):
    q = request.GET.get("q", "")
    results = []
    if q:
        categories = Category.objects.filter(name__istartswith=q)[:5]
        results = [
            {
                "id": cat.id,
                "name": cat.name,
                "image": cat.image.url if cat.image else "",
            }
            for cat in categories
        ]
    return JsonResponse({"results": results})

def get_category_count(request):
    count = Category.objects.count()
    return JsonResponse({"count": count})

# -------------------- Subcategory --------------------
# views.py - Updated manage_subcategory view
# views.py - Update the manage_subcategory view
def manage_subcategory(request):
    email = request.session.get("email")
    if not email:
        return redirect("login")

    # Fetch categories from the Category model
    categories = [cat.name for cat in Category.objects.all()]
    data = load_data()
    user_data_email = data['user_data'].get(email, {})
    subcategories = user_data_email.get("subcategories", {})

    error = request.GET.get('error', '')
    success = request.GET.get('success', '')

    if request.method == "POST":
        category = request.POST.get("category")
        product_name = request.POST.get("name")
        subcategory_name = request.POST.get("subcategory")
        price = request.POST.get("price")
        description = request.POST.get("description")
        image = request.FILES.get("image")

        if not (category and product_name and subcategory_name and price):
            return redirect(reverse('manage_subcategory') + '?error=' + "All required fields must be filled.")

        # Check if product already exists
        if category in subcategories and any(sc["name"] == product_name for sc in subcategories[category]):
            return redirect(reverse('manage_subcategory') + '?error=' + f"A product named '{product_name}' already exists in category '{category}'.")

        try:
            relative_path = "/media/products/default.png"
            if image:
                validate_image(image)
                image_dir = os.path.join(settings.MEDIA_ROOT, "products")
                os.makedirs(image_dir, exist_ok=True)
                ext = os.path.splitext(image.name)[1]
                unique_filename = f"{uuid.uuid4().hex}{ext}"
                image_path = os.path.join(image_dir, unique_filename)
                with open(image_path, "wb+") as dest:
                    for chunk in image.chunks():
                        dest.write(chunk)
                relative_path = f"/media/products/{unique_filename}"

            if category not in subcategories:
                subcategories[category] = []
                
            subcategories[category].append({
                "name": product_name,
                "subcategory": subcategory_name,
                "price": float(price),
                "description": description or "",
                "image": relative_path,
                "category": category,
                "rating": 0
            })
            
            save_data(data)
            
            # Redirect back to manage_subcategory with success message
            return redirect(reverse('manage_subcategory') + '?success=Product added successfully')

        except ValidationError as e:
            return redirect(reverse('manage_subcategory') + '?error=' + str(e))

    # Collect all subcategories for display
    all_subs = []
    for cat, subs in subcategories.items():
        for sc in subs:
            sc["category"] = cat
            all_subs.append(sc)

    # Apply filtering if requested
    category_filter = request.GET.get('category', '')
    if category_filter:
        all_subs = [sc for sc in all_subs if sc.get("category", "").lower() == category_filter.lower()]

    # Apply sorting if requested
    sort_option = request.GET.get('sort', '')
    if sort_option:
        if sort_option == 'name_asc':
            all_subs.sort(key=lambda x: x.get("name", "").lower())
        elif sort_option == 'name_desc':
            all_subs.sort(key=lambda x: x.get("name", "").lower(), reverse=True)
        elif sort_option == 'price_asc':
            all_subs.sort(key=lambda x: float(x.get("price", 0)))
        elif sort_option == 'price_desc':
            all_subs.sort(key=lambda x: float(x.get("price", 0)), reverse=True)

    # Apply search if requested
    search_query = request.GET.get('q', '')
    if search_query:
        search_query = search_query.lower()
        all_subs = [sc for sc in all_subs 
                   if search_query in sc.get("name", "").lower() 
                   or search_query in sc.get("subcategory", "").lower()
                   or search_query in sc.get("category", "").lower()
                   or search_query in sc.get("description", "").lower()]

    # Apply pagination
    paginator = Paginator(all_subs, 5)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # Prepare all_subcategories for empty state fallback
    all_subcategories = all_subs if all_subs else []

    # Update total count based on subcategories
    total_count = len(all_subcategories)

    return render(request, "subcategory.html", {
        "categories": categories,
        "page_obj": page_obj,
        "error": error,
        "success": success,
        "all_subcategories": all_subcategories,
        "total_count": total_count,
        "current_category_filter": category_filter,
        "current_sort": sort_option,
        "current_search": search_query
    })

def delete_subcategory(request, category, name):
    data = load_data()
    email = request.session.get("email")
    if not email or email not in data['user_data']:
        return redirect("login")

    subcategories = data['user_data'][email].get("subcategories", {})
    if category in subcategories:
        subcategories[category] = [sc for sc in subcategories[category] if sc["name"] != name]
        save_data(data)

    return redirect("manage_subcategory")

def edit_subcategory(request, cat_name, old_subcat_name):
    email = request.session.get("email")
    if not email:
        return redirect("login")

    # Fetch categories from the Category model
    categories = [cat.name for cat in Category.objects.all()]
    data = load_data()
    user_data_email = data['user_data'].get(email, {})
    subcategories = user_data_email.get("subcategories", {})

    current_subcat = None
    if cat_name in subcategories:
        for sc in subcategories[cat_name]:
            if sc["name"] == old_subcat_name:
                current_subcat = sc
                break

    if not current_subcat:
        return redirect("manage_subcategory")

    if request.method == "POST":
        new_subcat_name = request.POST.get("subcategory")
        new_category = request.POST.get("category")
        new_name = request.POST.get("name")
        new_price = request.POST.get("price")
        description = request.POST.get("description")
        new_image = request.FILES.get("image")

        if new_category and new_subcat_name and new_name:
            try:
                # Handle image update
                if new_image:
                    validate_image(new_image)
                    image_dir = os.path.join(settings.MEDIA_ROOT, "products")
                    os.makedirs(image_dir, exist_ok=True)
                    ext = os.path.splitext(new_image.name)[1]
                    unique_filename = f"{uuid.uuid4().hex}{ext}"
                    image_path = os.path.join(image_dir, unique_filename)
                    with open(image_path, "wb+") as dest:
                        for chunk in new_image.chunks():
                            dest.write(chunk)
                    relative_path = f"/media/products/{unique_filename}"
                else:
                    relative_path = current_subcat.get("image", "/media/products/default.png")

                # Remove old subcategory entry
                subcategories[cat_name] = [sc for sc in subcategories[cat_name] if sc["name"] != old_subcat_name]

                # Ensure new category exists
                if new_category not in subcategories:
                    subcategories[new_category] = []

                # Add updated subcategory/product
                subcategories[new_category].append({
                    "name": new_name,
                    "subcategory": new_subcat_name,
                    "price": float(new_price) if new_price else current_subcat.get("price", 0),
                    "description": description or current_subcat.get("description", ""),
                    "image": relative_path,
                    "category": new_category,
                    "rating": current_subcat.get("rating", 0)
                })

                save_data(data)
            except ValidationError as e:
                return render(request, "subcategory.html", {
                    "categories": categories,
                    "error": str(e)
                })

        return redirect("manage_subcategory")

    # Fallback GET redirect
    return redirect("manage_subcategory")

def search_subcategories(request):
    data = load_data()
    email = request.session.get("email")
    if not email or email not in data['user_data']:
        return JsonResponse({"results": []})

    q = request.GET.get("q", "").lower()
    subcategories = data['user_data'][email].get("subcategories", {})

    all_subs = []
    for cat, subs in subcategories.items():
        for sc in subs:
            sc["category"] = cat
            all_subs.append(sc)

    results = [
        {
            "name": sc["name"],
            "subcategory": sc["subcategory"],
            "category": sc["category"],
            "price": sc["price"],
            "description": sc.get("description", ""),
            "image": sc.get("image", "/media/products/default.png"),
            "rating": sc.get("rating", 0)
        }
        for sc in all_subs
        if q in sc["name"].lower() or q in sc["subcategory"].lower() or q in sc["category"].lower()
    ]

    return JsonResponse({"results": results})

def get_subcategory_count(request):
    data = load_data()
    email = request.session.get("email")
    if not email or email not in data['user_data']:
        return JsonResponse({"count": 0})

    subcategories = data['user_data'][email].get("subcategories", {})
    count = sum(len(subs) for subs in subcategories.values())
    return JsonResponse({"count": count})

def update_subcategory_rating(request):
    data = load_data()
    email = request.session.get("email")
    if not email or email not in data['user_data']:
        return JsonResponse({"success": False})

    category = request.POST.get("category")
    name = request.POST.get("name")
    rating = int(request.POST.get("rating", 0))

    subcategories = data['user_data'][email].get("subcategories", {})
    if category in subcategories:
        for sc in subcategories[category]:
            if sc["name"] == name:
                sc["rating"] = rating
                save_data(data)
                return JsonResponse({"success": True, "rating": rating})

    return JsonResponse({"success": False})

# views.py - Update the add_subcategory view
def add_subcategory(request):
    email = request.session.get("email")
    if not email:
        return redirect("login")

    # Fetch categories from the Category model
    categories = [cat.name for cat in Category.objects.all()]
    data = load_data()
    user_data_email = data['user_data'].get(email, {})
    subcategories = user_data_email.get("subcategories", {})

    if request.method == "POST":
        category = request.POST.get("category")
        product_name = request.POST.get("name")
        subcategory_name = request.POST.get("subcategory")
        price = request.POST.get("price")
        description = request.POST.get("description")
        image = request.FILES.get("image")

        if not (category and product_name and subcategory_name and price):
            return redirect(reverse('manage_subcategory') + '?error=' + "All required fields must be filled.")

        # Check if product already exists
        if category in subcategories and any(sc["name"] == product_name for sc in subcategories[category]):
            return redirect(reverse('manage_subcategory') + '?error=' + f"A product named '{product_name}' already exists in category '{category}'.")

        try:
            relative_path = "/media/products/default.png"
            if image:
                validate_image(image)
                image_dir = os.path.join(settings.MEDIA_ROOT, "products")
                os.makedirs(image_dir, exist_ok=True)
                ext = os.path.splitext(image.name)[1]
                unique_filename = f"{uuid.uuid4().hex}{ext}"
                image_path = os.path.join(image_dir, unique_filename)
                with open(image_path, "wb+") as dest:
                    for chunk in image.chunks():
                        dest.write(chunk)
                relative_path = f"/media/products/{unique_filename}"

            # Add to subcategories in JSON data
            if category not in subcategories:
                subcategories[category] = []
                
            subcategories[category].append({
                "name": product_name,
                "subcategory": subcategory_name,
                "price": float(price),
                "description": description or "",
                "image": relative_path,
                "category": category,
                "rating": 0
            })
            
            # Save the updated data to JSON
            save_data(data)
            
            # Redirect back to manage_subcategory with success message
            return redirect(reverse('manage_subcategory') + '?success=Product added successfully')

        except ValidationError as e:
            return redirect(reverse('manage_subcategory') + '?error=' + str(e))

    return redirect("manage_subcategory")
# -------------------- Products --------------------
def manage_products(request):
    data = load_data()
    email = request.session.get("email")
    if not email:
        return redirect("login")

    user_data_email = data['user_data'][email]
    subcategories = user_data_email.get("subcategories", {})
    products = user_data_email.get("products", [])

    enriched_products = []

    # Collect products from subcategories
    for cat, subs in subcategories.items():
        for sc in subs:
            enriched_products.append({
                "name": sc.get("name", ""),
                "price": sc.get("price", 0),
                "image_path": sc.get("image", "/media/products/default.png"),
                "category": cat,
                "subcategory": sc.get("subcategory", "No Subcategory"),
                "description": sc.get("description", "")
            })

    # Collect products from products[]
    for p in products:
        enriched_products.append({
            "name": p.get("name", ""),
            "price": p.get("price", 0),
            "image_path": p.get("image_path", "/media/products/default.png"),
            "category": p.get("category", "No Category"),
            "subcategory": p.get("subcategory", "No Subcategory"),
            "description": p.get("description", "")
        })

    # ✅ No pagination — show all products
    return render(request, "products.html", {
        "products": enriched_products
    })

# owner/views.py
def delete_product(request, product_name):
    data = load_data()
    email = request.session.get("email")
    if not email:
        return redirect("login")

    user_data_email = data['user_data'][email]
    products = user_data_email["products"]
    subcategories = user_data_email["subcategories"]

    # Delete from products array
    for i, p in enumerate(products):
        if p["name"] == product_name:
            if p.get("image_path") and "/default.png" not in p["image_path"]:
                full_path = os.path.join(settings.MEDIA_ROOT, p["image_path"].replace("/media/", ""))
                if os.path.exists(full_path):
                    os.remove(full_path)
            del products[i]
            break
    
    # Delete from subcategories
    for cat, subs in subcategories.items():
        for i, sc in enumerate(subs):
            if sc["name"] == product_name:
                if sc.get("image") and "/default.png" not in sc["image"]:
                    full_path = os.path.join(settings.MEDIA_ROOT, sc["image"].replace("/media/", ""))
                    if os.path.exists(full_path):
                        os.remove(full_path)
                del subs[i]
                break

    save_data(data)
    
    # Clear cache if you're using any
    from django.core.cache import cache
    cache.clear()
    
    return redirect("manage_products")

def edit_product(request, old_name):
    data = load_data()
    email = request.session.get("email")
    if not email:
        return redirect("login")

    user_data_email = data['user_data'][email]
    products = user_data_email["products"]
    subcategories = user_data_email["subcategories"]
    product = next((p for p in products if p["name"] == old_name), None)
    if not product:
        return redirect("manage_products")

    if request.method == "POST":
        new_name = request.POST.get("name")
        price = request.POST.get("price")
        description = request.POST.get("description")
        image = request.FILES.get("image")

        if new_name and price:
            try:
                if image:
                    validate_image(image)
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
                product["name"] = new_name
                product["price"] = float(price)
                product["description"] = description or product.get("description", "")

                for cat, subs in subcategories.items():
                    for sc in subs:
                        if sc["name"] == old_name:
                            sc["name"] = new_name
                            sc["subcategory"] = product.get("subcategory")
                            sc["price"] = float(price)
                            sc["description"] = description or sc.get("description", "")
                            sc["image"] = product["image_path"]
                            break

                save_data(data)
            except ValidationError as e:
                return render(request, "edit_product.html", {"product": product, "error": str(e)})

        return redirect("manage_products")

    return render(request, "edit_product.html", {"product": product})

# -------------------- Utility --------------------
def get_all_categories_and_subcategories():
    data = load_data()
    categories = {}

    for _, udata in data.get("user_data", {}).items():
        subcats_dict = udata.get("subcategories", {})
        for cat_name, products_list in subcats_dict.items():
            if products_list:
                if cat_name not in categories:
                    categories[cat_name] = set()
                for p in products_list:
                    sub_name = p.get("subcategory")
                    if sub_name:
                        categories[cat_name].add(sub_name)

    for cat in categories:
        categories[cat] = sorted(list(categories[cat]))

    return categories


import csv
from django.http import HttpResponse
from django.contrib import messages
from io import TextIOWrapper, StringIO

# Add to your views.py

def export_categories(request):
    # Create a CSV response
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="categories_export.csv"'
    
    # Create a CSV writer
    writer = csv.writer(response)
    
    # Write headers
    writer.writerow(['Name', 'Description', 'Image Path'])
    
    # Get all categories
    categories = Category.objects.all().order_by('name')
    
    # Write category data
    for category in categories:
        image_path = category.image.path if category.image else ''
        writer.writerow([category.name, category.description or '', image_path])
    
    return response

import csv
from django.http import HttpResponse
from django.contrib import messages
from io import TextIOWrapper, StringIO
import os
from django.core.files import File

def import_categories(request):
    if request.method == 'POST' and request.FILES.get('csv_file'):
        csv_file = request.FILES['csv_file']
        has_headers = request.POST.get('has_headers') == 'on'
        
        # Process the CSV file
        try:
            # Read the CSV file
            decoded_file = TextIOWrapper(csv_file.file, encoding='utf-8')
            reader = csv.reader(decoded_file)
            
            rows = list(reader)
            if has_headers and rows:
                rows = rows[1:]  # Skip header row
            
            success_count = 0
            error_count = 0
            errors = []
            
            for i, row in enumerate(rows):
                if not row:  # Skip empty rows
                    continue
                    
                if len(row) < 1:  # At least name is required
                    error_count += 1
                    errors.append(f"Row {i+1}: Missing required name field")
                    continue
                
                name = row[0].strip()
                description = row[1].strip() if len(row) > 1 else ''
                image_path = row[2].strip() if len(row) > 2 else None
                
                if not name:
                    error_count += 1
                    errors.append(f"Row {i+1}: Category name cannot be empty")
                    continue
                
                # Check if category already exists
                try:
                    category, created = Category.objects.get_or_create(
                        name=name,
                        defaults={'description': description}
                    )
                    
                    # Handle image if provided
                    if image_path and os.path.exists(image_path):
                        with open(image_path, 'rb') as f:
                            category.image.save(
                                os.path.basename(image_path), 
                                File(f), 
                                save=True
                            )
                    
                    if not created:
                        # Update existing category
                        category.description = description
                        category.save()
                    
                    success_count += 1
                except Exception as e:
                    error_count += 1
                    errors.append(f"Row {i+1}: Error saving category - {str(e)}")
            
            # Prepare status message
            if error_count == 0:
                status = {
                    'type': 'success',
                    'icon': 'check-circle',
                    'message': f'Successfully imported {success_count} categories.'
                }
            else:
                status = {
                    'type': 'warning' if success_count > 0 else 'danger',
                    'icon': 'exclamation-triangle',
                    'message': f'Imported {success_count} categories with {error_count} errors.',
                    'errors': errors[:10]  # Show first 10 errors only
                }
                
            # Store status in session to display on page reload
            request.session['import_status'] = status
            
        except Exception as e:
            status = {
                'type': 'danger',
                'icon': 'exclamation-circle',
                'message': f'Error processing CSV file: {str(e)}'
            }
            request.session['import_status'] = status
    
    return redirect('manage_category')
