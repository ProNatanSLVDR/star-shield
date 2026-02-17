from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.private.auths.models import Etablissement, QRCode, User
from tests.factories import EtablissementFactory, GoogleCredentialsFactory, QRCodeFactory, UserFactory


class TestDeleteOldProfilePicture(TestCase):
    def test_deletes_old_picture_on_change(self):
        user = UserFactory()
        old_picture = MagicMock()
        old_picture.name = "profile_pictures/old.jpg"
        old_picture.__bool__ = lambda self: True

        # Set the old picture directly in DB
        User.objects.filter(pk=user.pk).update()

        with patch.object(User.objects, "get") as mock_get:
            old_user = MagicMock()
            old_user.profile_picture = old_picture
            mock_get.return_value = old_user

            new_picture = MagicMock()
            new_picture.name = "profile_pictures/new.jpg"
            new_picture.__bool__ = lambda self: True
            user.profile_picture = new_picture

            # Trigger pre_save signal
            from apps.private.auths.models import delete_old_profile_picture

            delete_old_profile_picture(User, user)

            old_picture.delete.assert_called_once_with(save=False)

    def test_no_delete_when_picture_unchanged(self):
        user = UserFactory()
        same_picture = MagicMock()
        same_picture.name = "profile_pictures/same.jpg"
        same_picture.__bool__ = lambda self: True

        with patch.object(User.objects, "get") as mock_get:
            old_user = MagicMock()
            old_user.profile_picture = same_picture
            mock_get.return_value = old_user

            user.profile_picture = same_picture

            from apps.private.auths.models import delete_old_profile_picture

            delete_old_profile_picture(User, user)

            same_picture.delete.assert_not_called()

    def test_no_delete_for_new_user(self):
        user = User(email="new@example.com")
        user.pk = None  # New user

        from apps.private.auths.models import delete_old_profile_picture

        # Should not raise
        delete_old_profile_picture(User, user)


class TestDeleteOldQRLogo(TestCase):
    def test_deletes_old_logo_on_change(self):
        qr = QRCodeFactory()
        old_logo = MagicMock()
        old_logo.name = "qr_logos/old.png"
        old_logo.__bool__ = lambda self: True

        with patch.object(QRCode.objects, "get") as mock_get:
            old_qr = MagicMock()
            old_qr.qr_logo = old_logo
            mock_get.return_value = old_qr

            new_logo = MagicMock()
            new_logo.name = "qr_logos/new.png"
            new_logo.__bool__ = lambda self: True
            qr.qr_logo = new_logo

            from apps.private.auths.models import delete_old_qr_logo

            delete_old_qr_logo(QRCode, qr)

            old_logo.delete.assert_called_once_with(save=False)

    def test_no_delete_for_new_qr(self):
        qr = QRCode()
        qr.pk = None

        from apps.private.auths.models import delete_old_qr_logo

        # Should not raise
        delete_old_qr_logo(QRCode, qr)


class TestCreateDefaultQRCodes(TestCase):
    def test_creates_two_default_qr_codes(self):
        cred = GoogleCredentialsFactory()
        etab = Etablissement.objects.create(
            google_credential=cred,
            location_id="locations/new",
            account_id="accounts/new",
            title="New Etablissement",
            slug="new-etab-qr-test",
        )

        qr_codes = QRCode.objects.filter(etablissement=etab, locked=True)
        self.assertEqual(qr_codes.count(), 2)

        names = set(qr_codes.values_list("name", flat=True))
        self.assertEqual(names, {"Filtre", "Roulette"})

        routings = set(qr_codes.values_list("routing", flat=True))
        self.assertEqual(routings, {"feedback", "roulette"})

    def test_no_qr_codes_on_update(self):
        etab = EtablissementFactory()
        initial_count = QRCode.objects.filter(etablissement=etab).count()

        etab.title = "Updated Title"
        etab.save()

        final_count = QRCode.objects.filter(etablissement=etab).count()
        self.assertEqual(initial_count, final_count)
