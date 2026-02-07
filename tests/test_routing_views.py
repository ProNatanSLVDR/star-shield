from django.test import Client, TestCase
from django.urls import reverse

from apps.private.auths.models import QRCodeScan
from tests.factories import EtablissementFactory, QRCodeFactory


class TestQRCodeRedirectView(TestCase):
    def setUp(self):
        self.client = Client()
        self.etab = EtablissementFactory(active=True)

    def test_redirects_to_feedback(self):
        qr = QRCodeFactory(etablissement=self.etab, routing="feedback")

        response = self.client.get(reverse("routing:qr_code_redirect", args=[self.etab.slug, qr.short_code]))

        self.assertEqual(response.status_code, 302)
        self.assertIn("feedback", response.url)

    def test_redirects_to_roulette(self):
        qr = QRCodeFactory(etablissement=self.etab, routing="roulette")

        response = self.client.get(reverse("routing:qr_code_redirect", args=[self.etab.slug, qr.short_code]))

        self.assertEqual(response.status_code, 302)
        self.assertIn("roulette", response.url)

    def test_creates_scan_record(self):
        qr = QRCodeFactory(etablissement=self.etab, routing="feedback")

        self.client.get(reverse("routing:qr_code_redirect", args=[self.etab.slug, qr.short_code]))

        self.assertEqual(QRCodeScan.objects.filter(qr_code=qr).count(), 1)

    def test_404_for_invalid_short_code(self):
        response = self.client.get(reverse("routing:qr_code_redirect", args=[self.etab.slug, "INVALID1"]))

        self.assertEqual(response.status_code, 404)

    def test_404_for_mismatched_etablissement(self):
        other_etab = EtablissementFactory()
        qr = QRCodeFactory(etablissement=other_etab, routing="feedback")

        response = self.client.get(reverse("routing:qr_code_redirect", args=[self.etab.slug, qr.short_code]))

        self.assertEqual(response.status_code, 404)
