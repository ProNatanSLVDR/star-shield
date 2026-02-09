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
    "auto": (
        "Tu reponds dans la meme langue que l'avis du client. "
        "Si tu ne peux pas determiner la langue, reponds en francais."
    ),
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

MALICIOUS_CHECK_PROMPT = (
    "Tu es un expert en detection d'avis malveillants sur Google. "
    "Analyse l'avis suivant et determine s'il semble malveillant, faux ou de mauvaise foi.\n\n"
    "Criteres de suspicion :\n"
    "- Avis vague sans details specifiques sur l'experience\n"
    "- Langage agressif ou insultant sans explication\n"
    "- Aucune mention de produit, service ou experience concrete\n"
    "- Avis qui semble venir d'un concurrent ou d'une personne n'ayant pas visite l'etablissement\n\n"
    "Note : {rating}/5\n"
    "Commentaire : {comment}\n\n"
    "Reponds UNIQUEMENT par OUI (suspect) ou NON (legitime)."
)

MIN_REVIEWS_TO_PROCESS = 3


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


def _get_unreplied_reviews(etablissement: Etablissement):
    """Get unreplied reviews: last 24h, with a minimum of MIN_REVIEWS_TO_PROCESS."""
    base_qs = (
        Review.objects.filter(
            etablissement=etablissement,
            source="google",
            reply_comment__isnull=True,
            ai_response_status__isnull=True,
        )
        .exclude(comment="")
        .order_by("-writen_at")
    )

    cutoff = timezone.now() - timedelta(days=1)
    recent = base_qs.filter(writen_at__gte=cutoff)

    if recent.count() >= MIN_REVIEWS_TO_PROCESS:
        return recent

    return base_qs[:MIN_REVIEWS_TO_PROCESS]


def _check_malicious(review: Review) -> tuple[bool, str]:
    """
    Check if a low-rated review seems malicious.
    Returns (is_flagged, reason).
    """
    # Heuristic: no comment or very short comment on low rating
    if not review.comment or len(review.comment.strip()) <= 10:
        return True, "Avis négatif sans commentaire ou commentaire très court"

    # AI-based check
    try:
        prompt = MALICIOUS_CHECK_PROMPT.format(rating=review.rating, comment=review.comment)
        result = generate_response(prompt, "Tu es un assistant de detection de fraude.")
        if result.strip().upper().startswith("OUI"):
            return True, "Détecté comme potentiellement malveillant par l'IA"
    except Exception as e:
        logger.warning(f"[{review.etablissement_id}] Malicious check failed for review {review.id}: {e}")

    return False, ""


def _post_reply_to_google(review: Review, comment: str, reviews_service) -> None:
    """Post a reply to a Google review via GMB API."""
    etablissement = review.etablissement
    parent_path = f"{etablissement.account_id}/{etablissement.location_id}"
    review_name = f"{parent_path}/reviews/{review.google_review_id}"

    reviews_service.accounts().locations().reviews().updateReply(
        name=review_name,
        body={"comment": comment},
    ).execute()

    review.reply_comment = comment
    review.reply_date = timezone.now()
    review.reply_type = "ai"
    review.ai_response_status = "approved"
    review.save(update_fields=["reply_comment", "reply_date", "reply_type", "ai_response_status"])


