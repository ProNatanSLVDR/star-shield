"""
Django settings for tasks_api project.

This extends starshield.settings and overrides API-specific configurations.
"""

from pathlib import Path
from configurations import Configuration
import os

# Import base settings from starshield
from starshield.settings import (
    Base as StarshieldBase,
    Dev as StarshieldDev,
    Prod as StarshieldProd,
)

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


class Base(StarshieldBase):
    """Base settings for tasks API, extending starshield base settings."""

    ROOT_URLCONF = "tasks_api.urls"
    WSGI_APPLICATION = "tasks_api.wsgi.application"

    # API-specific middleware (remove web-specific ones)
    MIDDLEWARE = [
        "django.middleware.security.SecurityMiddleware",
        "django.contrib.sessions.middleware.SessionMiddleware",
        "django.middleware.common.CommonMiddleware",
        "django.middleware.csrf.CsrfViewMiddleware",
        "django.contrib.auth.middleware.AuthenticationMiddleware",
        "django.contrib.messages.middleware.MessageMiddleware",
        "django.middleware.clickjacking.XFrameOptionsMiddleware",
    ]

    # django-ninja doesn't need to be in INSTALLED_APPS, it works as a router
    # Keep shared apps from starshield and add tasks_api app
    INSTALLED_APPS = StarshieldBase.INSTALLED_APPS + [
        "tasks_api",
    ]

    # Cloud Tasks configuration
    CLOUD_TASKS_PROJECT_ID = os.getenv("CLOUD_TASKS_PROJECT_ID", "")
    CLOUD_TASKS_LOCATION = os.getenv("CLOUD_TASKS_LOCATION", "us-central1")
    CLOUD_TASKS_QUEUE_NAME = os.getenv("CLOUD_TASKS_QUEUE_NAME", "review-fetch-queue")

    # API base URL (for Cloud Tasks to call back)
    TASKS_API_BASE_URL = os.getenv("TASKS_API_BASE_URL", "http://localhost:8001")

    # API authentication token (for Cloud Tasks callbacks)
    TASKS_API_AUTH_TOKEN = os.getenv("TASKS_API_AUTH_TOKEN", "")

    # Task configuration
    TASK_MAX_RETRIES = 3
    TASK_TIMEOUT_SECONDS = 3600  # 1 hour


class Dev(Base, StarshieldDev):
    """Development settings for tasks API."""

    pass


class Prod(Base, StarshieldProd):
    """Production settings for tasks API."""

    pass
