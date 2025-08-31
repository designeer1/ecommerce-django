from django.db import models
from django.contrib.auth.models import User

class OwnerStats(models.Model):
    owner_name = models.CharField(max_length=150)
    owner_email = models.EmailField(unique=True)
    product_count = models.IntegerField(default=0)
    total_inventory_value = models.DecimalField(max_digits=12, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'taskpro1_owner_stats'
        verbose_name = 'Owner Statistic'
        verbose_name_plural = 'Owner Statistics'
    
    def __str__(self):
        return f"{self.owner_name} - {self.product_count} products"