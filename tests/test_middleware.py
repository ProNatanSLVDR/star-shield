import json

from django.contrib.messages.storage.fallback import FallbackStorage
from django.contrib.sessions.backends.db import SessionStore
from django.http import HttpResponse, HttpResponseRedirect
from django.test import RequestFactory, TestCase

from starshield.middleware import CustomMessageMiddleware, EtablissementMiddleware
from tests.factories import EtablissementFactory, UserFactory


class TestCustomMessageMiddleware(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _make_middleware(self, response=None):
        if response is None:
            response = HttpResponse("OK")

        def get_response(request):
            return response

        return CustomMessageMiddleware(get_response)

    def _make_request_with_messages(self, messages=None):
        request = self.factory.get("/test/")
        request.session = SessionStore()
        request.session.create()
        request._messages = FallbackStorage(request)
        if messages:
            for msg in messages:
                request._messages.add(25, msg)  # 25 = INFO level
        return request

    def test_adds_x_messages_header(self):
        middleware = self._make_middleware()
        request = self._make_request_with_messages(["Hello world"])

        response = middleware(request)

        self.assertIn("X-Messages", response.headers)
        data = json.loads(response.headers["X-Messages"])
        self.assertEqual(len(data), 1)
        self.assertEqual(data[0]["message"], "Hello world")

    def test_skips_header_on_redirect(self):
        redirect_response = HttpResponseRedirect("/other/")
        middleware = self._make_middleware(redirect_response)
        request = self._make_request_with_messages(["Hello world"])

        response = middleware(request)

        self.assertNotIn("X-Messages", response.headers)
        self.assertEqual(response.status_code, 302)

    def test_valid_json_in_header(self):
        middleware = self._make_middleware()
        request = self._make_request_with_messages(["Message 1", "Message 2"])

        response = middleware(request)

        data = json.loads(response.headers["X-Messages"])
        self.assertEqual(len(data), 2)

    def test_no_header_when_no_messages(self):
        middleware = self._make_middleware()
        request = self._make_request_with_messages()

        response = middleware(request)

        self.assertNotIn("X-Messages", response.headers)


class TestEtablissementMiddleware(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def _make_middleware(self):
        def get_response(request):
            return HttpResponse("OK")

        return EtablissementMiddleware(get_response)

    def test_sets_request_etablissement(self):
        etab = EtablissementFactory()
        middleware = self._make_middleware()
        request = self.factory.get("/test/")
        request.session = {"selected_etablissement": etab.id}
        request.user = etab.google_credential.user

        middleware(request)

        self.assertEqual(request.etablissement, etab)

    def test_clears_session_when_etablissement_deleted(self):
        user = UserFactory()
        middleware = self._make_middleware()
        request = self.factory.get("/test/")
        session = SessionStore()
        session["selected_etablissement"] = 99999  # non-existent
        session.create()
        request.session = session
        request.user = user

        middleware(request)

        self.assertNotIn("selected_etablissement", request.session)

    def test_no_error_when_no_session_key(self):
        middleware = self._make_middleware()
        request = self.factory.get("/test/")
        request.session = SessionStore()

        response = middleware(request)

        self.assertEqual(response.status_code, 200)
        self.assertFalse(hasattr(request, "etablissement"))
