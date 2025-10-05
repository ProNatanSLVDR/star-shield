from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import TestCase

from auths.models import Entreprise


class EntrepriseModelTests(TestCase):
    def test_str_returns_nom(self):
        entreprise = Entreprise.objects.create(nom="Acme Corp")

        self.assertEqual(str(entreprise), "Acme Corp")


class UserModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.entreprise = Entreprise.objects.create(nom="Acme Corp")
        cls.UserModel = get_user_model()

    def _create_user(self, **overrides):
        defaults = {
            "email": "john.doe@example.com",
            "password": "testpass123",
            "entreprise": self.entreprise,
        }
        defaults.update(overrides)
        return self.UserModel.objects.create_user(**defaults)

    def test_str_returns_full_name_when_available(self):
        user = self._create_user(first_name="John", last_name="Doe")

        self.assertEqual(str(user), "John Doe")

    def test_str_returns_email_when_no_name(self):
        user = self._create_user()

        self.assertEqual(str(user), "john.doe@example.com")

    def test_user_manager_sets_unusable_password_when_missing(self):
        for provided_password, expected_has_password in (
            ("password123", True),
            (None, False),
            (" ", False),
            ("", False),
        ):
            with self.subTest(password=provided_password):
                user = self._create_user(email=f"{provided_password!r}@example.com", password=provided_password)
                self.assertEqual(user.has_usable_password(), expected_has_password)

    def test_user_manager_normalizes_email(self):
        user = self._create_user(email="John.Doe@Example.com")

        self.assertEqual(user.email, "john.doe@example.com")

    def test_create_user_requires_email(self):
        with self.assertRaisesMessage(ValueError, "An email address is required."):
            self.UserModel.objects.create_user(
                email="",
                password="password123",
                entreprise=self.entreprise,
            )

    def test_create_superuser_requires_password(self):
        with self.assertRaisesMessage(ValueError, "Superuser must have a password."):
            self.UserModel.objects.create_superuser(
                email="admin@example.com",
                password=" ",
                entreprise=self.entreprise,
            )

    def test_create_superuser_requires_is_staff_true(self):
        with self.assertRaisesMessage(ValueError, "Superuser must have is_staff=True."):
            self.UserModel.objects.create_superuser(
                email="admin@example.com",
                password="password123",
                entreprise=self.entreprise,
                is_staff=False,
            )

    def test_create_superuser_requires_is_superuser_true(self):
        with self.assertRaisesMessage(ValueError, "Superuser must have is_superuser=True."):
            self.UserModel.objects.create_superuser(
                email="admin@example.com",
                password="password123",
                entreprise=self.entreprise,
                is_superuser=False,
            )


