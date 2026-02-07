"""
Weekly Performance Summary service - generates AI-powered weekly summaries.
"""

from datetime import datetime, timedelta

from django.db.models import Case, Count, IntegerField, When
from django.utils import timezone

from apps.private.auths.models import Etablissement, WeeklyPerformanceSummary
from apps.public.reviews.models import Review, ReviewAnalytics
from apps.tasks_api.services.openrouter_service import generate_response
from starshield.logger import logger


def get_week_start_date(date=None):
    """
    Get the Monday of the week for a given date.

    Args:
        date: datetime.date or None. If None, uses current date in Europe/Paris timezone.

    Returns:
        datetime.date: Monday of the week
    """
    if date is None:
        # Get current date in Europe/Paris timezone
        paris_tz = timezone.get_current_timezone()
        now = timezone.now().astimezone(paris_tz)
        date = now.date()

    # Calculate days to subtract to get to Monday (weekday() returns 0=Monday, 6=Sunday)
    days_to_monday = date.weekday()
    monday = date - timedelta(days=days_to_monday)
    return monday


def get_current_week_start():
    """
    Get the Monday of the current week in Europe/Paris timezone.

    Returns:
        datetime.date: Monday of current week
    """
    return get_week_start_date()


def get_previous_week_start(week_start_date):
    """
    Get the Monday of the previous week.

    Args:
        week_start_date: datetime.date representing a Monday

    Returns:
        datetime.date: Monday of previous week
    """
    return week_start_date - timedelta(days=7)


def collect_weekly_metrics(etablissement: Etablissement, week_start_date):
    """
    Collect all performance metrics for a given week.

    Args:
        etablissement: The establishment to collect metrics for
        week_start_date: datetime.date representing Monday of the week

    Returns:
        dict: Dictionary containing all collected metrics
    """
    week_end_date = week_start_date + timedelta(days=6)  # Sunday

    # Convert dates to datetime for filtering
    week_start_datetime = timezone.make_aware(datetime.combine(week_start_date, datetime.min.time()))
    week_end_datetime = timezone.make_aware(datetime.combine(week_end_date, datetime.max.time()))

    # Reviews metrics
    reviews_queryset = Review.objects.filter(etablissement=etablissement)

    # Reviews written during the week
    week_reviews = reviews_queryset.filter(
        writen_at__gte=week_start_datetime,
        writen_at__lte=week_end_datetime,
    )

    rating_counts = week_reviews.aggregate(
        total=Count("id"),
        **{f"rating_{r}": Count(Case(When(rating=r, then=1), output_field=IntegerField())) for r in range(1, 6)},
    )
    new_reviews_count = rating_counts["total"]
    new_reviews_by_rating = {r: rating_counts[f"rating_{r}"] for r in range(1, 6)}

    # Extract review texts (cap at 20, truncate comments to 500 chars)
    review_texts = []
    for review in week_reviews.order_by("-writen_at")[:20]:
        reviewer_name = "Anonyme"
        if review.google_reviewer_data:
            reviewer_name = review.google_reviewer_data.get("displayName", "Anonyme")
        comment = review.comment or ""
        if len(comment) > 500:
            comment = comment[:500] + "..."
        review_texts.append(
            {
                "rating": review.rating,
                "comment": comment,
                "reviewer_name": reviewer_name,
                "source": review.source,
            }
        )

    # Rating at start and end of week
    rating_at_start = None
    rating_at_end = None

    rating_history = (
        etablissement.rating_history.filter(created_at__lte=week_start_datetime).order_by("-created_at").first()
    )
    if rating_history:
        rating_at_start = float(rating_history.rating)

    rating_history = (
        etablissement.rating_history.filter(created_at__lte=week_end_datetime).order_by("-created_at").first()
    )
    if rating_history:
        rating_at_end = float(rating_history.rating)

    # Total reviews at end of week
    total_reviews_at_end = reviews_queryset.filter(writen_at__lte=week_end_datetime).count()

    # QR code analytics
    analytics_queryset = ReviewAnalytics.objects.filter(etablissement=etablissement)

    qr_page_visits = analytics_queryset.filter(
        type="feedback_viewed",
        created_at__gte=week_start_datetime,
        created_at__lte=week_end_datetime,
    ).count()

    reviews_redirected_google = analytics_queryset.filter(
        type="feedback_external",
        created_at__gte=week_start_datetime,
        created_at__lte=week_end_datetime,
    ).count()

    reviews_kept_private = analytics_queryset.filter(
        type="feedback_internal_viewed",
        created_at__gte=week_start_datetime,
        created_at__lte=week_end_datetime,
    ).count()

    internal_feedback_submitted = analytics_queryset.filter(
        type="feedback_internal_submitted",
        created_at__gte=week_start_datetime,
        created_at__lte=week_end_datetime,
    ).count()

    # AI responses generated during the week
    ai_responses_count = reviews_queryset.filter(
        reply_type="ai",
        reply_date__gte=week_start_datetime,
        reply_date__lte=week_end_datetime,
    ).count()

    # Comparison with previous week
    previous_week_start = get_previous_week_start(week_start_date)
    previous_week_end = previous_week_start + timedelta(days=6)
    previous_week_start_datetime = timezone.make_aware(datetime.combine(previous_week_start, datetime.min.time()))
    previous_week_end_datetime = timezone.make_aware(datetime.combine(previous_week_end, datetime.max.time()))

    previous_week_reviews = reviews_queryset.filter(
        writen_at__gte=previous_week_start_datetime,
        writen_at__lte=previous_week_end_datetime,
    ).count()

    previous_week_qr_visits = analytics_queryset.filter(
        type="feedback_viewed",
        created_at__gte=previous_week_start_datetime,
        created_at__lte=previous_week_end_datetime,
    ).count()

    previous_week_redirects = analytics_queryset.filter(
        type="feedback_external",
        created_at__gte=previous_week_start_datetime,
        created_at__lte=previous_week_end_datetime,
    ).count()

    metrics = {
        "week_start_date": week_start_date.isoformat(),
        "week_end_date": week_end_date.isoformat(),
        "new_reviews_count": new_reviews_count,
        "new_reviews_by_rating": new_reviews_by_rating,
        "review_texts": review_texts,
        "rating_at_start": rating_at_start,
        "rating_at_end": rating_at_end,
        "total_reviews_at_end": total_reviews_at_end,
        "qr_page_visits": qr_page_visits,
        "reviews_redirected_google": reviews_redirected_google,
        "reviews_kept_private": reviews_kept_private,
        "internal_feedback_submitted": internal_feedback_submitted,
        "ai_responses_count": ai_responses_count,
        "previous_week": {
            "new_reviews_count": previous_week_reviews,
            "qr_page_visits": previous_week_qr_visits,
            "reviews_redirected_google": previous_week_redirects,
        },
    }

    return metrics


