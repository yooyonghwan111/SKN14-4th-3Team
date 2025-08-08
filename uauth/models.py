from django.db import models
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django import forms


class UserDetail(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    birthday = models.DateField(null=True, blank=True)
    profile = models.ImageField(upload_to='profile/', null=True, blank=True) 


class UserForm(UserCreationForm):
    birthday = forms.DateField(label="Birthday", required=False)
    profile = forms.ImageField(label="Profile", required=False)

    class Meta:
        model = User
        fields = ("username", "password1", "password2", "email")