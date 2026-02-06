"""
AI Response service - generates and posts AI replies to Google Maps reviews.
"""

from datetime import timedelta

from django.utils import timezone

from apps.private.auths.models import Etablissement
from apps.public.reviews.models import Review
from apps.tasks_api.services.openrouter_service import generate_response
from starshield.logger import logger

# Prompt templates per tone
TONE_INSTRUCTIONS = {
    "professionnel": (
        "Tu es un assistant qui redige des reponses professionnelles aux avis clients. "
        "Ton style est formel, courtois et oriente service client. "
        "Tu utilises le vouvoiement systematiquement."
    ),
    "empathique": (
        "Tu es un assistant qui redige des reponses empathiques aux avis clients. "
        "Ton style est tres comprehensif, reconnaissant et sincere. "
        "Tu montres que tu comprends les emotions du client."
    ),
    "enthousiaste": (
        "Tu es un assistant qui redige des reponses enthousiastes aux avis clients. "
        "Ton style est dynamique, positif et chaleureux. "
        "Tu exprimes de la joie et de la gratitude avec energie."
    ),
    "amical": (
        "Tu es un assistant qui redige des reponses amicales aux avis clients. "
        "Ton style est decontracte, proche et respectueux. "
        "Tu utilises un ton convivial et accessible."
    ),
    "concis": (
        "Tu es un assistant qui redige des reponses concises aux avis clients. "
        "Ton style est bref, direct et efficace. "
        "Tu vas droit au but sans fioritures."
    ),
}

LENGTH_INSTRUCTIONS = {
    "short": "La reponse doit etre courte, 1 a 2 phrases maximum.",
    "medium": "La reponse doit etre de longueur moyenne, 2 a 4 phrases.",
    "long": "La reponse peut etre plus detaillee, 4 a 6 phrases.",
}

LANGUAGE_INSTRUCTIONS = {
    "fr": "Tu reponds TOUJOURS en francais.",
    "en": "Tu reponds TOUJOURS en anglais (English).",
    "auto": "Tu reponds dans la meme langue que l'avis du client. Si tu ne peux pas determiner la langue, reponds en francais.",
}

RATING_CONTEXT = {
    "low": (
        "Cet avis est negatif (1-2 etoiles). Le client est insatisfait. "
        "Adopte un angle apologetique : presente des excuses, montre de la comprehension, "
        "et propose de rectifier la situation. Ne sois pas defensif."
    ),
    "mid": (
        "Cet avis est mitige (3 etoiles). Le client a eu une experience correcte mais pas exceptionnelle. "
        "Remercie pour le retour, reconnais les points a ameliorer, et montre que tu prends note."
    ),
    "high": (
        "Cet avis est positif (4-5 etoiles). Le client est satisfait. "
        "Remercie chaleureusement, exprime de la gratitude et invite le client a revenir."
    ),
}


def _get_rating_context(rating: int) -> str:
    if rating <= 2:
        return RATING_CONTEXT["low"]
    if rating == 3:
        return RATING_CONTEXT["mid"]
    return RATING_CONTEXT["high"]


def _build_system_prompt(etablissement: Etablissement) -> str:
    tone = etablissement.ai_response_tone
    length = etablissement.ai_response_length
    language = etablissement.ai_response_language

    parts = [
        TONE_INSTRUCTIONS.get(tone, TONE_INSTRUCTIONS["professionnel"]),
        LENGTH_INSTRUCTIONS.get(length, LENGTH_INSTRUCTIONS["medium"]),
        LANGUAGE_INSTRUCTIONS.get(language, LANGUAGE_INSTRUCTIONS["fr"]),
        f'Tu rediges des reponses pour l\'etablissement "{etablissement.title}".',
        "IMPORTANT: Tu ne generes QUE la reponse a l'avis, sans aucun prefixe, sans guillemets, sans explication.",
    ]

    return "\n".join(parts)


