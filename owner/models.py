from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True, null=True)
    image = models.ImageField(
        upload_to='category_images/',
        blank=True,
        null=True,
        default='/static/images/no-image.png'
    )

    def __str__(self):
        return self.name

class SubCategory(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="subcategories")
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='subcategory_images/', blank=True, null=True, default='/static/images/no-image.png')

    def __str__(self):
        return f"{self.category.name} - {self.name}"

    @property
    def image_path(self):
        if self.image:
            return self.image.url
        return '/static/images/no-image.png'

class Product(models.Model):
    name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    image = models.ImageField(upload_to='products/', blank=True, null=True)
    subcategory = models.ForeignKey(
        'SubCategory',
        on_delete=models.CASCADE,
        related_name='products',
        null=True,
        blank=True
    )

    @property
    def image_path(self):
        if self.image:
            return self.image.url
        return '/static/images/no-image.png'

    def __str__(self):
        return self.name





