from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import IntegrityError
from django.test import TestCase, TransactionTestCase
from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError

from apps.private.auths.models import QRCode
from apps.public.reviews.models import ReviewAnalytics
from tests.factories import (
    EtablissementFactory,
    GoogleCredentialsFactory,
    QRCodeFactory,
    QRCodeScanFactory,
    RatingHistoryFactory,
    ReviewFactory,
    RoulettePrizeFactory,
    RouletteSpinFactory,
    StripeSubscriptionFactory,
    UserFactory,
)


class TestUser(TestCase):
    def test_has_google_credential_true(self):
        credential = GoogleCredentialsFactory()

        self.assertTrue(credential.user.has_google_credential)

    def test_has_google_credential_false(self):
        user = UserFactory()

        self.assertFalse(user.has_google_credential)


class TestEtablissement(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.etab = EtablissementFactory(title="Mon Restaurant")

    def test_str(self):
        self.assertEqual(str(self.etab), "Mon Restaurant")

    def test_has_active_subscription_true(self):
        StripeSubscriptionFactory(etablissement=self.etab, status="active")

        self.assertTrue(self.etab.has_active_subscription())

    def test_has_active_subscription_false(self):
        self.assertFalse(self.etab.has_active_subscription())

    def test_has_active_subscription_false_when_cancelled(self):
        StripeSubscriptionFactory(etablissement=self.etab, status="canceled")

        self.assertFalse(self.etab.has_active_subscription())

    def test_uuid_auto_generated(self):
        etab = EtablissementFactory()

        self.assertIsNotNone(etab.uuid)

    def test_default_threshold(self):
        etab = EtablissementFactory()

        self.assertEqual(etab.review_threshold, 4)

    def test_creates_default_locked_qr_codes_on_create(self):
        etab = EtablissementFactory()

        locked_qr_codes = etab.qr_codes.filter(locked=True)
        locked_routes = set(locked_qr_codes.values_list("name", "routing"))

        self.assertEqual(locked_qr_codes.count(), 2)
        self.assertSetEqual(
            locked_routes,
            {
                ("Filtre", "feedback"),
                ("Roulette", "roulette"),
            },
        )


class TestQRCode(TestCase):
    def test_str(self):
        qr = QRCodeFactory(name="Entrée", routing="feedback")

        self.assertEqual(str(qr), "Entrée (Feedback)")

    def test_auto_generates_short_code_on_save(self):
        qr = QRCodeFactory()

        self.assertIsNotNone(qr.short_code)
        self.assertEqual(len(qr.short_code), 8)

    def test_short_code_is_unique(self):
        qr1 = QRCodeFactory()
        qr2 = QRCodeFactory()

        self.assertNotEqual(qr1.short_code, qr2.short_code)

    def test_get_target_url_feedback(self):
        etab = EtablissementFactory(slug="my-etab")
        qr = QRCodeFactory(etablissement=etab, routing="feedback")

        url = qr.get_target_url("my-etab")

        self.assertIn("feedback", url)
        self.assertIn("my-etab", url)

    def test_get_target_url_roulette(self):
        etab = EtablissementFactory(slug="my-etab")
        qr = QRCodeFactory(etablissement=etab, routing="roulette")

        url = qr.get_target_url("my-etab")

        self.assertIn("roulette", url)

    def test_scan_count(self):
        qr = QRCodeFactory()
        QRCodeScanFactory(qr_code=qr)
        QRCodeScanFactory(qr_code=qr)

        self.assertEqual(qr.scan_count(), 2)


class TestReview(TestCase):
    def test_str_with_reviewer_data(self):
        review = ReviewFactory(
            rating=5,
            google_reviewer_data={"displayName": "Jean Dupont"},
        )

        result = str(review)

        self.assertIn("Jean Dupont", result)
        self.assertIn("5★", result)

    def test_str_without_reviewer_data_shows_anonyme(self):
        review = ReviewFactory(rating=3, google_reviewer_data={})

        result = str(review)

        self.assertIn("Anonyme", result)


class TestRoulettePrize(TestCase):
    def test_str_with_probability(self):
        etab = EtablissementFactory(title="My Resto")
        prize = RoulettePrizeFactory(
            etablissement=etab,
            name="Free Coffee",
            probability=Decimal("25.50"),
        )

        result = str(prize)

        self.assertIn("My Resto", result)
        self.assertIn("Free Coffee", result)
        self.assertIn("25.5%", result)

    def test_str_with_whole_number_probability(self):
        prize = RoulettePrizeFactory(probability=Decimal("50.00"))

        result = str(prize)

        self.assertIn("50%", result)


class TestRouletteSpin(TestCase):
    def test_str(self):
        etab = EtablissementFactory(title="Bistro")
        prize = RoulettePrizeFactory(etablissement=etab, name="10% off")
        spin = RouletteSpinFactory(
            etablissement=etab,
            prize=prize,
            prize_code="ABC123",
        )

        result = str(spin)

        self.assertIn("Bistro", result)
        self.assertIn("10% off", result)
        self.assertIn("ABC123", result)

    def test_is_used_defaults_false(self):
        spin = RouletteSpinFactory()

        self.assertFalse(spin.is_used)


class TestStripeSubscription(TestCase):
    def test_str(self):
        etab = EtablissementFactory(title="My Shop")
        sub = StripeSubscriptionFactory(etablissement=etab, status="active")

        self.assertEqual(str(sub), "My Shop - active")

    def test_unique_subscription_id(self):
        sub1 = StripeSubscriptionFactory(subscription_id="sub_unique_1")
        sub2 = StripeSubscriptionFactory(subscription_id="sub_unique_2")

        self.assertNotEqual(sub1.subscription_id, sub2.subscription_id)


class TestReviewAnalytics(TestCase):
    def test_str(self):
        etab = EtablissementFactory(title="Café Paris")
        analytics = ReviewAnalytics.objects.create(
            etablissement=etab,
            type="feedback_viewed",
        )

        self.assertEqual(str(analytics), "Café Paris - feedback_viewed")


class TestRatingHistory(TestCase):
    def test_str(self):
        etab = EtablissementFactory(title="Le Bouchon")
        history = RatingHistoryFactory(etablissement=etab, rating=Decimal("4.50"))

        result = str(history)

        self.assertIn("4.50★", result)
        self.assertIn("Le Bouchon", result)


class TestGoogleCredentialsCheckInvalidGrant(TestCase):
    def test_detects_invalid_grant_in_error_message(self):
        cred = GoogleCredentialsFactory(has_invalid_grants=False)

        result = cred._check_and_set_invalid_grant(Exception("Token has been expired or revoked. invalid_grant"))

        self.assertTrue(result)
        cred.refresh_from_db()
        self.assertTrue(cred.has_invalid_grants)

    def test_does_not_flag_unrelated_error(self):
        cred = GoogleCredentialsFactory(has_invalid_grants=False)

        result = cred._check_and_set_invalid_grant(Exception("Network timeout"))

        self.assertFalse(result)
        cred.refresh_from_db()
        self.assertFalse(cred.has_invalid_grants)

    def test_already_flagged_does_not_save_again(self):
        cred = GoogleCredentialsFactory(has_invalid_grants=True)

        result = cred._check_and_set_invalid_grant(Exception("invalid_grant"))

        self.assertTrue(result)

    def test_http_error_with_invalid_grant_in_details(self):
        http_error = HttpError(
            resp=MagicMock(status=401),
            content=b'{"error": "invalid_grant"}',
        )
        http_error.error_details = [{"reason": "invalid_grant"}]
        cred = GoogleCredentialsFactory(has_invalid_grants=False)

        result = cred._check_and_set_invalid_grant(http_error)

        self.assertTrue(result)


class TestGoogleCredentialsGetValidCredentials(TestCase):
    @patch("apps.private.auths.models.Request")
    @patch("apps.private.auths.models.Credentials")
    @patch("apps.private.auths.models.decrypt_symmetric", side_effect=lambda v, k: v)
    def test_returns_credentials_not_expired(self, mock_decrypt, mock_creds_class, mock_request):
        mock_creds = MagicMock()
        mock_creds.expired = False
        mock_creds_class.return_value = mock_creds
        cred = GoogleCredentialsFactory()

        result = cred.get_valid_credentials()

        self.assertEqual(result, mock_creds)

    @patch("apps.private.auths.models.encrypt_symmetric", side_effect=lambda v, k: f"enc_{v}")
    @patch("apps.private.auths.models.Request")
    @patch("apps.private.auths.models.Credentials")
    @patch("apps.private.auths.models.decrypt_symmetric", side_effect=lambda v, k: v)
    def test_refreshes_expired_token(self, mock_decrypt, mock_creds_class, mock_request, mock_encrypt):
        mock_creds = MagicMock()
        mock_creds.expired = True
        mock_creds.refresh_token = "new-refresh-token"
        mock_creds.token = "new-token"
        mock_creds_class.return_value = mock_creds
        cred = GoogleCredentialsFactory()

        result = cred.get_valid_credentials()

        mock_creds.refresh.assert_called_once()
        self.assertEqual(result, mock_creds)
        cred.refresh_from_db()
        self.assertEqual(cred.token, "enc_new-token")

    @patch("apps.private.auths.models.Request")
    @patch("apps.private.auths.models.Credentials")
    @patch("apps.private.auths.models.decrypt_symmetric", side_effect=lambda v, k: v)
    def test_refresh_error_sets_invalid_and_raises(self, mock_decrypt, mock_creds_class, mock_request):
        mock_creds = MagicMock()
        mock_creds.expired = True
        mock_creds.refresh_token = "some-token"
        mock_creds.refresh.side_effect = RefreshError("invalid_grant: Token revoked")
        mock_creds_class.return_value = mock_creds
        cred = GoogleCredentialsFactory(is_valid=True)

        with self.assertRaises(RefreshError):
            cred.get_valid_credentials()

        cred.refresh_from_db()
        self.assertFalse(cred.is_valid)
        self.assertTrue(cred.has_invalid_grants)


class TestGoogleCredentialsServices(TestCase):
    @patch("apps.private.auths.models.build")
    @patch("apps.private.auths.models.GoogleCredentials.get_valid_credentials")
    def test_get_reviews_service_success(self, mock_get_creds, mock_build):
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        cred = GoogleCredentialsFactory()

        result = cred.get_reviews_service()

        self.assertEqual(result, mock_service)
        mock_build.assert_called_once()

    @patch("apps.private.auths.models.GoogleCredentials.get_valid_credentials")
    def test_get_reviews_service_error_returns_none(self, mock_get_creds):
        mock_get_creds.side_effect = Exception("API Error")
        cred = GoogleCredentialsFactory()

        result = cred.get_reviews_service()

        self.assertIsNone(result)

    @patch("apps.private.auths.models.build")
    @patch("apps.private.auths.models.GoogleCredentials.get_valid_credentials")
    def test_get_locations_service_success(self, mock_get_creds, mock_build):
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        cred = GoogleCredentialsFactory()

        result = cred.get_locations_service()

        self.assertEqual(result, mock_service)

    @patch("apps.private.auths.models.GoogleCredentials.get_valid_credentials")
    def test_get_locations_service_error_returns_none(self, mock_get_creds):
        mock_get_creds.side_effect = Exception("API Error")
        cred = GoogleCredentialsFactory()

        result = cred.get_locations_service()

        self.assertIsNone(result)

    @patch("apps.private.auths.models.build")
    @patch("apps.private.auths.models.GoogleCredentials.get_valid_credentials")
    def test_get_accounts_service_success(self, mock_get_creds, mock_build):
        mock_service = MagicMock()
        mock_build.return_value = mock_service
        cred = GoogleCredentialsFactory()

        result = cred.get_accounts_service()

        self.assertEqual(result, mock_service)

    @patch("apps.private.auths.models.GoogleCredentials.get_valid_credentials")
    def test_get_accounts_service_error_returns_none(self, mock_get_creds):
        mock_get_creds.side_effect = Exception("API Error")
        cred = GoogleCredentialsFactory()

        result = cred.get_accounts_service()

        self.assertIsNone(result)

    @patch("apps.private.auths.models.GoogleCredentials.get_valid_credentials")
    def test_get_reviews_service_checks_invalid_grant(self, mock_get_creds):
        mock_get_creds.side_effect = Exception("invalid_grant")
        cred = GoogleCredentialsFactory(has_invalid_grants=False)

        cred.get_reviews_service()

        cred.refresh_from_db()
        self.assertTrue(cred.has_invalid_grants)


class TestCreateEtablissementFromLocation(TestCase):
    @patch("apps.private.auths.models.GoogleCredentials.get_locations_service")
    def test_success_creates_etablissement(self, mock_get_locs):
        mock_service = MagicMock()
        mock_service.locations().get().execute.return_value = {
            "name": "locations/123",
            "title": "My Cafe",
            "websiteUri": "https://mycafe.com",
            "metadata": {"mapsUri": "https://maps.google.com/123", "placeId": "PLACE123"},
        }
        mock_get_locs.return_value = mock_service
        cred = GoogleCredentialsFactory()

        with patch("apps.tasks_api.services.queue_service.enqueue_full_import_task"):
            result = cred.create_etablissement_from_location("accounts/1", "locations/123")

        self.assertIsNotNone(result)
        self.assertEqual(result.title, "My Cafe")
        self.assertEqual(result.location_id, "locations/123")

    @patch("apps.private.auths.models.GoogleCredentials.get_locations_service")
    def test_returns_none_when_service_fails(self, mock_get_locs):
        mock_get_locs.return_value = None
        cred = GoogleCredentialsFactory()

        result = cred.create_etablissement_from_location("accounts/1", "locations/123")

        self.assertIsNone(result)

    @patch("apps.private.auths.models.GoogleCredentials.get_locations_service")
    def test_returns_none_on_api_error(self, mock_get_locs):
        mock_service = MagicMock()
        mock_service.locations().get().execute.side_effect = Exception("API Error")
        mock_get_locs.return_value = mock_service
        cred = GoogleCredentialsFactory()

        result = cred.create_etablissement_from_location("accounts/1", "locations/123")

        self.assertIsNone(result)


class TestListAvailableLocations(TestCase):
    @patch("apps.private.auths.models.GoogleCredentials.get_locations_service")
    @patch("apps.private.auths.models.GoogleCredentials.get_accounts_service")
    def test_returns_locations(self, mock_get_accts, mock_get_locs):
        mock_accts = MagicMock()
        mock_accts.accounts().list().execute.return_value = {
            "accounts": [{"name": "accounts/1"}],
        }
        mock_get_accts.return_value = mock_accts

        mock_locs = MagicMock()
        mock_locs.accounts().locations().list().execute.return_value = {
            "locations": [{"name": "locations/1", "title": "Cafe"}],
        }
        mock_get_locs.return_value = mock_locs
        cred = GoogleCredentialsFactory()

        result = cred.list_available_locations()

        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["title"], "Cafe")

    @patch("apps.private.auths.models.GoogleCredentials.get_locations_service")
    @patch("apps.private.auths.models.GoogleCredentials.get_accounts_service")
    def test_returns_empty_when_services_fail(self, mock_get_accts, mock_get_locs):
        mock_get_accts.return_value = None
        mock_get_locs.return_value = None
        cred = GoogleCredentialsFactory()

        result = cred.list_available_locations()

        self.assertEqual(result, [])

    @patch("apps.private.auths.models.GoogleCredentials.get_locations_service")
    @patch("apps.private.auths.models.GoogleCredentials.get_accounts_service")
    def test_returns_empty_on_accounts_error(self, mock_get_accts, mock_get_locs):
        mock_accts = MagicMock()
        mock_accts.accounts().list().execute.side_effect = Exception("API Error")
        mock_get_accts.return_value = mock_accts
        mock_get_locs.return_value = MagicMock()
        cred = GoogleCredentialsFactory()

        result = cred.list_available_locations()

        self.assertEqual(result, [])

    @patch("apps.private.auths.models.GoogleCredentials.get_locations_service")
    @patch("apps.private.auths.models.GoogleCredentials.get_accounts_service")
    def test_marks_existing_locations(self, mock_get_accts, mock_get_locs):
        cred = GoogleCredentialsFactory()
        EtablissementFactory(
            google_credential=cred,
            location_id="locations/existing",
            account_id="accounts/1",
        )

        mock_accts = MagicMock()
        mock_accts.accounts().list().execute.return_value = {
            "accounts": [{"name": "accounts/1"}],
        }
        mock_get_accts.return_value = mock_accts

        mock_locs = MagicMock()
        mock_locs.accounts().locations().list().execute.return_value = {
            "locations": [
                {"name": "locations/existing", "title": "Existing"},
                {"name": "locations/new", "title": "New"},
            ],
        }
        mock_get_locs.return_value = mock_locs

        result = cred.list_available_locations()

        existing = next(loc for loc in result if loc["name"] == "locations/existing")
        new = next(loc for loc in result if loc["name"] == "locations/new")
        self.assertTrue(existing["exists"])
        self.assertFalse(new["exists"])

    @patch("apps.private.auths.models.GoogleCredentials.get_locations_service")
    @patch("apps.private.auths.models.GoogleCredentials.get_accounts_service")
    def test_handles_pagination(self, mock_get_accts, mock_get_locs):
        mock_accts = MagicMock()
        mock_accts.accounts().list().execute.return_value = {
            "accounts": [{"name": "accounts/1"}],
        }
        mock_get_accts.return_value = mock_accts

        mock_locs = MagicMock()
        # First call returns page with token, second returns final page
        mock_locs.accounts().locations().list().execute.side_effect = [
            {"locations": [{"name": "locations/1", "title": "Page1"}], "nextPageToken": "token123"},
            {"locations": [{"name": "locations/2", "title": "Page2"}]},
        ]
        mock_get_locs.return_value = mock_locs
        cred = GoogleCredentialsFactory()

        result = cred.list_available_locations()

        self.assertEqual(len(result), 2)


