import logging
from typing import Any

from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_migrate
from django.db.utils import OperationalError, ProgrammingError
from django.utils.translation import gettext_lazy as _
from django_tenants.utils import get_domain_model, get_tenant_model


LOGGER = logging.getLogger(__name__)
@post_migrate
def ensure_public_tenant(sender: Any, **kwargs: Any) -> None:  # pragma: no cover - management hook
    try:
        schema_name = getattr(settings, 'DEFAULT_PUBLIC_TENANT_SCHEMA', 'public')
        tenant_name = getattr(settings, 'DEFAULT_PUBLIC_TENANT_NAME', _('Public'))
        domain_name = getattr(settings, 'DEFAULT_PUBLIC_TENANT_DOMAIN', 'app')

        tenant_model = get_tenant_model()
        domain_model = get_domain_model()

        with transaction.atomic():
            tenant, _ = tenant_model.objects.get_or_create(
                schema_name=schema_name,
                defaults={'nom': tenant_name},
            )

            if tenant.nom != tenant_name:
                tenant.nom = tenant_name
                tenant.save(update_fields=['nom'])

            domain_model.objects.update_or_create(
                domain=domain_name,
                tenant=tenant,
                defaults={'is_primary': True},
            )

            domain_model.objects.filter(tenant=tenant).exclude(domain=domain_name).update(is_primary=False)
    except (ProgrammingError, OperationalError):
        return
    except Exception:  # pylint: disable=broad-except
        LOGGER.exception("Unable to ensure default public tenant")

