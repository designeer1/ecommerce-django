from django.urls import path
from . import views

urlpatterns = [
        # Payment success page
    path('payment/success/', views.payment_success, name='payment_success'),

    # Track order page with order_id as parameter
    path('order/track/<str:order_id>/', views.track_order, name='track_order'),

    
    path("invoice/download/", views.download_invoice_pdf, name="download_invoice_pdf"),

    path('payment/success/', views.payment_success, name='payment_success'),


    path("checkout/payment/", views.checkout_payment, name="checkout_payment"),
path("place-order/", views.place_order, name="place_order"),

    
    path('', views.home, name='customer_home'),
    path('login/', views.login_view, name='customer_login'),
    path('register/', views.register_view, name='customer_register'),
    path('logout/', views.logout_view, name='customer_logout'),

    path('cart/', views.cart_view, name='customer_cart'),
    path('cart-table/', views.cart_table_view, name='cart_table'),
    path('add-to-cart/<str:product_name>/', views.add_to_cart, name='add_to_cart'),
    path('remove-from-cart/<str:product_name>/', views.remove_from_cart, name='remove_from_cart'),
    path('cart/increment/<str:product_name>/', views.increment_cart_item, name='increment_cart_item'),
    path('cart/decrement/<str:product_name>/', views.decrement_cart_item, name='decrement_cart_item'),

    path("checkout/address/", views.checkout_address, name="checkout_address"),

    # ✅ Category/Subcategory URLs
    path('category/<str:category_name>/', views.products_by_category, name='products_by_category'),
    path('subcategory/<str:subcategory_name>/', views.products_by_subcategory, name='products_by_subcategory'),

    # Optional: individual product detail
    path('product/<str:product_name>/', views.product_detail, name='product_detail'),
]
