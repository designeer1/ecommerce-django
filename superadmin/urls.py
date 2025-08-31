# superadmin/urls.py
from django.urls import path
from django.views.generic import RedirectView
from . import views

urlpatterns = [
    # Redirect root to login
    path('', RedirectView.as_view(url='login/', permanent=False), name='superadmin_root'),
    
    # Authentication
    path('login/', views.superadmin_login, name='superadmin_login'),
    path('logout/', views.superadmin_logout, name='superadmin_logout'),
    
    # Main pages
    path('dashboard/', views.superadmin_dashboard, name='superadmin_dashboard'),
    path('products/', views.all_products, name='all_products'),
    path('stats/', views.system_stats, name='system_stats'),
    
    # Owner management
    path('owner/<str:email>/', views.owner_detail, name='owner_detail'),
    path('owner/<str:email>/delete/', views.delete_owner, name='delete_owner'),
    
    # API endpoints
    path('api/owner-stats/', views.get_owner_stats, name='get_owner_stats'),
]