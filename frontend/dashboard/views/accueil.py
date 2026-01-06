from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse
from frontend.dashboard.render import starshield_render
import logging

logger = logging.getLogger(__name__)


@login_required
def accueil_view(request):
    # Redirect to onboarding if not completed
    if not request.user.onboarding_completed:
        return redirect(reverse("dashboard:onboarding:welcome"))

    return starshield_render(request, "accueil.html", page_name="accueil")
