from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError

from auths.models import User


class Command(BaseCommand):
    help = "Make a user an admin by setting is_staff and is_superuser to True"

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            type=str,
            required=True,
            help="Email address of the user to make admin",
        )

    def handle(self, *args: Any, **options: Any) -> None:  # noqa: ANN002, ANN003 - Django signature
        email = options["email"]

        # Normalize email to lowercase (matching UserManager behavior)
        normalized_email = User.objects.normalize_email(email).lower()

        try:
            user = User.objects.get(email=normalized_email)
        except User.DoesNotExist:
            raise CommandError(f"User with email '{email}' not found.") from None
        except DatabaseError as exc:
            raise CommandError(f"Database error while looking up user: {exc}") from exc

        # Check if user is already an admin
        if user.is_staff and user.is_superuser:
            self.stdout.write(
                self.style.WARNING(
                    f"User '{user.email}' is already an admin (is_staff=True, is_superuser=True)."
                )
            )
            return

        # Set admin flags
        try:
            user.is_staff = True
            user.is_superuser = True
            user.save(update_fields=["is_staff", "is_superuser"])
        except DatabaseError as exc:
            raise CommandError(f"Failed to update user admin status: {exc}") from exc

        self.stdout.write(
            self.style.SUCCESS(
                f"Successfully made user '{user.email}' an admin (is_staff=True, is_superuser=True)."
            )
        )






