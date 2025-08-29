from django.urls import path
from . import views

urlpatterns = [
    # Dashboard
    path("", views.dashboard, name="dashboard"),
    
    # -------------------- Category Management --------------------
    path("manage_category/", views.manage_category, name="manage_category"),
    path("edit_category/<str:cat_name>/", views.edit_category, name="edit_category"),
    path("delete_category/<str:cat_name>/", views.delete_category, name="delete_category"),
    path("search-categories/", views.search_categories, name="search_categories"),
    path("categories/count/", views.get_category_count, name="category_count"),
    path("get-category-details/<str:cat_name>/", views.get_category_details, name="get_category_details"),

    # -------------------- Subcategory Management --------------------
    path("manage_subcategory/", views.manage_subcategory, name="manage_subcategory"),
    path("subcategories/add/", views.add_subcategory, name="add_subcategory"),
    path("subcategories/edit/<str:cat_name>/<str:old_subcat_name>/", views.edit_subcategory, name="edit_subcategory"),
    path("subcategories/delete/<str:category>/<str:name>/", views.delete_subcategory, name="delete_subcategory"),
    path("subcategories/search/", views.search_subcategories, name="search_subcategories"),
    path("subcategories/count/", views.get_subcategory_count, name="get_subcategory_count"),
    path("subcategories/update_rating/", views.update_subcategory_rating, name="update_subcategory_rating"),

    # -------------------- Product Management --------------------
    path("manage_products/", views.manage_products, name="manage_products"),
    path("edit_product/<str:old_name>/", views.edit_product, name="edit_product"),
    path("delete_product/<str:product_name>/", views.delete_product, name="delete_product"),

    # -------------------- Search --------------------
    path("search/", views.search_products, name="search_products"),

    # -------------------- Authentication --------------------
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout, name="logout"),

    # -------------------- Import/Export --------------------
    path('export-categories/', views.export_categories, name='export_categories'),
    path('import-categories/', views.import_categories, name='import_categories'),


    # subcategory\import\export
path('export-subcategories/', views.export_subcategories, name='export_subcategories'),
path('import-subcategories/', views.import_subcategories, name='import_subcategories'),
path('update-subcategory-image/', views.update_subcategory_image, name='update_subcategory_image'),


# Add these to your urlpatterns in urls.py
path('profile/', views.profile_view, name='profile'),
path('update-profile/', views.update_profile, name='update_profile'),

]