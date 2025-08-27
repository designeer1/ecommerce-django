from django.db import models
from django.contrib.auth.models import User
import uuid
import os

def user_profile_pic_path(instance, filename):
    # File will be uploaded to MEDIA_ROOT/user_<id>/profile_pics/<filename>
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join('user_{0}', 'profile_pics', filename).format(instance.user.id)

class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_picture = models.ImageField(upload_to=user_profile_pic_path, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile"

class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.FloatField()
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to="products/", blank=True)

    def __str__(self):
        return self.name

class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1)
    
    @property
    def total_price(self):
        if self.product:
            return self.product.price * self.quantity
        return 0

    def __str__(self):
        product_name = self.product.name if self.product else "Unknown Product"
        return f"Cart({self.user.username} - {product_name})"

class Coupon(models.Model):
    code = models.CharField(max_length=10, unique=True)
    discount = models.FloatField(default=20.0)
    used_by = models.ManyToManyField(User, blank=True)

    def __str__(self):
        return self.code

class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    products = models.JSONField()
    total_amount = models.FloatField()
    coupon_code = models.CharField(max_length=50, blank=True, null=True)
    discount_amount = models.FloatField(default=0)
    full_name = models.CharField(max_length=255, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    pincode = models.CharField(max_length=20, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Order {self.id} - {self.user.username}"