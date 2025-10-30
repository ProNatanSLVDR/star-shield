"""
Django management command to schedule nightly review sync tasks.

This command enqueues Cloud Tasks for all Etablissements that need nightly review sync.
Can be called by Cloud Scheduler (cron job).
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db import models
from datetime import timedelta

from auths.models import Etablissement
from tasks_api.services.cloud_tasks import enqueue_review_fetch_task


class Command(BaseCommand):
    help = "Schedule nightly review sync tasks for all Etablissements"

    def add_arguments(self, parser):
        parser.add_argument(
            "--hours-ago",
            type=int,
            default=24,
            help="Only sync Etablissements that haven't been updated in the last N hours (default: 24)",
        )

    def handle(self, *args, **options):
        hours_ago = options["hours_ago"]
        cutoff_time = timezone.now() - timedelta(hours=hours_ago)

        # Get all Etablissements that need syncing
        # (those that haven't been updated recently or have never been updated)
        etablissements = Etablissement.objects.filter(
            models.Q(last_reviews_update__lt=cutoff_time)
            | models.Q(last_reviews_update__isnull=True)
        )

        count = 0
        for etablissement in etablissements:
            task_name = enqueue_review_fetch_task(
                etablissement_id=etablissement.id,
                task_type="fetch-refresh",
            )
            if task_name:
                count += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Enqueued refresh task for Etablissement {etablissement.id} ({etablissement.title})"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"Failed to enqueue task for Etablissement {etablissement.id} ({etablissement.title})"
                    )
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"\nSuccessfully enqueued {count} out of {etablissements.count()} review sync tasks"
            )
        )