def _build_user_prompt(review: Review, rating_context: str) -> str:
    reviewer_name = "Un client"
    if review.google_reviewer_data and review.google_reviewer_data.get("displayName"):
        reviewer_name = review.google_reviewer_data["displayName"]

    comment = review.comment or "(pas de commentaire)"

    return (
        f"{rating_context}\n\n"
        f"Auteur de l'avis : {reviewer_name}\n"
        f"Note : {review.rating}/5 etoiles\n"
        f"Commentaire : {comment}\n\n"
        f"Redige une reponse appropriee a cet avis."
    )


def generate_and_send_responses(etablissement: Etablissement) -> dict:
    """
    Generate AI responses for unreplied reviews and post them via the GMB API.

    Args:
        etablissement: The establishment to process

    Returns:
        Dict with stats: {total_reviews, responded, failed, errors}
    """
    if not etablissement.ai_responses_enabled:
        return {"total_reviews": 0, "responded": 0, "failed": 0, "errors": ["AI responses not enabled"]}

    # Query unreplied reviews from the last 30 days
    cutoff_date = timezone.now() - timedelta(days=30)
    unreplied_reviews = (
        Review.objects.filter(
            etablissement=etablissement,
            source="google",
            reply_comment__isnull=True,
            writen_at__gte=cutoff_date,
        )
        .exclude(comment="")
        .order_by("-writen_at")
    )

    total_reviews = unreplied_reviews.count()
    responded = 0
    failed = 0
    errors = []

    if total_reviews == 0:
        logger.info(f"[{etablissement.id}] No unreplied reviews found")
        return {"total_reviews": 0, "responded": 0, "failed": 0, "errors": []}

    logger.info(f"[{etablissement.id}] Found {total_reviews} unreplied reviews to process")

    # Get the reviews service for posting replies
    if not etablissement.google_credential_id:
        error_msg = f"No Google credentials for {etablissement.title}"
        logger.error(f"[{etablissement.id}] {error_msg}")
        return {"total_reviews": total_reviews, "responded": 0, "failed": total_reviews, "errors": [error_msg]}

    reviews_service = etablissement.google_credential.get_reviews_service()
    if reviews_service is None:
        error_msg = f"Unable to initialize reviews service for {etablissement.title}"
        logger.error(f"[{etablissement.id}] {error_msg}")
        return {"total_reviews": total_reviews, "responded": 0, "failed": total_reviews, "errors": [error_msg]}

    system_prompt = _build_system_prompt(etablissement)

    for review in unreplied_reviews:
        try:
            # Generate AI response
            rating_context = _get_rating_context(review.rating)
            user_prompt = _build_user_prompt(review, rating_context)
            ai_response = generate_response(user_prompt, system_prompt)

            # Post reply via GMB API
            parent_path = f"{etablissement.account_id}/{etablissement.location_id}"
            review_name = f"{parent_path}/reviews/{review.google_review_id}"

            reviews_service.accounts().locations().reviews().updateReply(
                name=review_name,
                body={"comment": ai_response},
            ).execute()

            # Update review record
            review.reply_comment = ai_response
            review.reply_date = timezone.now()
            review.reply_type = "ai"
            review.save(update_fields=["reply_comment", "reply_date", "reply_type"])

            responded += 1
            logger.info(f"[{etablissement.id}] AI response posted for review {review.google_review_id}")

        except Exception as e:
            failed += 1
            error_msg = f"Failed to process review {review.google_review_id}: {e}"
            errors.append(error_msg)
            logger.error(f"[{etablissement.id}] {error_msg}", exc_info=True)
            etablissement.google_credential._check_and_set_invalid_grant(e)

    logger.info(
        f"[{etablissement.id}] AI responses complete: {responded} responded, {failed} failed out of {total_reviews}"
    )

    return {
        "total_reviews": total_reviews,
        "responded": responded,
        "failed": failed,
        "errors": errors,
    }
