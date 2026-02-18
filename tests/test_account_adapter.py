from unittest.mock import MagicMock, patch

from django.core.mail import EmailMultiAlternatives
from django.test import TestCase, override_settings

from starshield.account_adapter import CustomAccountAdapter


@override_settings(
    ACCOUNT_DEFAULT_HTTP_PROTOCOL="https",
    DEFAULT_FROM_EMAIL="noreply@starshield.fr",
)
class TestCustomAccountAdapter(TestCase):
    def setUp(self):
        self.adapter = CustomAccountAdapter()
        self.user = MagicMock()
        self.user.get_full_name.return_value = "Jean Dupont"
        self.user.email = "jean@example.com"

    def _render(self, template_prefix, context=None):
        base_context = {"user": self.user}
        if context:
            base_context.update(context)

        with patch.object(
            self.adapter.__class__.__bases__[0],
            "render_mail",
            return_value=EmailMultiAlternatives(
                subject="Test Subject",
                body="",
                from_email="noreply@starshield.fr",
                to=["jean@example.com"],
            ),
        ):
            return self.adapter.render_mail(template_prefix, "jean@example.com", base_context)

    def test_email_confirmation_with_code(self):
        msg = self._render("account/email/email_confirmation", {"code": "123456"})

        self.assertIsInstance(msg, EmailMultiAlternatives)
        self.assertEqual(msg.to, ["jean@example.com"])

    def test_email_confirmation_with_activate_url(self):
        msg = self._render("account/email/email_confirmation", {"activate_url": "https://example.com/activate"})

        self.assertIsInstance(msg, EmailMultiAlternatives)

    def test_email_confirmation_without_code_or_url(self):
        msg = self._render("account/email/email_confirmation")

        self.assertIsInstance(msg, EmailMultiAlternatives)

    def test_password_reset_with_url(self):
        msg = self._render("account/email/password_reset", {"password_reset_url": "https://example.com/reset"})

        self.assertIsInstance(msg, EmailMultiAlternatives)

    def test_password_reset_without_url(self):
        msg = self._render("account/email/password_reset")

        self.assertIsInstance(msg, EmailMultiAlternatives)

    def test_email_change_with_url(self):
        msg = self._render(
            "account/email/email_change",
            {"new_email": "new@example.com", "activate_url": "https://example.com/confirm"},
        )

        self.assertIsInstance(msg, EmailMultiAlternatives)

    def test_email_change_without_url(self):
        msg = self._render("account/email/email_change", {"new_email": "new@example.com"})

        self.assertIsInstance(msg, EmailMultiAlternatives)

    def test_password_set_with_url(self):
        msg = self._render("account/email/password_set", {"password_set_url": "https://example.com/set"})

        self.assertIsInstance(msg, EmailMultiAlternatives)

    def test_password_set_without_url(self):
        msg = self._render("account/email/password_set")

        self.assertIsInstance(msg, EmailMultiAlternatives)

    def test_generic_fallback_with_message(self):
        msg = self._render("account/email/unknown_template", {"message": "Custom message here"})

        self.assertIsInstance(msg, EmailMultiAlternatives)

    def test_generic_fallback_without_message(self):
        msg = self._render("account/email/unknown_template")

        self.assertIsInstance(msg, EmailMultiAlternatives)

    def test_user_display_email_only(self):
        self.user.get_full_name.return_value = ""
        msg = self._render("account/email/email_confirmation", {"code": "ABC"})

        self.assertIsInstance(msg, EmailMultiAlternatives)

    def test_user_display_string_user(self):
        msg = self._render("account/email/email_confirmation", {"user": "string_user", "code": "ABC"})

        self.assertIsInstance(msg, EmailMultiAlternatives)

    def test_user_display_none(self):
        msg = self._render("account/email/email_confirmation", {"user": None, "code": "ABC"})

        self.assertIsInstance(msg, EmailMultiAlternatives)

    def test_exception_falls_back_to_default(self):
        with (
            patch.object(
                self.adapter.__class__.__bases__[0],
                "render_mail",
                return_value=EmailMultiAlternatives(
                    subject="Fallback",
                    body="",
                    from_email="noreply@starshield.fr",
                    to=["jean@example.com"],
                ),
            ),
            patch("starshield.account_adapter.render_to_string", side_effect=Exception("Template error")),
        ):
            msg = self.adapter.render_mail(
                "account/email/email_confirmation",
                "jean@example.com",
                {"user": self.user, "code": "123"},
            )

        self.assertIsInstance(msg, EmailMultiAlternatives)
        self.assertEqual(msg.subject, "Fallback")
