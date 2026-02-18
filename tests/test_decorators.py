from unittest.mock import Mock

from django.contrib.sessions.backends.db import SessionStore
from django.http import HttpResponse
from django.test import RequestFactory, TestCase

from starshield.decorators import (
    google_gmb_connected_required,
    selected_etablissement_required,
    unselect_etablissement,
)
from tests.factories import GoogleCredentialsFactory, UserFactory


def dummy_view(request, *args, **kwargs):
    return HttpResponse("OK")


class TestGoogleGmbConnectedRequired(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.decorated = google_gmb_connected_required(dummy_view)

    def _make_request(self, user):
        request = self.factory.get("/test/")
        request.user = user
        request.session = SessionStore()
        return request

    def test_redirects_when_no_credential(self):
        user = UserFactory()
        request = self._make_request(user)

        response = self.decorated(request)

        self.assertEqual(response.status_code, 302)
        self.assertIn("reconnect", response.url)

    def test_redirects_when_credential_invalid(self):
        cred = GoogleCredentialsFactory(is_valid=False)
        request = self._make_request(cred.user)

        response = self.decorated(request)

        self.assertEqual(response.status_code, 302)
        self.assertIn("reconnect", response.url)

    def test_redirects_when_invalid_grants(self):
        cred = GoogleCredentialsFactory(is_valid=True, has_invalid_grants=True)
        request = self._make_request(cred.user)

        response = self.decorated(request)

        self.assertEqual(response.status_code, 302)
        self.assertIn("reconnect", response.url)

    def test_allows_when_valid(self):
        cred = GoogleCredentialsFactory(is_valid=True, has_invalid_grants=False)
        request = self._make_request(cred.user)

        response = self.decorated(request)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"OK")


class TestSelectedEtablissementRequired(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.decorated = selected_etablissement_required(dummy_view)

    def test_redirects_when_no_etablissement_in_session(self):
        request = self.factory.get("/test/")
        request.user = UserFactory()
        request.session = SessionStore()
        # Django messages framework needs _messages attribute
        request._messages = Mock()

        response = self.decorated(request)

        self.assertEqual(response.status_code, 302)
        self.assertIn("etablissement", response.url)

    def test_allows_when_etablissement_in_session(self):
        request = self.factory.get("/test/")
        request.user = UserFactory()
        request.session = SessionStore()
        request.session["selected_etablissement"] = 1

        response = self.decorated(request)

        self.assertEqual(response.status_code, 200)


class TestUnselectEtablissement(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.decorated = unselect_etablissement(dummy_view)

    def test_clears_session_when_etablissement_selected(self):
        request = self.factory.get("/test/")
        request.user = UserFactory()
        request.session = SessionStore()
        request.session["selected_etablissement"] = 1
        request.etablissement = object()

        response = self.decorated(request)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn("selected_etablissement", request.session)
        self.assertFalse(hasattr(request, "etablissement"))

    def test_allows_when_no_etablissement(self):
        request = self.factory.get("/test/")
        request.user = UserFactory()
        request.session = SessionStore()

        response = self.decorated(request)

        self.assertEqual(response.status_code, 200)
