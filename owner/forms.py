from django import forms
from .models import Category, SubCategory

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name", "description", "image"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter category name"
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "placeholder": "Enter description",
                "rows": 3
            }),
        }

class SubCategoryForm(forms.ModelForm):
    class Meta:
        model = SubCategory
        fields = ["category", "name", "image"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Enter subcategory name"}),
            "category": forms.Select(attrs={"class": "form-select"}),
        }