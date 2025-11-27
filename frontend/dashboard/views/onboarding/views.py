from functools import wraps
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.urls import reverse
from django.contrib import messages
from django.utils.translation import gettext as _

from frontend.dashboard.render import starshield_render
from auths.models import GoogleCredentials


def check_onboarding_completed(view_func):
    """
    Decorator to redirect users who have already completed onboarding.
    """

    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if request.user.onboarding_completed:
            return redirect(reverse("dashboard:accueil"))
        return view_func(request, *args, **kwargs)

    return _wrapped_view


@login_required
@check_onboarding_completed
def welcome_view(request):
    context = {
        "step": 1,
        "total_steps": 5,
        "next_url": reverse("dashboard:onboarding:how_it_works"),
    }
    return starshield_render(request, "onboarding/welcome.html", context=context, page_name="onboarding")


@login_required
@check_onboarding_completed
def how_it_works_view(request):
    context = {
        "step": 2,
        "total_steps": 5,
        "prev_url": reverse("dashboard:onboarding:welcome"),
        "next_url": reverse("dashboard:onboarding:connect_google"),
    }
    return starshield_render(request, "onboarding/how_it_works.html", context=context, page_name="onboarding")


@login_required
@check_onboarding_completed
def connect_google_view(request):
    has_google_connected = hasattr(request.user, "google_credential") and request.user.google_credential.is_valid

    context = {
        "step": 3,
        "total_steps": 5,
        "prev_url": reverse("dashboard:onboarding:how_it_works"),
        "next_url": reverse("dashboard:onboarding:import_etablissements") if has_google_connected else None,
        "has_google_connected": has_google_connected,
        "google_connect_url": reverse("auths:google_gmb_start"),
    }
    return starshield_render(request, "onboarding/connect_google.html", context=context, page_name="onboarding")


@login_required
@check_onboarding_completed
def import_etablissements_view(request):
    # Check if Google is connected
    if not hasattr(request.user, "google_credential") or not request.user.google_credential.is_valid:
        messages.warning(request, _("Veuillez d'abord connecter votre compte Google My Business."))
        return redirect(reverse("dashboard:onboarding:connect_google"))

    google_credential = request.user.google_credential

    # Handle form submission
    if request.method == "POST":
        from frontend.dashboard.views.etablissements.forms import ImportEtablissementForm

        available_locations = request.session.get("available_locations", [])
        if not available_locations:
            available_locations = google_credential.list_available_locations()
            request.session["available_locations"] = available_locations

        form = ImportEtablissementForm(request.POST, available_locations=available_locations)

        if form.is_valid():
            selected_locations = form.cleaned_data.get("locations", [])
            locations_dict = {loc["name"]: loc for loc in available_locations}

            # Import each selected location
            imported_count = 0
            for location_name in selected_locations:
                location = locations_dict.get(location_name)
                if location:
                    etablissement = google_credential.create_etablissement_from_location(account_id=location["account_id"], location_id=location_name)
                    if etablissement:
                        imported_count += 1

            if imported_count > 0:
                messages.success(request, _("{} établissement(s) importé(s) avec succès!").format(imported_count))
                request.session.pop("available_locations", None)
                return redirect(reverse("dashboard:onboarding:complete"))
            else:
                messages.error(request, _("Aucun établissement n'a pu être importé."))

    available_locations = google_credential.list_available_locations()
    request.session["available_locations"] = available_locations

    # Filter out locations that already exist
    new_locations = [loc for loc in available_locations if not loc.get("exists", False)]

    from frontend.dashboard.views.etablissements.forms import ImportEtablissementForm

    form = ImportEtablissementForm(available_locations=available_locations)

    context = {
        "step": 4,
        "total_steps": 5,
        "prev_url": reverse("dashboard:onboarding:connect_google"),
        "next_url": reverse("dashboard:onboarding:complete") if new_locations else None,
        "available_locations": available_locations,
        "new_locations": new_locations,
        "has_locations": len(new_locations) > 0,
        "form": form,
    }
    return starshield_render(request, "onboarding/import_etablissements.html", context=context, page_name="onboarding")


@login_required
@check_onboarding_completed
def complete_view(request):
    # Mark onboarding as completed
    if not request.user.onboarding_completed:
        request.user.onboarding_completed = True
        request.user.save()
        messages.success(request, _("Bienvenue sur StarShield ! Votre configuration est terminée."))

    context = {
        "step": 5,
        "total_steps": 5,
    }
    return starshield_render(request, "onboarding/complete.html", context=context, page_name="onboarding")


@login_required
@check_onboarding_completed
def skip_onboarding_view(request):
    """Allow users to skip onboarding."""
    request.user.onboarding_completed = True
    request.user.save()
    messages.info(request, _("Vous pouvez toujours accéder à l'onboarding depuis votre profil."))
    return redirect(reverse("dashboard:accueil"))
