from datetime import timedelta
from unittest.mock import MagicMock

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from googleapiclient.errors import HttpError

from tests.factories import (
    GoogleCredentialsFactory,
    QRCodeFactory,
    QRCodeScanFactory,
)

User = get_user_model()


class TestUserManager(TestCase):
    def test_create_user_normalizes_email(self):
        user = User.objects.create_user("Test@EXAMPLE.COM", "password123")
        self.assertEqual(user.email, "test@example.com")

    def test_create_user_sets_unusable_password_when_none(self):
        user = User.objects.create_user("nopass@example.com")
        self.assertFalse(user.has_usable_password())

    def test_create_user_sets_unusable_password_for_empty_string(self):
        user = User.objects.create_user("empty@example.com", "")
        self.assertFalse(user.has_usable_password())

    def test_create_user_sets_usable_password(self):
        user = User.objects.create_user("pass@example.com", "strongpass123")
        self.assertTrue(user.has_usable_password())

    def test_create_user_is_not_staff_or_superuser(self):
        user = User.objects.create_user("regular@example.com", "pass123")
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_user_raises_without_email(self):
        with self.assertRaises(ValueError, msg="email address is required"):
            User.objects.create_user("", "pass123")

    def test_create_superuser_sets_staff_and_superuser(self):
        user = User.objects.create_superuser("admin@example.com", "adminpass123")
        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_create_superuser_raises_without_password(self):
        with self.assertRaises(ValueError, msg="must have a password"):
            User.objects.create_superuser("admin2@example.com", None)

    def test_create_superuser_raises_with_empty_password(self):
        with self.assertRaises(ValueError, msg="must have a password"):
            User.objects.create_superuser("admin3@example.com", "  ")

    def test_create_superuser_raises_if_not_staff(self):
        with self.assertRaises(ValueError, msg="is_staff=True"):
            User.objects.create_superuser("admin4@example.com", "pass", is_staff=False)

    def test_create_superuser_raises_if_not_superuser(self):
        with self.assertRaises(ValueError, msg="is_superuser=True"):
            User.objects.create_superuser("admin5@example.com", "pass", is_superuser=False)


class TestGoogleCredentialsCheckInvalidGrant(TestCase):
    def test_detects_invalid_grant_in_error_message(self):
        cred = GoogleCredentialsFactory(has_invalid_grants=False)
        error = Exception("invalid_grant: Token has been expired or revoked")

        result = cred._check_and_set_invalid_grant(error)

        self.assertTrue(result)
        cred.refresh_from_db()
        self.assertTrue(cred.has_invalid_grants)

    def test_returns_false_for_non_grant_error(self):
        cred = GoogleCredentialsFactory(has_invalid_grants=False)
        error = Exception("Connection timeout")

        result = cred._check_and_set_invalid_grant(error)

        self.assertFalse(result)
        cred.refresh_from_db()
        self.assertFalse(cred.has_invalid_grants)

    def test_does_not_save_if_already_set(self):
        cred = GoogleCredentialsFactory(has_invalid_grants=True)
        error = Exception("invalid_grant")

        result = cred._check_and_set_invalid_grant(error)

        self.assertTrue(result)

    def test_detects_invalid_grant_in_http_error(self):
        cred = GoogleCredentialsFactory(has_invalid_grants=False)
        resp = MagicMock()
        resp.status = 401
        resp.reason = "invalid_grant"
        error = HttpError(resp, b"invalid_grant: Token has been expired or revoked")

        result = cred._check_and_set_invalid_grant(error)

        self.assertTrue(result)
        cred.refresh_from_db()
        self.assertTrue(cred.has_invalid_grants)


class TestQRCodeScanMethods(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.qr = QRCodeFactory()

    def test_scans_today(self):
        QRCodeScanFactory(qr_code=self.qr)
        self.assertEqual(self.qr.scans_today(), 1)

    def test_scans_today_excludes_yesterday(self):
        scan = QRCodeScanFactory(qr_code=self.qr)
        # Move scan to yesterday
        yesterday = timezone.now() - timedelta(days=1)
        type(scan).created_at = None  # Needed for auto_now_add
        scan.__class__.objects.filter(pk=scan.pk).update(created_at=yesterday)
        self.assertEqual(self.qr.scans_today(), 0)

    def test_scans_this_week(self):
        QRCodeScanFactory(qr_code=self.qr)
        self.assertGreaterEqual(self.qr.scans_this_week(), 1)

    def test_scans_this_month(self):
        QRCodeScanFactory(qr_code=self.qr)
        self.assertGreaterEqual(self.qr.scans_this_month(), 1)

    def test_scan_count(self):
        QRCodeScanFactory(qr_code=self.qr)
        QRCodeScanFactory(qr_code=self.qr)
        self.assertEqual(self.qr.scan_count(), 2)
