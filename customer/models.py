from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
import uuid, os


def user_profile_pic_path(instance, filename):
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4()}.{ext}"
    return os.path.join(f"user_{instance.user.id}", "profile_pics", filename)


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
