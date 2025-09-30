import logging
from typing import Any, Iterable

from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_migrate
from django.db.utils import OperationalError, ProgrammingError
from django.dispatch import receiver
from django.utils.translation import gettext_lazy as _
from django_tenants.utils import get_tenant_domain_model, get_tenant_model


LOGGER = logging.getLogger(__name__)


@receiver(post_migrate)
def ensure_public_tenant(sender: Any, **kwargs: Any) -> None:
    try:
        schema_name = settings.PUBLIC_SCHEMA_NAME
        tenant_name = getattr(settings, "PUBLIC_TENANT_NAME", "Public")
        domain_name = getattr(settings, "WEBAPP_DOMAIN")

        tenant_model = get_tenant_model()
        domain_model = get_tenant_domain_model()

        with transaction.atomic():
            tenant, created = tenant_model.objects.get_or_create(
                schema_name=schema_name,
                defaults={"nom": tenant_name},
            )

            if not created and tenant.nom != tenant_name:
                tenant.nom = tenant_name
                tenant.save(update_fields=["nom"])

            domain_model.objects.update_or_create(
                domain=domain_name,
                tenant=tenant,
                defaults={"is_primary": True},
            )
    except (ProgrammingError, OperationalError):
        return
    except Exception:  # pylint: disable=broad-except
        LOGGER.exception("Unable to ensure default public tenant")

