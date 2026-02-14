from django.contrib import messages
from django.shortcuts import redirect
from django.template.response import TemplateResponse

from apps.private.auths.choices import AI_LANGUAGE_CHOICES, AI_LENGTH_CHOICES, AI_TONE_CHOICES
from apps.private.dashboard.render import starshield_render
from starshield.decorators import (
    google_gmb_connected_required,
    selected_etablissement_required,
)

from .forms import AiResponseSettingsForm

AI_PREVIEW_TEXTS = {
    # Professionnel - FR
    ("professionnel", "short", "fr"): (
        "Nous vous remercions pour votre retour, Madame Dupont. Votre satisfaction est notre priorité."
    ),
    ("professionnel", "medium", "fr"): (
        "Nous vous remercions sincèrement pour votre retour, Madame Dupont. Votre satisfaction est notre priorité"
        " et nous sommes ravis que notre équipe ait su répondre à vos attentes. Nous espérons avoir le plaisir"
        " de vous accueillir à nouveau."
    ),
    ("professionnel", "long", "fr"): (
        "Nous vous remercions sincèrement pour votre retour, Madame Dupont. Votre satisfaction est au cœur de nos"
        " préoccupations et nous sommes ravis que notre équipe ait su répondre à vos attentes. C'est grâce à des"
        " retours comme le vôtre que nous pouvons continuer à améliorer la qualité de nos services. Nous mettons"
        " un point d'honneur à offrir une expérience irréprochable à chacun de nos clients. Nous espérons avoir"
        " le plaisir de vous accueillir à nouveau très prochainement."
    ),
    # Professionnel - EN
    ("professionnel", "short", "en"): "Thank you for your feedback, Mrs. Dupont. Your satisfaction is our priority.",
    ("professionnel", "medium", "en"): (
        "Thank you sincerely for your feedback, Mrs. Dupont. Your satisfaction is our priority and we are delighted"
        " that our team met your expectations. We look forward to welcoming you again."
    ),
    ("professionnel", "long", "en"): (
        "Thank you sincerely for your feedback, Mrs. Dupont. Your satisfaction is at the heart of our concerns and"
        " we are delighted that our team met your expectations. It is thanks to feedback like yours that we can"
        " continue to improve the quality of our services. We take great pride in offering an impeccable experience"
        " to each of our clients. We look forward to welcoming you again very soon."
    ),
    # Empathique - FR
    ("empathique", "short", "fr"): "Votre avis nous touche beaucoup, Marie. Merci du fond du cœur.",
    ("empathique", "medium", "fr"): (
        "Votre avis nous touche beaucoup, Marie. Savoir que vous avez vécu une expérience aussi positive nous"
        " remplit de joie. C'est grâce à des retours comme le vôtre que notre équipe trouve sa motivation"
        " au quotidien."
    ),
    ("empathique", "long", "fr"): (
        "Votre avis nous touche profondément, Marie. Savoir que vous avez vécu une expérience aussi positive"
        " nous remplit de joie et de gratitude. Chaque membre de notre équipe s'investit avec passion pour"
        " créer des moments uniques. C'est grâce à des personnes comme vous que nous trouvons la motivation"
        " de donner le meilleur de nous-mêmes chaque jour. Votre recommandation est le plus beau des compliments."
    ),
    # Empathique - EN
    ("empathique", "short", "en"): (
        "Your review truly touches us, Marie. Thank you from the bottom of our hearts."
    ),
    ("empathique", "medium", "en"): (
        "Your review truly touches us, Marie. Knowing that you had such a positive experience fills us with joy."
        " It's thanks to feedback like yours that our team finds motivation every day."
    ),
    ("empathique", "long", "en"): (
        "Your review deeply touches us, Marie. Knowing that you had such a positive experience fills us with joy"
        " and gratitude. Every member of our team is passionately dedicated to creating unique moments. It's"
        " thanks to people like you that we find the motivation to give our very best every day. Your"
        " recommendation is the most beautiful compliment."
    ),
    # Enthousiaste - FR
    ("enthousiaste", "short", "fr"): "Quelle joie de lire votre commentaire, Marie ! Merci infiniment !",
    ("enthousiaste", "medium", "fr"): (
        "Quelle joie de lire votre commentaire, Marie ! Nous sommes absolument ravis que vous ayez passé un"
        " excellent moment avec notre équipe. Votre recommandation nous fait chaud au cœur, merci infiniment !"
    ),
    ("enthousiaste", "long", "fr"): (
        "Quelle joie immense de lire votre commentaire, Marie ! Nous sommes absolument ravis que vous ayez passé"
        " un excellent moment avec notre équipe. C'est exactement ce genre de retour qui nous donne une énergie"
        " incroyable ! Toute l'équipe est aux anges de savoir que vous avez apprécié votre expérience. Votre"
        " recommandation nous fait chaud au cœur et nous motive à nous surpasser. Merci mille fois et à très vite !"
    ),
    # Enthousiaste - EN
    ("enthousiaste", "short", "en"): "What a joy to read your comment, Marie! Thank you so much!",
    ("enthousiaste", "medium", "en"): (
        "What a joy to read your comment, Marie! We are absolutely thrilled that you had a wonderful time with"
        " our team. Your recommendation warms our hearts, thank you so much!"
    ),
    ("enthousiaste", "long", "en"): (
        "What an immense joy to read your comment, Marie! We are absolutely thrilled that you had a wonderful"
        " time with our team. This is exactly the kind of feedback that gives us incredible energy! The whole"
        " team is over the moon knowing you enjoyed your experience. Your recommendation warms our hearts and"
        " motivates us to surpass ourselves. Thank you a thousand times and see you very soon!"
    ),
    # Amical - FR
    ("amical", "short", "fr"): "Merci beaucoup Marie ! À très bientôt chez nous !",
    ("amical", "medium", "fr"): (
        "Merci beaucoup Marie ! On est super contents que l'équipe vous ait plu. C'est toujours un plaisir"
        " d'accueillir des personnes aussi sympathiques. À très bientôt chez nous !"
    ),
    ("amical", "long", "fr"): (
        "Merci beaucoup Marie ! On est super contents que l'équipe vous ait plu, ça fait vraiment plaisir à"
        " entendre. C'est toujours un bonheur d'accueillir des personnes aussi sympathiques que vous. On fait"
        " de notre mieux pour que chaque visite soit un bon moment. Votre recommandation nous touche énormément,"
        " c'est la plus belle des récompenses. À très bientôt chez nous !"
    ),
    # Amical - EN
    ("amical", "short", "en"): "Thank you so much Marie! See you soon!",
    ("amical", "medium", "en"): (
        "Thank you so much Marie! We're so happy you liked the team. It's always a pleasure to welcome such"
        " lovely people. See you very soon!"
    ),
    ("amical", "long", "en"): (
        "Thank you so much Marie! We're so happy you liked the team, it really means a lot to hear that. It's"
        " always a joy to welcome people as nice as you. We do our best to make every visit a great time. Your"
        " recommendation means the world to us, it's the best reward. See you very soon!"
    ),
    # Concis - FR
    ("concis", "short", "fr"): "Merci Marie. Au plaisir.",
    ("concis", "medium", "fr"): (
        "Merci pour votre avis, Marie. Ravis de votre expérience. Au plaisir de vous revoir."
    ),
    ("concis", "long", "fr"): (
        "Merci pour votre avis, Marie. Ravis que l'équipe vous ait plu. Votre recommandation nous fait plaisir."
        " Au plaisir de vous revoir."
    ),
    # Concis - EN
    ("concis", "short", "en"): "Thank you Marie. See you soon.",
    ("concis", "medium", "en"): (
        "Thank you for your review, Marie. Glad you enjoyed your experience. See you again soon."
    ),
    ("concis", "long", "en"): (
        "Thank you for your review, Marie. Glad the team made a good impression. Your recommendation means a lot."
        " See you again soon."
    ),
}

