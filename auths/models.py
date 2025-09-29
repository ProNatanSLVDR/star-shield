from django.db import models
from django_tenants.models import TenantMixin, DomainMixin


# Modèles premier niveau
class Entreprise(TenantMixin):
    nom = models.CharField(max_length=100)

    created_on = models.DateField(auto_now_add=True)
    modified_on = models.DateField(auto_now=True)


class DomaineEntreprise(DomainMixin):
    pass