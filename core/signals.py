from __future__ import annotations

import logging
from typing import Any

from django.apps import AppConfig
from django.db.models.signals import post_migrate
from django.dispatch import receiver

from .models import Entreprise

logger = logging.getLogger(__name__)


@receiver(post_migrate)
def ensure_public_entreprise(sender: AppConfig, **kwargs: Any) -> None:
    if sender.name != 'core':
        return

    try:
        Entreprise.objects.get_or_create(nom='Public')
    except Exception:  # pragma: no cover - defensive logging
        logger.exception('Unable to ensure the default public entreprise exists')