def parse_summary_sections(raw_text: str) -> dict:
    """
    Parse AI response into 3 sections using markers.

    Expected markers: ---SHORT_SUMMARY---, ---FULL_REPORT---, ---ADVICE---

    Returns:
        dict with keys: short_summary, summary_text, advice_text
    """
    result = {
        "short_summary": "",
        "summary_text": "",
        "advice_text": "",
    }

    if "---SHORT_SUMMARY---" in raw_text and "---FULL_REPORT---" in raw_text and "---ADVICE---" in raw_text:
        parts = raw_text.split("---SHORT_SUMMARY---")
        after_short = parts[1] if len(parts) > 1 else ""

        parts = after_short.split("---FULL_REPORT---")
        result["short_summary"] = parts[0].strip()
        after_full = parts[1] if len(parts) > 1 else ""

        parts = after_full.split("---ADVICE---")
        result["summary_text"] = parts[0].strip()
        result["advice_text"] = parts[1].strip() if len(parts) > 1 else ""
    else:
        # Fallback: put everything in summary_text, generate a short preview
        result["summary_text"] = raw_text.strip()
        # Use first 200 chars as short summary
        preview = raw_text.strip().replace("\n", " ")
        if len(preview) > 200:
            preview = preview[:200] + "..."
        result["short_summary"] = preview

    return result


