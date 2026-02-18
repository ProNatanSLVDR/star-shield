import json
from unittest.mock import patch

from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from apps.private.dashboard.render import starshield_render


class TestStarshieldRender(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    @patch("apps.private.dashboard.render.render")
    def test_render_with_template(self, mock_render):
        mock_render.return_value = HttpResponse("rendered")
        request = self.factory.get("/")
        context = {}

        response = starshield_render(
            request,
            template_name="some_template.html",
            context=context,
            page_name="accueil",
        )

        self.assertEqual(response.status_code, 200)
        mock_render.assert_called_once()
        self.assertEqual(context["current_page"], "accueil")

    def test_render_without_template(self):
        request = self.factory.get("/")
        response = starshield_render(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"")

    def test_render_with_hx_triggers(self):
        request = self.factory.get("/")
        response = starshield_render(
            request,
            hx_triggers={"refreshList": True, "closeModal": True},
        )

        self.assertEqual(response.status_code, 200)
        triggers = json.loads(response["HX-Trigger"])
        self.assertIn("refreshList", triggers)
        self.assertIn("closeModal", triggers)

    def test_render_with_all_false_triggers(self):
        request = self.factory.get("/")
        response = starshield_render(
            request,
            hx_triggers={"refreshList": False, "closeModal": False},
        )

        self.assertNotIn("HX-Trigger", response)

    def test_render_with_mixed_triggers(self):
        request = self.factory.get("/")
        response = starshield_render(
            request,
            hx_triggers={"refreshList": True, "closeModal": False},
        )

        triggers = json.loads(response["HX-Trigger"])
        self.assertIn("refreshList", triggers)
        self.assertNotIn("closeModal", triggers)

    @patch("apps.private.dashboard.render.render")
    def test_context_includes_current_page(self, mock_render):
        mock_render.return_value = HttpResponse("ok")
        request = self.factory.get("/")
        context = {}

        starshield_render(
            request,
            template_name="any.html",
            context=context,
            page_name="stats",
        )

        self.assertEqual(context["current_page"], "stats")

    def test_no_triggers_param(self):
        request = self.factory.get("/")
        response = starshield_render(request)

        self.assertNotIn("HX-Trigger", response)
