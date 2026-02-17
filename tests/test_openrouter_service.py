from unittest.mock import MagicMock, patch

from django.test import SimpleTestCase, override_settings


class TestGenerateResponse(SimpleTestCase):
    def _import_and_reset(self):
        """Import fresh and reset the cached session."""
        import apps.tasks_api.services.openrouter_service as mod

        mod._session = None
        return mod.generate_response

    @override_settings(OPENROUTER_API_KEY="", OPENROUTER_MODEL="test-model")
    def test_raises_on_missing_api_key(self):
        generate_response = self._import_and_reset()
        with self.assertRaises(RuntimeError, msg="OPENROUTER_API_KEY is not configured"):
            generate_response("prompt", "system")

    @override_settings(OPENROUTER_API_KEY="sk-test-key", OPENROUTER_MODEL="test-model")
    @patch("apps.tasks_api.services.openrouter_service._get_session")
    def test_returns_content_from_api(self, mock_get_session):
        mock_response = MagicMock()
        mock_response.json.return_value = {"choices": [{"message": {"content": "  AI response text  "}}]}
        mock_response.raise_for_status = MagicMock()
        mock_session = MagicMock()
        mock_session.post.return_value = mock_response
        mock_get_session.return_value = mock_session

        generate_response = self._import_and_reset()
        result = generate_response("user prompt", "system prompt")

        self.assertEqual(result, "AI response text")
        mock_session.post.assert_called_once()

    @override_settings(OPENROUTER_API_KEY="sk-test-key", OPENROUTER_MODEL="test-model")
    @patch("apps.tasks_api.services.openrouter_service._get_session")
    def test_raises_on_http_error(self, mock_get_session):
        import requests

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.RequestException("500 Server Error")
        mock_session = MagicMock()
        mock_session.post.return_value = mock_response
        mock_get_session.return_value = mock_session

        generate_response = self._import_and_reset()
        with self.assertRaises(RuntimeError, msg="OpenRouter API request failed"):
            generate_response("prompt", "system")

    @override_settings(OPENROUTER_API_KEY="sk-test-key", OPENROUTER_MODEL="test-model")
    @patch("apps.tasks_api.services.openrouter_service._get_session")
    def test_raises_on_unexpected_response_format(self, mock_get_session):
        mock_response = MagicMock()
        mock_response.json.return_value = {"unexpected": "format"}
        mock_response.raise_for_status = MagicMock()
        mock_session = MagicMock()
        mock_session.post.return_value = mock_response
        mock_get_session.return_value = mock_session

        generate_response = self._import_and_reset()
        with self.assertRaises(RuntimeError, msg="Unexpected OpenRouter response format"):
            generate_response("prompt", "system")

    @override_settings(OPENROUTER_API_KEY="sk-test-key", OPENROUTER_MODEL="test-model")
    @patch("apps.tasks_api.services.openrouter_service._get_session")
    def test_sends_correct_payload(self, mock_get_session):
        mock_response = MagicMock()
        mock_response.json.return_value = {"choices": [{"message": {"content": "response"}}]}
        mock_response.raise_for_status = MagicMock()
        mock_session = MagicMock()
        mock_session.post.return_value = mock_response
        mock_get_session.return_value = mock_session

        generate_response = self._import_and_reset()
        generate_response("my prompt", "my system")

        call_kwargs = mock_session.post.call_args
        payload = call_kwargs[1]["json"] if "json" in call_kwargs[1] else call_kwargs.kwargs["json"]
        self.assertEqual(payload["model"], "test-model")
        self.assertEqual(payload["messages"][0]["role"], "system")
        self.assertEqual(payload["messages"][0]["content"], "my system")
        self.assertEqual(payload["messages"][1]["role"], "user")
        self.assertEqual(payload["messages"][1]["content"], "my prompt")


class TestGetSession(SimpleTestCase):
    def test_returns_session_with_retry(self):
        import apps.tasks_api.services.openrouter_service as mod

        mod._session = None
        session = mod._get_session()
        self.assertIsNotNone(session)
        # Second call returns same instance
        self.assertIs(mod._get_session(), session)
        mod._session = None  # Reset for other tests
