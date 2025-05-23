# app/forms.py
from django import forms
from django.contrib.auth.models import User
from .models import Expense, Profile

class ExpenseForm(forms.ModelForm):
    class Meta:
        model = Expense
        fields = ['date', 'description', 'category', 'amount']

class SignupForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    role = forms.ChoiceField(choices=Profile.ROLE_CHOICES)
    full_name = forms.CharField(max_length=100, required=True)

    class Meta:
        model = User
        fields = ['username', 'password', 'role', 'full_name']




