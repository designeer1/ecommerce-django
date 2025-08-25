from django import forms

class CategoryForm(forms.Form):
    category = forms.CharField(max_length=100, label="Category Name", required=True)