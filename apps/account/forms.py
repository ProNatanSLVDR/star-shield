from __future__ import annotations

from django import forms


class UserLoginForm(forms.Form):
    email = forms.EmailField(max_length=75, widget=forms.EmailInput(attrs={"autocomplete": "email"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))
