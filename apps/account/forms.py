from __future__ import annotations

from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import (
    UserCreationForm as DjangoUserCreationForm,
    UserChangeForm as DjangoUserChangeForm,
)
from django.core.exceptions import ValidationError

from .models import User


class EmailAuthenticationForm(forms.Form):
    email = forms.EmailField(
        label="Email",
        widget=forms.EmailInput(attrs={"autocomplete": "email"}),
        max_length=254,
    )
    password = forms.CharField(widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))

    error_messages = {
        "invalid_login": "Invalid email or password.",
        "inactive": "This account is inactive.",
    }

    def __init__(self, request=None, *args, **kwargs):
        self.request = request
        self.user_cache: User | None = None
        super().__init__(*args, **kwargs)

    def clean(self):
        email = self.cleaned_data.get("email", "").strip().lower()
        password = self.cleaned_data.get("password")

        if not email or not password:
            raise ValidationError(self.error_messages["invalid_login"], code="invalid_login")

        user = authenticate(
            request=self.request,
            username=email,
            password=password,
        )
        if user is None or not isinstance(user, User):
            raise ValidationError(self.error_messages["invalid_login"], code="invalid_login")

        self.confirm_login_allowed(user)
        self.user_cache = user
        return self.cleaned_data

    def confirm_login_allowed(self, user: User) -> None:
        if not getattr(user, "is_active", False):
            raise ValidationError(self.error_messages["inactive"], code="inactive")

    def get_user(self) -> User | None:
        return self.user_cache


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
