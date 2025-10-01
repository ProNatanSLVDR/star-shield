from __future__ import annotations

from django.db import models
from django.utils.translation import gettext_lazy as _


class Entreprise(models.Model):
    nom = models.CharField(max_length=100)

    created_on = models.DateField(auto_now_add=True)
    modified_on = models.DateField(auto_now=True)

    class Meta:
        verbose_name = _('Entreprise')
        verbose_name_plural = _('Entreprises')

    def __str__(self) -> str:
        return self.nom