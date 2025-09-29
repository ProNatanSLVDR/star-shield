from __future__ import annotations

from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    UserCreationForm as DjangoUserCreationForm,
    UserChangeForm as DjangoUserChangeForm,
)
from django.core.exceptions import ValidationError

from .models import User


class EmailAuthenticationForm(AuthenticationForm):
    username = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
        max_length=254,
    )

    def confirm_login_allowed(self, user: User) -> None:
        if not user.is_active:
            raise ValidationError("This account is inactive.", code="inactive")


class UserCreationForm(DjangoUserCreationForm):
    email = forms.EmailField(widget=forms.EmailInput(attrs={"autocomplete": "email"}))
    first_name = forms.CharField(required=False, max_length=150)
    last_name = forms.CharField(required=False, max_length=150)

    class Meta(DjangoUserCreationForm.Meta):
        model = User
        fields = ("email", "first_name", "last_name")

    def clean_email(self) -> str:
        email = self.cleaned_data.get("email", "").strip()
        if not email:
            raise ValidationError("Email is required.")

        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("A user with that email already exists.")

        return email

    def save(self, commit: bool = True) -> User:
        user: User = super().save(commit=False)
        user.email = self.cleaned_data["email"].lower()
        if commit:
            user.save()
        return user


class UserChangeForm(DjangoUserChangeForm):
    class Meta(DjangoUserChangeForm.Meta):
        model = User
        fields = (
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_staff",
            "is_superuser",
            "groups",
            "user_permissions",
        )
