"""
OpenRouter API service for generating AI responses.
"""

import requests
from django.conf import settings
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from starshield.logger import logger

_session = None


def _get_session() -> requests.Session:
    """Get a requests session with retry logic for transient failures."""
    global _session
    if _session is None:
        _session = requests.Session()
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST"],
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        _session.mount("https://", adapter)
    return _session


def generate_response(prompt: str, system_prompt: str) -> str:
    """
    Call OpenRouter chat completions API to generate a response.

    Args:
        prompt: The user message (review content)
        system_prompt: System instructions for tone/style

    Returns:
        The generated response text

    Raises:
        RuntimeError: If the API call fails
    """
    api_key = settings.OPENROUTER_API_KEY
    model = settings.OPENROUTER_MODEL

    if not api_key:
        raise RuntimeError("OPENROUTER_API_KEY is not configured")

    session = _get_session()

    try:
        response = session.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
            },
            timeout=30,
        )
        response.raise_for_status()
    except requests.RequestException as e:
        logger.error(f"OpenRouter API request failed: {e}")
        raise RuntimeError(f"OpenRouter API request failed: {e}") from e

    data = response.json()
    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError) as e:
        logger.error(f"Unexpected OpenRouter response format: {data}")
        raise RuntimeError(f"Unexpected OpenRouter response format: {e}") from e
