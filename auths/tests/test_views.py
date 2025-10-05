from __future__ import annotations

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from auths.models import Entreprise


class LoginViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = Client()
        cls.login_url = reverse("auths:login")
        cls.dashboard_url = reverse("dashboard:accueil")
        cls.entreprise = Entreprise.objects.create(nom="Acme Corp")
        cls.UserModel = get_user_model()

    def test_redirect_authenticated_user(self):
        user = self.UserModel.objects.create_user(
            email="user@example.com",
            password="password123",
            entreprise=self.entreprise,
        )
        self.client.force_login(user)

        response = self.client.get(self.login_url)

        self.assertRedirects(response, self.dashboard_url)

    def test_get_request_returns_ok(self):
        response = self.client.get(self.login_url)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "auths/login.html")

    def test_post_invalid_data_shows_error(self):
        response = self.client.post(self.login_url, data={"email": "user@example.com", "password": "wrong"}, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "auths/login.html")
        messages = list(response.context["messages"])
        self.assertTrue(messages)
        self.assertIn("Email ou mot de passe incorrect.", str(messages[0]))

    def test_post_inactive_user_shows_generic_error(self):
        self.UserModel.objects.create_user(
            email="user@example.com",
            password="password123",
            entreprise=self.entreprise,
            is_active=False,
        )

        response = self.client.post(
            self.login_url,
            data={"email": "user@example.com", "password": "password123"},
            follow=True,
        )

        self.assertEqual(response.status_code, 200)
        messages = list(response.context["messages"])
        self.assertTrue(messages)
        self.assertIn("Email ou mot de passe incorrect.", str(messages[0]))

    def test_post_valid_credentials_logs_in_user(self):
        self.UserModel.objects.create_user(
            email="user@example.com",
            password="password123",
            entreprise=self.entreprise,
        )

        response = self.client.post(
            self.login_url,
            data={"email": "user@example.com", "password": "password123"},
        )

        self.assertRedirects(response, reverse("dashboard:accueil"))


class LogoutViewTests(TestCase):
    def test_logout_redirects_to_login(self):
        response = self.client.get(reverse("auths:logout"))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response.url.startswith(reverse("auths:login")))


