from django.test import TestCase
from django.urls import reverse

from tests.factories import EtablissementFactory, QRCodeFactory


class TestDashboardQRCodeViews(TestCase):
    def setUp(self):
        self.etab = EtablissementFactory(active=True)
        self.user = self.etab.google_credential.user
        self.client.force_login(self.user)

        session = self.client.session
        session["selected_etablissement"] = self.etab.id
        session.save()

    def _settings_payload(self, qr_code, **overrides):
        payload = {
            "name": qr_code.name,
            "routing": qr_code.routing,
            "qr_fill_color": qr_code.qr_fill_color,
            "qr_fill_color_secondary": qr_code.qr_fill_color_secondary,
            "qr_background_color": qr_code.qr_background_color,
            "qr_style": qr_code.qr_style,
            "qr_color_mask": qr_code.qr_color_mask,
        }
        payload.update(overrides)
        return payload

    def test_locked_qr_ignores_name_and_routing_changes(self):
        qr_code = self.etab.qr_codes.get(name="Filtre")
        update_url = reverse("dashboard:etablissement:qrcodes", args=[qr_code.short_code])

        response = self.client.post(
            update_url,
            data=self._settings_payload(
                qr_code,
                name="QR modifie",
                routing="roulette",
                qr_fill_color="#123456",
            ),
        )

        self.assertEqual(response.status_code, 302)
        qr_code.refresh_from_db()
        self.assertEqual(qr_code.name, "Filtre")
        self.assertEqual(qr_code.routing, "feedback")
        self.assertEqual(qr_code.qr_fill_color, "#123456")

    def test_locked_qr_cannot_be_deleted(self):
        qr_code = self.etab.qr_codes.get(name="Roulette")
        delete_url = reverse("dashboard:etablissement:qrcode_delete_partial", args=[qr_code.short_code])

        response = self.client.post(delete_url)

        self.assertEqual(response.status_code, 302)
        self.assertTrue(self.etab.qr_codes.filter(id=qr_code.id).exists())

    def test_unlocked_qr_can_update_name_routing_and_delete(self):
        qr_code = QRCodeFactory(etablissement=self.etab, name="Custom QR", routing="feedback")
        update_url = reverse("dashboard:etablissement:qrcodes", args=[qr_code.short_code])

        update_response = self.client.post(
            update_url,
            data=self._settings_payload(
                qr_code,
                name="Custom QR Renomme",
                routing="verify",
            ),
        )
        self.assertEqual(update_response.status_code, 302)

        qr_code.refresh_from_db()
        self.assertEqual(qr_code.name, "Custom QR Renomme")
        self.assertEqual(qr_code.routing, "verify")

        delete_url = reverse("dashboard:etablissement:qrcode_delete_partial", args=[qr_code.short_code])
        delete_response = self.client.post(delete_url)
        self.assertEqual(delete_response.status_code, 302)
        self.assertFalse(self.etab.qr_codes.filter(id=qr_code.id).exists())

    def test_selector_displays_permament_label_for_locked_qr_codes(self):
        response = self.client.get(reverse("dashboard:etablissement:qrcodes"))

        self.assertEqual(response.status_code, 200)
        locked_slots = [slot for slot in response.context["all_slots"] if slot and slot.locked]
        self.assertEqual(len(locked_slots), 2)
        self.assertContains(response, "Permament")
