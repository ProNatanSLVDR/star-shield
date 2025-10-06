from __future__ import annotations
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.exceptions import ValidationError
from django.db import models


class UserManager(BaseUserManager):
    def _create_user(self, email: str, password: str | None, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")

        normalized_email = self.normalize_email(email).lower()
        user = self.model(email=normalized_email, **extra_fields)

        if password and password.strip():
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_active", True)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        if not password or not password.strip():
            raise ValueError("Superuser must have a password.")

        try:
            admin_entreprise, _ = Entreprise.objects.get_or_create(nom="admin")
        except Exception as exc:
            raise ValueError("Failed to ensure the admin entreprise exists.") from exc

        extra_fields["entreprise"] = admin_entreprise

        return self._create_user(email, password, **extra_fields)


class Entreprise(models.Model):
    nom = models.CharField(max_length=100)

    created_on = models.DateField(auto_now_add=True)
    modified_on = models.DateField(auto_now=True)

    def __str__(self) -> str:
        return self.nom

class User(AbstractBaseUser, PermissionsMixin):
    entreprise = models.ForeignKey(Entreprise, on_delete=models.CASCADE)
    email = models.EmailField(unique=True)

    # Infos Personnelles
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)

    # Misc
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    def __str__(self) -> str:
        if self.first_name or self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        return self.email

