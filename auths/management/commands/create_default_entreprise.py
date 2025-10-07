from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, transaction

from auths.models import Entreprise


class Command(BaseCommand):
    help = "Create the default entreprise if it does not exist."  # noqa: A003 - Django uses 'help'

    def handle(self, *args: Any, **options: Any) -> None:  # noqa: ANN002, ANN003 - Django signature
        try:
            with transaction.atomic():
                entreprise, created = Entreprise.objects.get_or_create(nom="default")
        except DatabaseError as exc:  # pragma: no cover - defensive error handling
            raise CommandError("Failed to ensure the default entreprise exists.") from exc

        if created:
            self.stdout.write(self.style.SUCCESS("Created entreprise named 'default'."))
            return

        self.stdout.write("Entreprise named 'default' already exists.")

