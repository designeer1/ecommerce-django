from django.urls import path
from . import views

urlpatterns = [
    path("", views.dashboard, name="dashboard"),

    # Category management
    path("manage_category/", views.manage_category, name="manage_category"),
    path("delete_category/<str:cat_name>/", views.delete_category, name="delete_category"),
    path("edit_category/<str:old_name>/", views.edit_category, name="edit_category"),

    # Auth
    path("login/", views.login_view, name="login"),
    path("register/", views.register_view, name="register"),
    path("logout/", views.logout, name="logout"),

    # Subcategory management
    path("manage_subcategory/", views.manage_subcategory, name="manage_subcategory"),
    path("subcategory/delete/<str:category>/<str:name>/", views.delete_subcategory, name="delete_subcategory"),
    path("edit_subcategory/<str:cat_name>/<str:old_subcat_name>/", views.edit_subcategory, name="edit_subcategory"),

    # Product management
    path("manage_products/", views.manage_products, name="manage_products"),
    path("delete_product/<str:product_name>/", views.delete_product, name="delete_product"),
    path("edit_product/<str:old_name>/", views.edit_product, name="edit_product"),
#cart

path('manage_products/', views.manage_products, name='manage_products'),


    # Search
    path("search/", views.search_view, name="search"),
]
