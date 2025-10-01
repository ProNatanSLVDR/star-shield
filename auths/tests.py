from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from .models import User


class UserModelTests(TestCase):
    def test_create_user_with_email_forces_lowercase(self):
        user = User.objects.create_user(email="User@Example.com", password="testpass123")

        self.assertEqual(user.email, "user@example.com")
        self.assertTrue(user.check_password("testpass123"))

    def test_create_user_without_password_raises_error(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="user@example.com", password=None)

    def test_create_user_without_email_raises_error(self):
        with self.assertRaises(ValueError):
            User.objects.create_user(email="", password="pass1234")

    def test_email_unique_case_insensitive(self):
        User.objects.create_user(email="duplicate@example.com", password="pass1234")
        with self.assertRaises(IntegrityError):
            User.objects.create_user(email="Duplicate@example.com", password="pass1234")


class AuthenticationViewsTests(TestCase):
    def test_login_requires_valid_credentials(self):
        User.objects.create_user(email="user@example.com", password="testpass123")

        response = self.client.post(
            reverse("auths:login"),
            {"email": "user@example.com", "password": "testpass123"},
            follow=True,
        )

        self.assertRedirects(response, reverse("dashboard:accueil"))

    def test_login_redirects_to_next_when_provided(self):
        User.objects.create_user(email="user@example.com", password="testpass123")

        response = self.client.post(
            reverse("auths:login") + "?next=/protected/",
            {"email": "user@example.com", "password": "testpass123"},
        )

        self.assertRedirects(response, "/protected/", fetch_redirect_response=False)

    def test_login_redirects_to_next_when_provided(self):
        User.objects.create_user(email="user@example.com", password="testpass123")

        response = self.client.post(
            reverse("auths:login") + "?next=/protected/",
            {"email": "user@example.com", "password": "testpass123"},
        )

        self.assertRedirects(response, "/protected/", fetch_redirect_response=False)

    def test_signup_creates_user_and_logs_in(self):
        response = self.client.post(
            reverse("auths:register"),
            {
                "email": "newuser@example.com",
                "first_name": "New",
                "last_name": "User",
                "password1": "ComplexPass123",
                "password2": "ComplexPass123",
            },
            follow=True,
        )

        self.assertRedirects(response, reverse("dashboard:accueil"))
        self.assertTrue(User.objects.filter(email="newuser@example.com").exists())

    def test_logout_requires_post(self):
        user = User.objects.create_user(email="user@example.com", password="testpass123")
        self.client.login(username="user@example.com", password="testpass123")

        response = self.client.get(reverse("auths:logout"))

        self.assertEqual(response.status_code, 405)

    def test_logout_redirects_when_post(self):
        user = User.objects.create_user(email="user@example.com", password="testpass123")
        self.client.login(username="user@example.com", password="testpass123")

        response = self.client.post(reverse("auths:logout"))

        self.assertRedirects(response, reverse("auths:login"))
