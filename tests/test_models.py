from decimal import Decimal

from django.test import TestCase

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