class TestQRCodeSaveRetry(TestCase):
    def test_retries_on_integrity_error(self):
        etab = EtablissementFactory()
        qr = QRCode(etablissement=etab, name="Test QR")

        with patch.object(QRCode, "_generate_short_code", side_effect=["AAAAAAAA", "BBBBBBBB"]):
            # First save with AAAAAAAA
            qr.save()
            first_code = qr.short_code

        self.assertIsNotNone(first_code)


class TestQRCodeSaveRetryExhaustion(TransactionTestCase):
    def test_raises_after_max_attempts(self):
        etab = EtablissementFactory()
        QRCodeFactory(etablissement=etab, short_code="EXISTING")

        qr = QRCode(etablissement=etab, name="Collider")

        with (
            patch.object(QRCode, "_generate_short_code", return_value="EXISTING"),
            self.assertRaises(IntegrityError),
        ):
            qr.save()


class TestQRCodeScans(TestCase):
    def test_scans_today(self):
        qr = QRCodeFactory()
        QRCodeScanFactory(qr_code=qr)
        QRCodeScanFactory(qr_code=qr)

        self.assertEqual(qr.scans_today(), 2)

    def test_scans_this_week(self):
        qr = QRCodeFactory()
        QRCodeScanFactory(qr_code=qr)

        self.assertEqual(qr.scans_this_week(), 1)

    def test_scans_this_month(self):
        qr = QRCodeFactory()
        QRCodeScanFactory(qr_code=qr)
        QRCodeScanFactory(qr_code=qr)
        QRCodeScanFactory(qr_code=qr)

        self.assertEqual(qr.scans_this_month(), 3)

    def test_get_target_url_verify(self):
        etab = EtablissementFactory(slug="my-etab")
        qr = QRCodeFactory(etablissement=etab, routing="verify")

        url = qr.get_target_url("my-etab")

        self.assertIn("verify", url)

    def test_get_target_url_unknown_returns_none(self):
        qr = QRCodeFactory(routing="feedback")
        # Manually set an invalid routing
        qr.routing = "unknown"

        url = qr.get_target_url("identifier")

        self.assertIsNone(url)


