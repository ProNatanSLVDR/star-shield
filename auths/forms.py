from __future__ import annotations

from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.core.exceptions import ValidationError


class UserLoginForm(forms.Form):
    email = forms.EmailField(max_length=75, widget=forms.EmailInput(attrs={"autocomplete": "email"}))
    password = forms.CharField(widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))


class UserRegistrationForm(forms.Form):
    first_name = forms.CharField(
        max_length=75,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "given-name",
                "class": "input input-bordered",
                "placeholder": "Jean",
            }
        ),
        label="Prénom",
    )
    last_name = forms.CharField(
        max_length=75,
        widget=forms.TextInput(
            attrs={
                "autocomplete": "family-name",
                "class": "input input-bordered",
                "placeholder": "Dupont",
            }
        ),
        label="Nom",
    )
    email = forms.EmailField(
        max_length=75,
        widget=forms.EmailInput(
            attrs={
                "autocomplete": "email",
                "class": "input input-bordered",
                "placeholder": "moi@exemple.com",
            }
        ),
        label="Email",
    )
    password1 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "class": "input input-bordered",
                "placeholder": "••••••••",
            }
        ),
        label="Mot de passe",
    )
    password2 = forms.CharField(
        widget=forms.PasswordInput(
            attrs={
                "autocomplete": "new-password",
                "class": "input input-bordered",
                "placeholder": "••••••••",
            }
        ),
        label="Confirmez le mot de passe",
    )

    error_messages = {
        "password_mismatch": "Les mots de passe ne correspondent pas.",
        "email_exists": "Cet email est déjà utilisé.",
    }

    def clean_email(self) -> str:
        email = self.cleaned_data["email"].lower()
        user_model = get_user_model()
        if user_model.objects.filter(email=email).exists():
            raise ValidationError(self.error_messages["email_exists"], code="email_exists")
        return email

    def clean(self) -> dict[str, object]:
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")

        if password1 and password2 and password1 != password2:
            raise ValidationError({"password2": self.error_messages["password_mismatch"]})

        if password1:
            password_validation.validate_password(password1)

        return cleaned_data

    def save(self):
        user_model = get_user_model()

        user = user_model.objects.create_user(
            email=self.cleaned_data["email"],
            password=self.cleaned_data["password1"],
            first_name=self.cleaned_data["first_name"].strip(),
            last_name=self.cleaned_data["last_name"].strip(),
        )
        return user
