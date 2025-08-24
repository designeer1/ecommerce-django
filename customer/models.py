from django.db import models
from django.contrib.auth.models import User
import uuid

class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.FloatField()
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="products/", blank=True)

    def __str__(self):
        return self.name

from django.db import models
from django.contrib.auth.models import User
from owner.models import Product

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    
    @property
    def total_price(self):
        return self.product.price * self.quantity


class Coupon(models.Model):
    code = models.CharField(max_length=10, unique=True)
    discount = models.FloatField(default=20.0)  # 20% discount
    used_by = models.ManyToManyField(User, blank=True)

    def __str__(self):
        return self.code

class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    products = models.JSONField()  # store cart items as JSON
    total_amount = models.FloatField()
    coupon_code = models.CharField(max_length=50, blank=True, null=True)
    discount_amount = models.FloatField(default=0)
    full_name = models.CharField(max_length=255)
    address = models.TextField()
    city = models.CharField(max_length=100)
    pincode = models.CharField(max_length=20)
    phone = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id} - {self.user.username}"