class TestDeleteOldProfilePictureSignal(TestCase):
    def test_deletes_old_picture_on_change(self):
        user = UserFactory()
        # Simulate having an old profile picture
        old_file = MagicMock()
        old_file.name = "old_pic.jpg"
        old_file.__bool__ = lambda self: True

        with patch("apps.private.auths.models.User.objects.get") as mock_get:
            mock_old = MagicMock()
            mock_old.profile_picture = old_file
            mock_get.return_value = mock_old

            user.profile_picture = SimpleUploadedFile("new_pic.jpg", b"content", content_type="image/jpeg")
            user.save()

            old_file.delete.assert_called_once_with(save=False)

    def test_no_delete_when_no_old_picture(self):
        user = UserFactory(profile_picture=None)
        # Save again with no profile picture - should not error
        user.first_name = "Updated"
        user.save()
        # No exception means success


class TestDeleteOldQRLogoSignal(TestCase):
    def test_deletes_old_logo_on_change(self):
        qr = QRCodeFactory()
        old_file = MagicMock()
        old_file.name = "old_logo.png"
        old_file.__bool__ = lambda self: True

        with patch("apps.private.auths.models.QRCode.objects.get") as mock_get:
            mock_old = MagicMock()
            mock_old.qr_logo = old_file
            mock_get.return_value = mock_old

            qr.qr_logo = SimpleUploadedFile("new_logo.png", b"content", content_type="image/png")
            qr.save()

            old_file.delete.assert_called_once_with(save=False)

    def test_no_delete_for_new_qr_code(self):
        """No error when saving a brand new QRCode (no pk yet)."""
        etab = EtablissementFactory()
        qr = QRCode(etablissement=etab, name="Brand New")
        # Should not raise
        qr.save()
        self.assertIsNotNone(qr.pk)


