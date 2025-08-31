from django.apps import AppConfig

class SuperadminConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'superadmin'  # Change this
    label = 'superadmin'  # Add this to make it unique

from django.contrib import admin
from .models import OwnerStats

@admin.register(OwnerStats)
class OwnerStatsAdmin(admin.ModelAdmin):
    list_display = ('owner_name', 'owner_email', 'product_count', 'total_inventory_value', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('owner_name', 'owner_email')
    ordering = ('-product_count',)