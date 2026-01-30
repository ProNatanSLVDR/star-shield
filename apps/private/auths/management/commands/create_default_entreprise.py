from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, transaction

from apps.private.auths.models import Entreprise


class Command(BaseCommand):
    help = "Create the default entreprise if it does not exist."

    def handle(self, *args: Any, **options: Any) -> None:
        try:
            with transaction.atomic():
                entreprise, created = Entreprise.objects.get_or_create(nom="default")
        except DatabaseError as exc:  # pragma: no cover - defensive error handling
            raise CommandError("Failed to ensure the default entreprise exists.") from exc

        if created:
            self.stdout.write(self.style.SUCCESS("Created entreprise named 'default'."))
            return

        self.stdout.write("Entreprise named 'default' already exists.")
