"""
Django settings for tasks_api project.

This extends starshield.settings and overrides API-specific configurations.
"""

from pathlib import Path

# Import base settings from starshield
from starshield.settings import (
    Base as StarshieldBase,
    Dev as StarshieldDev,
    Prod as StarshieldProd,
)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


class Base:
    """Base settings for tasks API, extending starshield base settings."""

    ROOT_URLCONF = "tasks_api.urls"
    WSGI_APPLICATION = "tasks_api.wsgi.application"

    # API-specific middleware (remove web-specific ones)
    MIDDLEWARE = StarshieldBase.CORE_MIDDLEWARE


class Dev(Base, StarshieldDev):
    """Development settings for tasks API."""

    pass


class Prod(Base, StarshieldProd):
    """Production settings for tasks API."""

    pass
