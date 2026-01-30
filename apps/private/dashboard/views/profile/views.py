from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect
from django.views.decorators.http import require_http_methods

from apps.private.dashboard.render import starshield_render

from .forms import UserProfileForm


@login_required
def profile_view(request):
    user = request.user

    if request.method == "POST":
        form = UserProfileForm(request.POST)
        if form.is_valid():
            user.first_name = form.cleaned_data.get("first_name", "")
            user.last_name = form.cleaned_data.get("last_name", "")
            user.save()
            messages.success(request, "Profil mis à jour avec succès.")
            return redirect("dashboard:profile:profile")
    else:
        form = UserProfileForm(
            initial={
                "first_name": user.first_name,
                "last_name": user.last_name,
            }
        )

    context = {
        "form": form,
        "user": user,
    }

    return starshield_render(
        request,
        "profile/index.html",
        context=context,
        page_name="profile",
    )


@login_required
@require_http_methods(["GET", "POST"])
def profile_picture_partial(request):
    """
    HTMX view for handling profile picture upload and deletion.
    Returns a partial template with the profile picture section.
    """
    user = request.user
    hx_triggers = {}

    if request.method == "POST":
        # Handle profile picture deletion
        if request.POST.get("delete_profile_picture"):
            if user.profile_picture:
                user.profile_picture.delete(save=False)
                user.profile_picture = None
                user.save()
                messages.success(request, "Photo de profil supprimée avec succès.")
                hx_triggers["profile-picture-updated"] = True
        # Handle profile picture upload
        elif "profile_picture" in request.FILES:
            user.profile_picture = request.FILES["profile_picture"]
            user.save()
            messages.success(request, "Photo de profil mise à jour avec succès.")
            hx_triggers["profile-picture-updated"] = True

    context = {
        "user": user,
    }

    return starshield_render(
        request,
        "profile/profile_picture_partial.html",
        context=context,
        hx_triggers=hx_triggers,
    )
