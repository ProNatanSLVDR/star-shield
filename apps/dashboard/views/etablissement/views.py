from django.shortcuts import render, redirect
from django.db.models import Avg, Count, Q
from django.utils import timezone
from datetime import timedelta
from auths.models import Etablissement
from apps.reviews.models import Review
from apps.dashboard.render import starshield_render
from starshield.decorators import google_gmb_connected_required, selected_etablissement_required


@google_gmb_connected_required
@selected_etablissement_required
def overview_view(request):
    """
    Comprehensive overview page for the selected etablissement.
    """
    # Get selected etablissement
    etablissement_id = request.session.get("selected_etablissement")
    etablissement = Etablissement.objects.filter(
        id=etablissement_id, 
        google_credential=request.user.google_credential
    ).first()
    
    if not etablissement:
        return redirect("dashboard:etablissements:list")
    
    # Get period filter (default to 30 days)
    period = request.GET.get('period', '30')
    period_days = {
        '7': 7,
        '30': 30,
        '90': 90,
        'all': None
    }.get(period, 30)
    
    # Calculate date filter
    if period_days:
        start_date = timezone.now() - timedelta(days=period_days)
        reviews_filter = Q(created_at__gte=start_date)
        rating_history_filter = Q(recorded_at__gte=start_date)
    else:
        reviews_filter = Q()
        rating_history_filter = Q()
    
    # Get reviews for the period
    reviews = Review.objects.filter(
        etablissement=etablissement
    ).filter(reviews_filter).order_by('-created_at')
    
    # Calculate statistics
    total_reviews = reviews.count()
    avg_rating = reviews.aggregate(avg=Avg('rating'))['avg'] or 0
    
    # Source breakdown
    internal_count = reviews.filter(source='internal').count()
    google_count = reviews.filter(source='google').count()
    
    # Rating distribution
    rating_distribution = {}
    for i in range(1, 6):
        rating_distribution[i] = reviews.filter(rating=i).count()
    
    # Recent reviews (last 10)
    recent_reviews = reviews[:10]
    
    # Prepare recent reviews data for table component
    recent_reviews_data = []
    for review in recent_reviews:
        # Create star rating HTML
        stars_html = ""
        for i in range(1, 6):
            if i <= review.rating:
                stars_html += '<i class="fa-solid fa-star text-warning"></i>'
            else:
                stars_html += '<i class="fa-regular fa-star text-muted"></i>'
        
        recent_reviews_data.append({
            'rating': {
                'type': 'html',
                'value': f'<div class="d-flex justify-content-center">{stars_html}</div>'
            },
            'source': {
                'type': 'badge',
                'value': review.get_source_display(),
                'variant': 'primary' if review.source == 'google' else 'secondary'
            },
            'comment': review.comment[:100] + '...' if len(review.comment) > 100 else review.comment or 'Aucun commentaire',
            'created_at': review.created_at.strftime('%d/%m/%Y %H:%M')
        })
    
    # Rating history for trend
    rating_history = etablissement.rating_history.filter(rating_history_filter).order_by('recorded_at')
    
    # Calculate trend
    trend = None
    if rating_history.count() >= 2:
        first_rating = rating_history.first().rating
        last_rating = rating_history.last().rating
        if last_rating > first_rating:
            trend = 'up'
        elif last_rating < first_rating:
            trend = 'down'
        else:
            trend = 'stable'
    
    context = {
        'etablissement': etablissement,
        'period': period,
        'total_reviews': total_reviews,
        'avg_rating': round(avg_rating, 2) if avg_rating else 0,
        'internal_count': internal_count,
        'google_count': google_count,
        'rating_distribution': rating_distribution,
        'recent_reviews': recent_reviews,
        'recent_reviews_data': recent_reviews_data,
        'rating_history': rating_history,
        'trend': trend,
    }
    
    return starshield_render(request, "etablissement/overview.html", context=context, page_name="etablissement")