CUSTOMER_REVIEW_TEXTS = {
    "fr": "Excellent service ! L'équipe est très accueillante et professionnelle. Je recommande vivement.",
    "en": "Excellent service! The team is very welcoming and professional. I highly recommend.",
}

_TONE_LABELS = dict(AI_TONE_CHOICES)
_LENGTH_LABELS = dict(AI_LENGTH_CHOICES)
_LANGUAGE_LABELS = dict(AI_LANGUAGE_CHOICES)


def _get_preview_context(tone, length, language, etablissement):
    """Build context dict for the AI preview partial."""
    # auto-detect shows French (review is in French)
    display_language = "fr" if language == "auto" else language

    ai_preview_text = AI_PREVIEW_TEXTS.get((tone, length, display_language), "")
    customer_review_text = CUSTOMER_REVIEW_TEXTS.get(display_language, CUSTOMER_REVIEW_TEXTS["fr"])

    # Detect unsaved changes
    saved = {
        "ai_response_tone": etablissement.ai_response_tone,
        "ai_response_length": etablissement.ai_response_length,
        "ai_response_language": etablissement.ai_response_language,
        "ai_response_validation_required": etablissement.ai_response_validation_required,
        "ai_response_malicious_protection": etablissement.ai_response_malicious_protection,
    }

    current = {
        "ai_response_tone": tone,
        "ai_response_length": length,
        "ai_response_language": language,
        "ai_response_validation_required": etablissement._preview_validation_required,
        "ai_response_malicious_protection": etablissement._preview_malicious_protection,
    }

    has_unsaved_changes = saved != current

    return {
        "ai_preview_text": ai_preview_text,
        "customer_review_text": customer_review_text,
        "tone_label": _TONE_LABELS.get(tone, tone).capitalize(),
        "length_label": _LENGTH_LABELS.get(length, length),
        "language_label": _LANGUAGE_LABELS.get(language, language),
        "has_unsaved_changes": has_unsaved_changes,
    }