def generate_and_send_responses(etablissement: Etablissement) -> dict:
    """
    Generate AI responses for unreplied reviews and post them via the GMB API.
    Respects validation mode and malicious protection settings.

    Returns:
        Dict with stats: {total_reviews, responded, failed, pending, flagged, errors}
    """
    if not etablissement.ai_responses_enabled:
        return {
            "total_reviews": 0,
            "responded": 0,
            "failed": 0,
            "pending": 0,
            "flagged": 0,
            "errors": ["AI responses not enabled"],
        }

    unreplied_reviews = _get_unreplied_reviews(etablissement)
    total_reviews = unreplied_reviews.count() if hasattr(unreplied_reviews, "count") else len(unreplied_reviews)
    logger.info(f"[{etablissement.id}] Found {total_reviews} unreplied reviews to process")

    responded = 0
    failed = 0
    pending = 0
    flagged = 0
    errors = []

    if total_reviews == 0:
        logger.info(f"[{etablissement.id}] No unreplied reviews found")
        return {"total_reviews": 0, "responded": 0, "failed": 0, "pending": 0, "flagged": 0, "errors": []}

    # Get reviews service only if we might need to post (not in pure validation mode)
    reviews_service = None
    if not etablissement.ai_response_validation_required:
        if not etablissement.google_credential_id:
            error_msg = f"No Google credentials for {etablissement.title}"
            logger.error(f"[{etablissement.id}] {error_msg}")
            return {
                "total_reviews": total_reviews,
                "responded": 0,
                "failed": total_reviews,
                "pending": 0,
                "flagged": 0,
                "errors": [error_msg],
            }

        reviews_service = etablissement.google_credential.get_reviews_service()
        if reviews_service is None:
            error_msg = f"Unable to initialize reviews service for {etablissement.title}"
            logger.error(f"[{etablissement.id}] {error_msg}")
            return {
                "total_reviews": total_reviews,
                "responded": 0,
                "failed": total_reviews,
                "pending": 0,
                "flagged": 0,
                "errors": [error_msg],
            }

    system_prompt = _build_system_prompt(etablissement)

    for review in unreplied_reviews:
        try:
            # Step 1: Malicious check for low-rated reviews
            is_flagged = False
            flag_reason = ""
            if etablissement.ai_response_malicious_protection and review.rating <= 2:
                is_flagged, flag_reason = _check_malicious(review)

            # Step 2: Generate AI response
            rating_context = _get_rating_context(review.rating)
            user_prompt = _build_user_prompt(review, rating_context)
            ai_response = generate_response(user_prompt, system_prompt)

            # Step 3: Handle based on flags and validation mode
            if is_flagged:
                # Flagged: save draft but don't post, regardless of validation mode
                review.ai_draft_comment = ai_response
                review.ai_response_status = "flagged"
                review.ai_flag_reason = flag_reason
                review.save(update_fields=["ai_draft_comment", "ai_response_status", "ai_flag_reason"])
                flagged += 1
                logger.info(f"[{etablissement.id}] Review {review.google_review_id} flagged: {flag_reason}")

            elif etablissement.ai_response_validation_required:
                # Validation mode: save draft for user review
                review.ai_draft_comment = ai_response
                review.ai_response_status = "pending"
                review.save(update_fields=["ai_draft_comment", "ai_response_status"])
                pending += 1
                logger.info(f"[{etablissement.id}] Review {review.google_review_id} saved as pending")

            else:
                # Auto-post mode: post directly to Google
                _post_reply_to_google(review, ai_response, reviews_service)
                responded += 1
                logger.info(f"[{etablissement.id}] AI response posted for review {review.google_review_id}")

        except Exception as e:
            failed += 1
            error_msg = f"Failed to process review {review.google_review_id}: {e}"
            errors.append(error_msg)
            logger.error(f"[{etablissement.id}] {error_msg}", exc_info=True)
            if etablissement.google_credential_id:
                etablissement.google_credential._check_and_set_invalid_grant(e)

    logger.info(
        f"[{etablissement.id}] AI responses complete: "
        f"{responded} responded, {pending} pending, {flagged} flagged, {failed} failed out of {total_reviews}"
    )

    return {
        "total_reviews": total_reviews,
        "responded": responded,
        "failed": failed,
        "pending": pending,
        "flagged": flagged,
        "errors": errors,
    }


def approve_ai_response(review_id: int, edited_comment: str | None = None) -> bool:
    """Approve a pending/flagged AI response and post it to Google."""
    review = Review.objects.select_related("etablissement__google_credential").get(id=review_id)

    comment = edited_comment or review.ai_draft_comment
    if not comment:
        logger.error(f"No draft comment to approve for review {review_id}")
        return False

    try:
        reviews_service = review.etablissement.google_credential.get_reviews_service()
        if reviews_service is None:
            logger.error(f"Unable to get reviews service for review {review_id}")
            return False

        _post_reply_to_google(review, comment, reviews_service)
        # Clear draft after posting
        review.ai_draft_comment = None
        review.ai_flag_reason = None
        review.save(update_fields=["ai_draft_comment", "ai_flag_reason"])
        return True

    except Exception as e:
        logger.error(f"Failed to approve review {review_id}: {e}", exc_info=True)
        review.etablissement.google_credential._check_and_set_invalid_grant(e)
        return False


def reject_ai_response(review_id: int) -> bool:
    """Reject a pending/flagged AI response."""
    try:
        review = Review.objects.get(id=review_id)
        review.ai_response_status = "rejected"
        review.ai_draft_comment = None
        review.ai_flag_reason = None
        review.save(update_fields=["ai_response_status", "ai_draft_comment", "ai_flag_reason"])
        return True
    except Exception as e:
        logger.error(f"Failed to reject review {review_id}: {e}", exc_info=True)
        return False


def regenerate_ai_response(review_id: int) -> str | None:
    """Regenerate AI draft for a review. Returns the new draft or None on failure."""
    try:
        review = Review.objects.select_related("etablissement").get(id=review_id)
        etablissement = review.etablissement

        system_prompt = _build_system_prompt(etablissement)
        rating_context = _get_rating_context(review.rating)
        user_prompt = _build_user_prompt(review, rating_context)
        ai_response = generate_response(user_prompt, system_prompt)

        # Keep the same status (pending or flagged), just update the draft
        review.ai_draft_comment = ai_response
        review.save(update_fields=["ai_draft_comment"])

        return ai_response

    except Exception as e:
        logger.error(f"Failed to regenerate response for review {review_id}: {e}", exc_info=True)
        return None
