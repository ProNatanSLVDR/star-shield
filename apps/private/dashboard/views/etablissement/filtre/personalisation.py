from django.contrib import messages
from django.shortcuts import redirect
from django.template.response import TemplateResponse

from apps.private.dashboard.render import starshield_render
from apps.public.reviews.utils import build_feedback_context
from starshield.decorators import (
    google_gmb_connected_required,
    selected_etablissement_required,
)

from .forms import ReviewSettingsForm

PREVIEW_FIELDS = ["review_accent_color", "review_show_etablissement_pill", "review_page_label", "review_page_text"]


def _build_preview(etablissement, overrides=None):
    """Build preview context, optionally overriding etablissement attrs."""
    if overrides:
        for key, value in overrides.items():
            setattr(etablissement, key, value)

    identifier = str(etablissement.uuid)
    return build_feedback_context(etablissement, identifier, mode="main")


@google_gmb_connected_required
@selected_etablissement_required
def personalisation_preview_view(request):
    etablissement = request.etablissement

    # Read form values from GET params
    accent_color = request.GET.get("review_accent_color", etablissement.review_accent_color)
    show_pill_raw = request.GET.get("review_show_etablissement_pill", "True")
    show_pill = show_pill_raw == "True"
    page_label = request.GET.get("review_page_label", etablissement.review_page_label)
    page_text = request.GET.get("review_page_text", etablissement.review_page_text)

    # Detect unsaved changes by comparing with DB values
    from apps.private.auths.models import Etablissement

    saved = Etablissement.objects.values(*PREVIEW_FIELDS).get(pk=etablissement.pk)
    current = {
        "review_accent_color": accent_color,
        "review_show_etablissement_pill": show_pill,
        "review_page_label": page_label,
        "review_page_text": page_text,
    }
    # Normalize: saved show_pill could be bool or str
    saved_pill = saved["review_show_etablissement_pill"]
    if isinstance(saved_pill, str):
        saved_pill = saved_pill == "True"
    saved_normalized = {
        "review_accent_color": saved["review_accent_color"],
        "review_show_etablissement_pill": saved_pill,
        "review_page_label": saved["review_page_label"] or "",
        "review_page_text": saved["review_page_text"] or "",
    }
    current_normalized = {
        "review_accent_color": current["review_accent_color"],
        "review_show_etablissement_pill": current["review_show_etablissement_pill"],
        "review_page_label": current["review_page_label"] or "",
        "review_page_text": current["review_page_text"] or "",
    }
    has_unsaved_changes = saved_normalized != current_normalized

    overrides = {
        "review_accent_color": accent_color,
        "review_show_etablissement_pill": show_pill,
        "review_page_label": page_label,
        "review_page_text": page_text,
    }

    preview_context = _build_preview(etablissement, overrides)

    context = {
        "preview_context": preview_context,
        "has_unsaved_changes": has_unsaved_changes,
    }

    return TemplateResponse(request, "etablissement/filtre/personalisation_preview_partial.html", context)


@google_gmb_connected_required
@selected_etablissement_required
def personalisation_settings_view(request):
    etablissement = request.etablissement

    if request.method == "POST":
        form = ReviewSettingsForm(request.POST)
        if form.is_valid():
            etablissement.review_accent_color = form.cleaned_data["review_accent_color"]
            etablissement.review_show_etablissement_pill = form.cleaned_data["review_show_etablissement_pill"]
            etablissement.review_page_label = form.cleaned_data.get("review_page_label", "")
            etablissement.review_page_text = form.cleaned_data.get("review_page_text", "")
            etablissement.save()

            messages.success(request, "Personalisation mise à jour avec succès.")
            return redirect("dashboard:etablissement:filtre:personalisation")
    else:
        form = ReviewSettingsForm(
            initial={
                "review_accent_color": etablissement.review_accent_color,
                "review_show_etablissement_pill": etablissement.review_show_etablissement_pill,
                "review_page_label": etablissement.review_page_label or "",
                "review_page_text": etablissement.review_page_text or "",
            }
        )

    # Build preview context for feedback template
    preview_context = _build_preview(etablissement)

    context = {
        "etablissement": etablissement,
        "form": form,
        "preview_context": preview_context,
    }

    return starshield_render(
        request,
        "etablissement/filtre/personalisation.html",
        context=context,
        page_name="personalisation",
    )
