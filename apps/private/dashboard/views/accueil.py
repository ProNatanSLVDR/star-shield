from django.shortcuts import redirect
from django.urls import reverse

from apps.private.dashboard.render import starshield_render
from apps.public.reviews.models import ReviewAnalytics
from starshield.decorators import unselect_etablissement


@unselect_etablissement
def accueil_view(request):
    # Redirect to onboarding if not completed
    if not request.user.onboarding_completed:
        return redirect(reverse("dashboard:onboarding:welcome"))

    # Initialize stats with defaults
    total_etablissements = 0
    active_etablissements = 0
    average_rating = None
    total_qr_consultations = 0

    # Calculate statistics if user has google_credential
    if hasattr(request.user, "google_credential") and request.user.google_credential:
        etablissements = request.user.google_credential.etablissements.all()

        # Total establishments count
        total_etablissements = etablissements.count()

        # Active establishments count
        active_etablissements = etablissements.filter(active=True).count()

        # Average rating: get latest RatingHistory entry for each establishment
        ratings_list = []
        for etablissement in etablissements:
            latest_rating_entry = etablissement.rating_history.order_by("-created_at").first()
            if latest_rating_entry:
                ratings_list.append(float(latest_rating_entry.rating))

        # Calculate average if we have ratings
        if ratings_list:
            average_rating = sum(ratings_list) / len(ratings_list)

        # Total QR consultations across all establishments
        total_qr_consultations = ReviewAnalytics.objects.filter(
            etablissement__in=etablissements, type="feedback_viewed"
        ).count()

    context = {
        "total_etablissements": total_etablissements,
        "active_etablissements": active_etablissements,
        "average_rating": average_rating,
        "total_qr_consultations": total_qr_consultations,
    }

    return starshield_render(request, "accueil.html", context=context, page_name="accueil")
