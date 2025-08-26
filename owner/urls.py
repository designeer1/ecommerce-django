from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    
    # Category management
    path("manage_category/", views.manage_category, name="manage_category"),
    path("delete_category/<str:cat_name>/", views.delete_category, name="delete_category"),
    path("edit_category/<str:cat_name>/", views.edit_category, name="edit_category"),
    path("search-categories/", views.search_categories, name="search_categories"),
    path("categories/count/", views.get_category_count, name="category_count"),

    # Auth
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout, name="logout"),

    # Subcategory management
    path('manage_subcategory/', views.manage_subcategory, name='manage_subcategory'),
    path('subcategories/edit/<str:cat_name>/<str:old_subcat_name>/', views.edit_subcategory, name='edit_subcategory'),

    path('subcategories/delete/<str:category>/<str:name>/', views.delete_subcategory, name='delete_subcategory'),
    path('subcategories/search/', views.search_subcategories, name='search_subcategories'),
    path('subcategories/count/', views.get_subcategory_count, name='get_subcategory_count'),
    path("subcategories/update_rating/", views.update_subcategory_rating, name="update_subcategory_rating"),

    # Product management
    path("manage_products/", views.manage_products, name="manage_products"),
    path("edit_product/<str:old_name>/", views.edit_product, name="edit_product"),
    path("delete_product/<str:product_name>/", views.delete_product, name="delete_product"),

    # Search
    path("search/", views.search_products, name="search_products"),
]