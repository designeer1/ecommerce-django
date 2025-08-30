# forms.py
from django import forms
from django.contrib.auth.models import User
from .models import CustomerProfile

class ProfileUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=False)
    
    class Meta:
        model = CustomerProfile
        fields = ['profile_picture', 'phone_number', 'date_of_birth']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['email'].initial = self.instance.user.email
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        if commit:
            profile.save()
            # Update user email if provided
            email = self.cleaned_data.get('email')
            if email and profile.user:
                profile.user.email = email
                profile.user.save()
        return profile