@google_gmb_connected_required
@selected_etablissement_required
def ai_responses_preview_view(request):
    etablissement = request.etablissement

    tone = request.GET.get("ai_response_tone", etablissement.ai_response_tone)
    length = request.GET.get("ai_response_length", etablissement.ai_response_length)
    language = request.GET.get("ai_response_language", etablissement.ai_response_language)

    validation_required = request.GET.get("ai_response_validation_required", "") == "on"
    malicious_protection = request.GET.get("ai_response_malicious_protection", "") == "on"

    # Attach temporary attrs for comparison
    etablissement._preview_validation_required = validation_required
    etablissement._preview_malicious_protection = malicious_protection

    context = _get_preview_context(tone, length, language, etablissement)

    return TemplateResponse(request, "etablissement/ai_responses/ai_preview_partial.html", context)


@google_gmb_connected_required
@selected_etablissement_required
def ai_responses_settings_view(request):
    etablissement = request.etablissement

    if request.method == "POST":
        form = AiResponseSettingsForm(request.POST)
        if form.is_valid():
            etablissement.ai_response_tone = form.cleaned_data["ai_response_tone"]
            etablissement.ai_response_length = form.cleaned_data["ai_response_length"]
            etablissement.ai_response_language = form.cleaned_data["ai_response_language"]
            etablissement.ai_response_validation_required = form.cleaned_data["ai_response_validation_required"]
            etablissement.ai_response_malicious_protection = form.cleaned_data["ai_response_malicious_protection"]
            etablissement.save()

            messages.success(request, "Paramètres des réponses IA mis à jour avec succès.")
            return redirect("dashboard:etablissement:ai_responses:settings")
    else:
        form = AiResponseSettingsForm(
            initial={
                "ai_response_tone": etablissement.ai_response_tone,
                "ai_response_length": etablissement.ai_response_length,
                "ai_response_language": etablissement.ai_response_language,
                "ai_response_validation_required": etablissement.ai_response_validation_required,
                "ai_response_malicious_protection": etablissement.ai_response_malicious_protection,
            }
        )

    # Build initial preview context
    etablissement._preview_validation_required = etablissement.ai_response_validation_required
    etablissement._preview_malicious_protection = etablissement.ai_response_malicious_protection

    preview_context = _get_preview_context(
        etablissement.ai_response_tone,
        etablissement.ai_response_length,
        etablissement.ai_response_language,
        etablissement,
    )

    context = {
        "etablissement": etablissement,
        "form": form,
        **preview_context,
    }

    return starshield_render(
        request,
        "etablissement/ai_responses/settings.html",
        context=context,
        page_name="ai_responses_settings",
    )
