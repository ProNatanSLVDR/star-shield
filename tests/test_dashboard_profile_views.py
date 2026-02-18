from io import BytesIO

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse
from PIL import Image

from tests.factories import UserFactory


def _create_test_image():
    """Create a small in-memory image for upload tests."""
    buffer = BytesIO()
    image = Image.new("RGB", (100, 100), color="red")
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return SimpleUploadedFile("test.png", buffer.read(), content_type="image/png")


class TestProfileView(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.client.force_login(self.user)

    def test_get_returns_200(self):
        response = self.client.get(reverse("dashboard:profile:profile"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("form", response.context)

    def test_post_updates_name(self):
        response = self.client.post(
            reverse("dashboard:profile:profile"),
            data={"first_name": "Jean", "last_name": "Dupont"},
        )
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "Jean")
        self.assertEqual(self.user.last_name, "Dupont")

    def test_post_empty_names(self):
        response = self.client.post(
            reverse("dashboard:profile:profile"),
            data={"first_name": "", "last_name": ""},
        )
        self.assertEqual(response.status_code, 302)
        self.user.refresh_from_db()
        self.assertEqual(self.user.first_name, "")

    def test_unauthenticated_redirects(self):
        self.client.logout()
        response = self.client.get(reverse("dashboard:profile:profile"))
        self.assertEqual(response.status_code, 302)


class TestProfilePicturePartial(TestCase):
    def setUp(self):
        self.user = UserFactory()
        self.client.force_login(self.user)

    def test_get_returns_200(self):
        response = self.client.get(reverse("dashboard:profile:picture_partial"))
        self.assertEqual(response.status_code, 200)

    def test_upload_picture(self):
        image = _create_test_image()
        response = self.client.post(
            reverse("dashboard:profile:picture_partial"),
            data={"profile_picture": image},
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertTrue(self.user.profile_picture)

    def test_delete_picture(self):
        # First upload
        self.user.profile_picture = "test.png"
        self.user.save()
        response = self.client.post(
            reverse("dashboard:profile:picture_partial"),
            data={"delete_profile_picture": "on"},
        )
        self.assertEqual(response.status_code, 200)
        self.user.refresh_from_db()
        self.assertFalse(self.user.profile_picture)

    def test_empty_post(self):
        response = self.client.post(reverse("dashboard:profile:picture_partial"), data={})
        self.assertEqual(response.status_code, 200)
