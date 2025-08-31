from django.shortcuts import render, redirect
from django.contrib.auth.models import User
from django.http import JsonResponse
from django.db.models import Count, Q
from django.core.paginator import Paginator
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
import json
from pathlib import Path
from django.conf import settings
from .models import OwnerStats
from django.db import transaction

# Load owner data from JSON
def load_owner_data():
    DATA_FILE = Path(__file__).parent.parent / 'owner' / 'data.json'
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading owner data: {e}")
            return {"users": {}, "user_data": {}}
    return {"users": {}, "user_data": {}}

# Check if user is superuser
def is_superuser(user):
    return user.is_authenticated and user.is_superuser

# Superadmin login
def superadmin_login(request):
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('superadmin_dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None and user.is_superuser:
            login(request, user)
            return redirect('superadmin_dashboard')
        else:
            return render(request, 'superadmin/login.html', {'error': 'Invalid credentials or not authorized'})
    
    return render(request, 'superadmin/login.html')

# Superadmin logout
def superadmin_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('superadmin_login')

def update_owner_stats():
    """Update or create owner statistics in the database"""
    data = load_owner_data()
    owners_data = data.get('users', {})
    user_data = data.get('user_data', {})
    
    with transaction.atomic():
        for email, owner_info in owners_data.items():
            # Calculate product count for this owner
            product_count = 0
            total_value = 0.00
            
            if email in user_data:
                udata = user_data[email]
                # Count from subcategories
                subcategories = udata.get('subcategories', {})
                for category, products in subcategories.items():
                    product_count += len(products)
                    # Calculate total value
                    for product in products:
                        total_value += float(product.get('price', 0))
                # Count from products array
                products_list = udata.get('products', [])
                product_count += len(products_list)
                for product in products_list:
                    total_value += float(product.get('price', 0))
            
            # Update or create the record
            OwnerStats.objects.update_or_create(
                owner_email=email,
                defaults={
                    'owner_name': owner_info.get('username', 'Unknown'),
                    'product_count': product_count,
                    'total_inventory_value': total_value
                }
            )

# Superadmin dashboard with authentication check
# In your views.py, update the superadmin_dashboard function
@login_required
@user_passes_test(is_superuser)
def superadmin_dashboard(request):
    """Admin dashboard showing owners and their products"""
    # Update statistics first
    update_owner_stats()
    
    # Get data from database
    owner_stats = OwnerStats.objects.all().order_by('-product_count')
    
    # Get totals for the cards
    total_owners = owner_stats.count()
    total_products = sum(stat.product_count for stat in owner_stats)
    total_inventory_value = sum(stat.total_inventory_value for stat in owner_stats)
    
    # Prepare owners list for template (without profile pictures)
    owners = []
    for stat in owner_stats:
        owners.append({
            'email': stat.owner_email,
            'username': stat.owner_name,
            'product_count': stat.product_count,
            'total_value': stat.total_inventory_value,
            'django_user': User.objects.filter(email=stat.owner_email).first()
        })
    
    return render(request, 'superadmin/dashboard.html', {
        'total_owners': total_owners,
        'total_products': total_products,
        'total_inventory_value': total_inventory_value,
        'owners': owners
    })

# Owner detail view
@login_required
@user_passes_test(is_superuser)
def owner_detail(request, email):
    """View details of a specific owner"""
    # Load owner data
    data = load_owner_data()
    owners_data = data.get('users', {})
    user_data = data.get('user_data', {})
    
    if email not in owners_data:
        messages.error(request, 'Owner not found.')
        return redirect('superadmin_dashboard')
    
    owner_info = owners_data[email]
    
    # Get owner's products and calculate inventory value
    products = []
    total_inventory_value = 0
    categories = set()
    
    if email in user_data:
        udata = user_data[email]
        
        # Products from subcategories
        subcategories = udata.get('subcategories', {})
        for category, product_list in subcategories.items():
            categories.add(category)
            for product in product_list:
                product_price = float(product.get('price', 0))
                total_inventory_value += product_price
                products.append({
                    'name': product.get('name', 'N/A'),
                    'category': category,
                    'subcategory': product.get('subcategory', 'N/A'),
                    'price': product_price,
                    'image': product.get('image', '/media/products/default.png'),
                    'description': product.get('description', ''),
                    'type': 'subcategory'
                })
        
        # Products from products array
        for product in udata.get('products', []):
            product_price = float(product.get('price', 0))
            total_inventory_value += product_price
            category = product.get('category', 'N/A')
            categories.add(category)
            products.append({
                'name': product.get('name', 'N/A'),
                'category': category,
                'subcategory': product.get('subcategory', 'N/A'),
                'price': product_price,
                'image_path': product.get('image_path', '/media/products/default.png'),
                'description': product.get('description', ''),
                'type': 'direct'
            })
    
    # Calculate average price
    average_price = total_inventory_value / len(products) if products else 0
    
    # Get Django user if exists
    django_user = User.objects.filter(email=email).first()
    
    return render(request, 'superadmin/owner_detail.html', {
        'owner': owner_info,
        'owner_email': email,
        'products': products,
        'product_count': len(products),
        'categories_count': len(categories),
        'total_inventory_value': total_inventory_value,
        'average_price': average_price,
        'store_rating': 4.5,  # You can replace this with actual rating logic
        'django_user': django_user
    })

# Get owner statistics
@login_required
@user_passes_test(is_superuser)
def get_owner_stats(request):
    """Get owner statistics for AJAX requests"""
    data = load_owner_data()
    owners_data = data.get('users', {})
    user_data = data.get('user_data', {})
    
    total_owners = len(owners_data)
    
    total_products = 0
    for email, udata in user_data.items():
        # Count products from subcategories
        subcategories = udata.get('subcategories', {})
        for category, products in subcategories.items():
            total_products += len(products)
        # Count products from products array
        total_products += len(udata.get('products', []))
    
    return JsonResponse({
        'total_owners': total_owners,
        'total_products': total_products
    })

# Delete owner account
@login_required
@user_passes_test(is_superuser)
def delete_owner(request, email):
    """Delete an owner account from both JSON and database"""
    if request.method == "POST":
        data = load_owner_data()
        owners_data = data.get('users', {})
        user_data = data.get('user_data', {})
        
        if email in owners_data:
            # Remove from owners data
            del owners_data[email]
            
            # Remove from user data
            if email in user_data:
                del user_data[email]
            
            # Save the updated data
            DATA_FILE = Path(__file__).parent.parent / 'owner' / 'data.json'
            try:
                with open(DATA_FILE, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False)
                
                # Also remove from database
                OwnerStats.objects.filter(owner_email=email).delete()
                
                messages.success(request, f'Owner {email} has been deleted successfully.')
            except Exception as e:
                messages.error(request, f'Error saving data: {e}')
        else:
            messages.error(request, 'Owner not found.')
    
    return redirect('superadmin_dashboard')

# View all products across all owners
@login_required
@user_passes_test(is_superuser)
def all_products(request):
    """View all products from all owners"""
    data = load_owner_data()
    user_data = data.get('user_data', {})
    
    all_products_list = []
    
    for email, udata in user_data.items():
        owner_info = data.get('users', {}).get(email, {})
        owner_name = owner_info.get('username', 'Unknown Owner')
        
        # Products from subcategories
        subcategories = udata.get('subcategories', {})
        for category, product_list in subcategories.items():
            for product in product_list:
                all_products_list.append({
                    'name': product.get('name', 'N/A'),
                    'category': category,
                    'subcategory': product.get('subcategory', 'N/A'),
                    'price': product.get('price', 0),
                    'image': product.get('image', '/media/products/default.png'),
                    'description': product.get('description', ''),
                    'owner': owner_name,
                    'owner_email': email,
                    'type': 'subcategory'
                })
        
        # Products from products array
        for product in udata.get('products', []):
            all_products_list.append({
                'name': product.get('name', 'N/A'),
                'category': product.get('category', 'N/A'),
                'subcategory': product.get('subcategory', 'N/A'),
                'price': product.get('price', 0),
                'image_path': product.get('image_path', '/media/products/default.png'),
                'description': product.get('description', ''),
                'owner': owner_name,
                'owner_email': email,
                'type': 'direct'
            })
    
    # Search functionality
    search_query = request.GET.get('q', '')
    if search_query:
        search_query = search_query.lower()
        all_products_list = [p for p in all_products_list 
                           if search_query in p['name'].lower() 
                           or search_query in p['category'].lower()
                           or search_query in p['subcategory'].lower()
                           or search_query in p['description'].lower()
                           or search_query in p['owner'].lower()]
    
    # Sort by product name
    all_products_list.sort(key=lambda x: x['name'].lower())
    
    # Pagination
    paginator = Paginator(all_products_list, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    return render(request, 'superadmin/all_products.html', {
        'page_obj': page_obj,
        'search_query': search_query,
        'total_products': len(all_products_list)
    })

# System statistics
@login_required
@user_passes_test(is_superuser)
def system_stats(request):
    """System-wide statistics"""
    data = load_owner_data()
    owners_data = data.get('users', {})
    user_data = data.get('user_data', {})
    
    # Basic stats
    total_owners = len(owners_data)
    
    total_products = 0
    total_categories = set()
    for email, udata in user_data.items():
        # Count products from subcategories
        subcategories = udata.get('subcategories', {})
        for category, products in subcategories.items():
            total_products += len(products)
            total_categories.add(category)
        # Count products from products array
        total_products += len(udata.get('products', []))
    
    # Product price statistics
    all_prices = []
    for email, udata in user_data.items():
        # Prices from subcategories
        subcategories = udata.get('subcategories', {})
        for category, products in subcategories.items():
            for product in products:
                all_prices.append(product.get('price', 0))
        # Prices from products array
        for product in udata.get('products', []):
            all_prices.append(product.get('price', 0))
    
    if all_prices:
        avg_price = sum(all_prices) / len(all_prices)
        max_price = max(all_prices)
        min_price = min(all_prices)
    else:
        avg_price = max_price = min_price = 0
    
    # Owner with most products
    owner_stats = []
    for email, owner_info in owners_data.items():
        product_count = 0
        if email in user_data:
            udata = user_data[email]
            # Count from subcategories
            subcategories = udata.get('subcategories', {})
            for category, products in subcategories.items():
                product_count += len(products)
            # Count from products array
            product_count += len(udata.get('products', []))
        
        owner_stats.append({
            'email': email,
            'username': owner_info.get('username', 'N/A'),
            'product_count': product_count
        })
    
    owner_stats.sort(key=lambda x: x['product_count'], reverse=True)
    top_owner = owner_stats[0] if owner_stats else None
    
    return render(request, 'superadmin/system_stats.html', {
        'total_owners': total_owners,
        'total_products': total_products,
        'total_categories': len(total_categories),
        'avg_price': round(avg_price, 2),
        'max_price': max_price,
        'min_price': min_price,
        'top_owner': top_owner,
        'owner_stats': owner_stats[:5]  # Top 5 owners
    })

# Add this to your superadmin/views.py
@login_required
@user_passes_test(is_superuser)
def superadmin_root(request):
    """Redirect to dashboard if logged in, otherwise to login"""
    if request.user.is_authenticated and request.user.is_superuser:
        return redirect('superadmin_dashboard')
    else:
        return redirect('superadmin_login')