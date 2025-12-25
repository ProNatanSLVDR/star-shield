"""
Django settings for tasks_api project.

This extends starshield.settings and overrides API-specific configurations.
"""

from pathlib import Path
import os

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

    # Cloud Tasks configuration
    CLOUD_TASKS_PROJECT_ID = os.getenv("CLOUD_TASKS_PROJECT_ID", "")
    CLOUD_TASKS_LOCATION = os.getenv("CLOUD_TASKS_LOCATION", "")
    CLOUD_TASKS_SERVICE_ACCOUNT = "cloud-run@starshield-app.iam.gserviceaccount.com"

    # API base URL (for Cloud Tasks to call back)
    TASKS_API_BASE_URL = os.getenv("TASKS_API_BASE_URL", "http://localhost:8001")
    TASKS_API_QUEUE_NAME = os.getenv("TASKS_API_QUEUE_NAME", "")

    # Task configuration
    TASK_MAX_RETRIES = 3
    TASK_TIMEOUT_SECONDS = 3600  # 1 hour


class Dev(Base, StarshieldDev):
    """Development settings for tasks API."""

    pass


class Prod(Base, StarshieldProd):
    """Production settings for tasks API."""

    pass
