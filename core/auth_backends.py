from __future__ import annotations

from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q
from django.core.exceptions import MultipleObjectsReturned


class EmailBackend(ModelBackend):
    def authenticate(self, request, email: str | None = None, password: str | None = None, **kwargs):
        if not email or not password:
            return None

        UserModel = get_user_model()
        normalized_email = UserModel.objects.normalize_email(email).lower()

        try:
            user = UserModel.objects.filter(Q(email__iexact=normalized_email)).first()
        except MultipleObjectsReturned:
            return None

        if user is None:
            return None

        if not user.check_password(password):
            return None

        if not self.user_can_authenticate(user):
            return None

        return user

    def get_user(self, user_id):
        UserModel = get_user_model()
        try:
            user = UserModel.objects.get(pk=user_id)
        except UserModel.DoesNotExist:
            return None

        if self.user_can_authenticate(user):
            return user

        return None

