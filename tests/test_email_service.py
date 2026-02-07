from django.core import mail
from django.test import TestCase, override_settings

from starshield.email_service import send_email


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="test@starshield.pro",
    BREVO_SENDER_EMAIL="noreply@starshield.pro",
)
class TestSendEmail(TestCase):
    def test_sends_single_recipient(self):
        send_email(
            to="user@example.com",
            subject="Test Subject",
            template_name="emails/basic_mail.html",
            context={"text": "Hello"},
        )

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["user@example.com"])
        self.assertEqual(mail.outbox[0].subject, "Test Subject")

    def test_sends_multiple_recipients(self):
        send_email(
            to=["user1@example.com", "user2@example.com"],
            subject="Multi",
            template_name="emails/basic_mail.html",
        )

        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["user1@example.com", "user2@example.com"])

    def test_raises_for_empty_recipients(self):
        with self.assertRaises(ValueError):
            send_email(
                to=[],
                subject="No Recipients",
                template_name="emails/basic_mail.html",
            )

    def test_fail_silently_does_not_raise_for_empty_recipients(self):
        # Should not raise
        send_email(
            to=[],
            subject="No Recipients",
            template_name="emails/basic_mail.html",
            fail_silently=True,
        )

        self.assertEqual(len(mail.outbox), 0)

    @override_settings(DEFAULT_FROM_EMAIL=None, BREVO_SENDER_EMAIL=None)
    def test_raises_when_no_from_email_configured(self):
        with self.assertRaises(ValueError):
            send_email(
                to="user@example.com",
                subject="Test",
                template_name="emails/basic_mail.html",
            )