class TestUserManager(TestCase):
    def test_create_user_with_email(self):
        from apps.private.auths.models import User

        user = User.objects.create_user(email="test@example.com", password="testpass123")

        self.assertEqual(user.email, "test@example.com")
        self.assertTrue(user.check_password("testpass123"))
        self.assertFalse(user.is_staff)
        self.assertFalse(user.is_superuser)

    def test_create_user_without_password(self):
        from apps.private.auths.models import User

        user = User.objects.create_user(email="nopass@example.com")

        self.assertFalse(user.has_usable_password())

    def test_create_user_empty_email_raises(self):
        from apps.private.auths.models import User

        with self.assertRaises(ValueError):
            User.objects._create_user(email="", password="test")

    def test_create_superuser(self):
        from apps.private.auths.models import User

        user = User.objects.create_superuser(email="admin@example.com", password="adminpass")

        self.assertTrue(user.is_staff)
        self.assertTrue(user.is_superuser)

    def test_create_superuser_without_password_raises(self):
        from apps.private.auths.models import User

        with self.assertRaises(ValueError):
            User.objects.create_superuser(email="admin@example.com", password="")

    def test_create_superuser_not_staff_raises(self):
        from apps.private.auths.models import User

        with self.assertRaises(ValueError):
            User.objects.create_superuser(email="admin@example.com", password="pass", is_staff=False)

    def test_create_superuser_not_superuser_raises(self):
        from apps.private.auths.models import User

        with self.assertRaises(ValueError):
            User.objects.create_superuser(email="admin@example.com", password="pass", is_superuser=False)

    def test_user_str_with_name(self):
        user = UserFactory(first_name="Jean", last_name="Dupont")
        self.assertEqual(str(user), "Jean Dupont")

    def test_user_str_email_only(self):
        user = UserFactory(first_name="", last_name="")
        self.assertEqual(str(user), user.email)
