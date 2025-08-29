from django.core.management.base import BaseCommand
from owner.models import Category, SubCategory, Product
from pathlib import Path
import json

class Command(BaseCommand):
    help = 'Sync data from data.json to database'
    
    def handle(self, *args, **options):
        data_file = Path(__file__).resolve().parent.parent.parent / "owner" / "data.json"
        
        if data_file.exists():
            with open(data_file, "r") as f:
                data = json.load(f)
            
            for email, user_data in data.get('user_data', {}).items():
                # Sync categories
                for cat_name in user_data.get('categories', []):
                    category, created = Category.objects.get_or_create(
                        name=cat_name,
                        defaults={'description': f'Category for {cat_name}'}
                    )
                
                # Sync subcategories and products
                for cat_name, products in user_data.get('subcategories', {}).items():
                    try:
                        category = Category.objects.get(name=cat_name)
                        
                        for product_data in products:
                            subcategory, created = SubCategory.objects.get_or_create(
                                category=category,
                                name=product_data.get('subcategory', 'Unknown'),
                                defaults={'image': product_data.get('image', '').replace('/media/', '')}
                            )
                            
                            Product.objects.get_or_create(
                                name=product_data['name'],
                                defaults={
                                    'price': product_data['price'],
                                    'image': product_data.get('image', '').replace('/media/', ''),
                                    'subcategory': subcategory,
                                    'description': product_data.get('description', '')
                                }
                            )
                    except Category.DoesNotExist:
                        print(f"Category {cat_name} not found in database")
        
        self.stdout.write(self.style.SUCCESS('Data synced successfully'))