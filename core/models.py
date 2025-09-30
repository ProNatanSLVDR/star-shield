from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _
from django_tenants.models import TenantMixin, DomainMixin


class Entreprise(TenantMixin):
    nom = models.CharField(max_length=100)

    created_on = models.DateField(auto_now_add=True)
    modified_on = models.DateField(auto_now=True)


class DomaineEntreprise(DomainMixin):
    pass