def generate_weekly_summary(etablissement: Etablissement, metrics_data: dict) -> dict:
    """
    Generate AI-powered weekly summary using OpenRouter API.

    Args:
        etablissement: The establishment
        metrics_data: Dictionary of metrics collected for the week

    Returns:
        dict: {"short_summary": ..., "summary_text": ..., "advice_text": ...}
    """
    system_prompt = """Tu es Shieldy, un assistant IA amical, fun mais professionnel, qui aide les propriétaires d'établissements à comprendre leur performance hebdomadaire.

Tu écris toujours en français. Tu utilises "vous" pour t'adresser au propriétaire.

Ton style :
- Amical, positif et encourageant, avec une touche d'humour
- Concis et structuré
- Tu mets en avant les points positifs et les tendances encourageantes
- Tu donnes des conseils constructifs et actionnables
- Tu compares avec la semaine précédente quand c'est pertinent
- Tu analyses les avis clients pour en tirer des enseignements

Formatage :
- Utilise **gras** pour mettre en valeur les chiffres clés et les points importants
- Utilise des listes à puces avec "- " pour structurer les points
- N'utilise PAS de titres markdown (pas de #, ##, etc.) — les titres sont gérés dans l'interface
- Garde un style concis et aéré

Tu dois structurer ta réponse en 3 sections séparées par des marqueurs :

---SHORT_SUMMARY---
Un résumé très court (2-3 phrases max) pour un aperçu rapide de la semaine.
Ce texte apparaît sur une carte de preview. Pas de markdown ici, juste du texte simple.

---FULL_REPORT---
Le rapport complet de la semaine (5-10 points). Analyse les chiffres, les tendances,
et les avis clients. Utilise des puces et du **gras** pour les chiffres.

---ADVICE---
2-4 conseils personnalisés et actionnables basés sur les données de la semaine.
Utilise des puces et du **gras**. Sois concret et pratique."""

    # Build user prompt with metrics
    week_start = metrics_data.get("week_start_date", "")
    week_end = metrics_data.get("week_end_date", "")
    new_reviews = metrics_data.get("new_reviews_count", 0)
    rating_start = metrics_data.get("rating_at_start")
    rating_end = metrics_data.get("rating_at_end")
    total_reviews = metrics_data.get("total_reviews_at_end", 0)
    qr_visits = metrics_data.get("qr_page_visits", 0)
    redirects = metrics_data.get("reviews_redirected_google", 0)
    kept_private = metrics_data.get("reviews_kept_private", 0)
    internal_submitted = metrics_data.get("internal_feedback_submitted", 0)
    ai_responses = metrics_data.get("ai_responses_count", 0)
    review_texts = metrics_data.get("review_texts", [])

    prev_week = metrics_data.get("previous_week", {})
    prev_week_reviews = prev_week.get("new_reviews_count", 0)
    prev_week_qr = prev_week.get("qr_page_visits", 0)
    prev_week_redirects = prev_week.get("reviews_redirected_google", 0)

    rating_start_str = f"{rating_start:.1f}" if rating_start is not None else "non disponible"
    rating_end_str = f"{rating_end:.1f}" if rating_end is not None else "non disponible"

    # Build reviews section
    reviews_section = ""
    if review_texts:
        reviews_lines = []
        for r in review_texts:
            stars = "★" * r["rating"] + "☆" * (5 - r["rating"])
            source_label = "Google" if r["source"] == "google" else "Interne"
            comment_text = r["comment"] if r["comment"] else "(pas de commentaire)"
            reviews_lines.append(f"- {r['reviewer_name']} ({source_label}) {stars} : {comment_text}")
        reviews_section = "\n\nAvis reçus cette semaine :\n" + "\n".join(reviews_lines)
    else:
        reviews_section = "\n\nAucun avis reçu cette semaine."

    user_prompt = f"""Analyse la performance de {etablissement.title} pour la semaine du {week_start} au {week_end}.

Données de la semaine :
- Nouveaux avis reçus : {new_reviews}
- Note moyenne au début de la semaine : {rating_start_str}
- Note moyenne à la fin de la semaine : {rating_end_str}
- Total d'avis à la fin de la semaine : {total_reviews}
- Visites de la page QR Code : {qr_visits}
- Redirections vers Google : {redirects}
- Avis gardés en interne : {kept_private}
- Feedbacks internes soumis : {internal_submitted}
- Réponses IA générées : {ai_responses}

Comparaison avec la semaine précédente :
- Nouveaux avis : {new_reviews} (semaine précédente : {prev_week_reviews})
- Visites QR Code : {qr_visits} (semaine précédente : {prev_week_qr})
- Redirections Google : {redirects} (semaine précédente : {prev_week_redirects}){reviews_section}

Génère le rapport structuré avec les 3 sections (---SHORT_SUMMARY---, ---FULL_REPORT---, ---ADVICE---)."""

    try:
        raw_response = generate_response(user_prompt, system_prompt)
        return parse_summary_sections(raw_response)
    except Exception as e:
        logger.error(f"[{etablissement.id}] Failed to generate weekly summary: {e}", exc_info=True)
        raise


def generate_and_store_weekly_summary(etablissement: Etablissement, week_start_date=None) -> WeeklyPerformanceSummary:
    """
    Generate and store a weekly performance summary for an establishment.

    Args:
        etablissement: The establishment
        week_start_date: datetime.date for Monday of the week. If None, uses previous week.

    Returns:
        WeeklyPerformanceSummary: The created summary instance
    """
    if week_start_date is None:
        # Default to previous week (Monday-Sunday that just ended)
        current_week_start = get_current_week_start()
        week_start_date = get_previous_week_start(current_week_start)

    # Check if summary already exists
    existing_summary = WeeklyPerformanceSummary.objects.filter(
        etablissement=etablissement,
        week_start_date=week_start_date,
    ).first()

    if existing_summary:
        logger.info(f"[{etablissement.id}] Weekly summary already exists for week {week_start_date}")
        return existing_summary

    try:
        # Collect metrics
        metrics_data = collect_weekly_metrics(etablissement, week_start_date)

        # Generate summary (now returns a dict with 3 sections)
        sections = generate_weekly_summary(etablissement, metrics_data)

        # Store summary
        summary = WeeklyPerformanceSummary.objects.create(
            etablissement=etablissement,
            week_start_date=week_start_date,
            short_summary=sections["short_summary"],
            summary_text=sections["summary_text"],
            advice_text=sections["advice_text"],
            metrics_data=metrics_data,
        )

        logger.info(f"[{etablissement.id}] Weekly summary generated and stored for week {week_start_date}")
        return summary

    except Exception as e:
        logger.error(f"[{etablissement.id}] Error generating weekly summary: {e}", exc_info=True)
        raise
