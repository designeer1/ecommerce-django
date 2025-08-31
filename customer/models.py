# customer/models.py
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid, os
from django.core.exceptions import ValidationError
from django.contrib.auth.hashers import make_password, check_password


def user_profile_pic_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join(f"user_{instance.user.id}", "profile_pics", filename)

# customer/models.py - Add this model
class NewProductNotification(models.Model):
    product_name = models.CharField(max_length=255)
    added_date = models.DateTimeField(auto_now_add=True)
    notified_users = models.ManyToManyField(User, blank=True)
    is_active = models.BooleanField(default=True)
    
    def __str__(self):
        return f"New Product: {self.product_name}"
    
    class Meta:
        ordering = ['-added_date']
class CustomerProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    profile_picture = models.ImageField(upload_to=user_profile_pic_path, blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    
    # Additional fields for name and password storage
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    password_hash = models.CharField(max_length=128, blank=True)  # Store hashed password
    
    def __str__(self):
        return f"{self.user.username}'s Profile"
    
    def set_password(self, raw_password):
        """Hash and store the password"""
        self.password_hash = make_password(raw_password)
        self.save()
    
    def check_password(self, raw_password):
        """Verify the password against the stored hash"""
        return check_password(raw_password, self.password_hash)
    
    def save(self, *args, **kwargs):
        # Sync with User model if needed
        if self.user:
            if self.first_name and self.user.first_name != self.first_name:
                self.user.first_name = self.first_name
            if self.last_name and self.user.last_name != self.last_name:
                self.user.last_name = self.last_name
            self.user.save()
        super().save(*args, **kwargs)


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
        return self.product.price * self.quantity if self.product else 0

    def __str__(self):
        return f"Cart({self.user.username} - {self.product.name if self.product else 'Unknown'})"


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


# ✅ Unified CustomerOrder
class CustomerOrder(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('cancelled', 'Cancelled'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    order_id = models.CharField(max_length=100, unique=True)
    products = models.JSONField()
    total_amount = models.FloatField()
    discount_amount = models.FloatField(default=0)
    grand_total = models.FloatField()
    shipping_address = models.JSONField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    order_date = models.DateTimeField(auto_now_add=True)
    payment_status = models.CharField(max_length=20, default="Completed")

    def __str__(self):
        return f"Order {self.order_id} - {self.user.username} - {self.status}"

    def get_status_timeline(self):
        return self.orderstatushistory_set.order_by("changed_at")


class OrderStatusHistory(models.Model):
    order = models.ForeignKey(CustomerOrder, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=CustomerOrder.STATUS_CHOICES)
    changed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.order.order_id} - {self.status} at {self.changed_at}"