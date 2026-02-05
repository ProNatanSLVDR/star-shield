"""
OpenRouter API service for generating AI responses.
"""

import requests
from django.conf import settings

from starshield.logger import logger


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

    try:
        response = requests.post(
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
