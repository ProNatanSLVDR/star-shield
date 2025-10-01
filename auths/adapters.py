from __future__ import annotations

from allauth.account.adapter import DefaultAccountAdapter


class AccountAdapter(DefaultAccountAdapter):
    """Custom account adapter to enforce email-based authentication only."""

    def is_open_for_signup(self, request):
        return super().is_open_for_signup(request)

