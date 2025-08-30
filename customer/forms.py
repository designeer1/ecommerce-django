# forms.py
from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from .models import CustomerProfile


class ProfileUpdateForm(forms.ModelForm):
    email = forms.EmailField(required=False)
    first_name = forms.CharField(max_length=30, required=False)
    last_name = forms.CharField(max_length=30, required=False)
    password = forms.CharField(
        widget=forms.PasswordInput, 
        required=False,
        help_text="Leave blank if you don't want to change your password"
    )
    password_confirm = forms.CharField(
        widget=forms.PasswordInput, 
        required=False,
        label="Confirm Password"
    )
    
    class Meta:
        model = CustomerProfile
        fields = ['profile_picture', 'phone_number', 'date_of_birth', 'first_name', 'last_name']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'})
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.user:
            self.fields['email'].initial = self.instance.user.email
            self.fields['first_name'].initial = self.instance.first_name or self.instance.user.first_name
            self.fields['last_name'].initial = self.instance.last_name or self.instance.user.last_name
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")
        
        if password or password_confirm:
            if password != password_confirm:
                self.add_error('password_confirm', "Passwords do not match")
            
            # Validate password strength
            try:
                validate_password(password)
            except ValidationError as e:
                self.add_error('password', e)
        
        return cleaned_data
    
    def save(self, commit=True):
        profile = super().save(commit=False)
        
        # Update user email if provided
        email = self.cleaned_data.get('email')
        if email and profile.user:
            profile.user.email = email
        
        # Update names
        first_name = self.cleaned_data.get('first_name')
        last_name = self.cleaned_data.get('last_name')
        
        if first_name:
            profile.first_name = first_name
            profile.user.first_name = first_name
        
        if last_name:
            profile.last_name = last_name
            profile.user.last_name = last_name
        
        # Update password if provided
        password = self.cleaned_data.get('password')
        if password:
            profile.set_password(password)
            profile.user.set_password(password)
        
        if commit:
            profile.user.save()
            profile.save()
        
        return profile


class CustomerRegistrationForm(forms.ModelForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(max_length=30, required=True)
    last_name = forms.CharField(max_length=30, required=True)
    username = forms.CharField(max_length=150, required=True)
    password = forms.CharField(widget=forms.PasswordInput)
    password_confirm = forms.CharField(widget=forms.PasswordInput, label="Confirm Password")
    
    class Meta:
        model = CustomerProfile
        fields = ['phone_number', 'date_of_birth', 'profile_picture']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'})
        }
    
    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        password_confirm = cleaned_data.get("password_confirm")
        
        if password != password_confirm:
            self.add_error('password_confirm', "Passwords do not match")
        
        # Validate password strength
        try:
            validate_password(password)
        except ValidationError as e:
            self.add_error('password', e)
        
        # Check if email already exists
        email = cleaned_data.get('email')
        if email and User.objects.filter(email=email).exists():
            self.add_error('email', "A user with this email already exists.")
        
        # Check if username already exists
        username = cleaned_data.get('username')
        if username and User.objects.filter(username=username).exists():
            self.add_error('username', "A user with this username already exists.")
        
        return cleaned_data
    
    def save(self, commit=True):
        # Create User first
        email = self.cleaned_data['email']
        first_name = self.cleaned_data['first_name']
        last_name = self.cleaned_data['last_name']
        username = self.cleaned_data['username']
        password = self.cleaned_data['password']
        
        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        
        # Create CustomerProfile
        profile = super().save(commit=False)
        profile.user = user
        profile.first_name = first_name
        profile.last_name = last_name
        profile.set_password(password)  # Store hashed password in profile too
        
        if commit:
            profile.save()
        
        return profile