from django.shortcuts import redirect
from django.db.models import Avg, Q
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

    # Sentiment split
    positive_reviews = reviews.filter(rating__gte=4).count()
    neutral_reviews = reviews.filter(rating=3).count()
    negative_reviews = reviews.filter(rating__lte=2).count()

    # Comment coverage
    reviews_with_comment = reviews.exclude(comment__isnull=True).exclude(comment__exact="").count()
    comment_coverage = 0
    if total_reviews:
        comment_coverage = round((reviews_with_comment / total_reviews) * 100)

    # Review pace per day
    reviews_per_day = 0
    if total_reviews:
        if period_days:
            days_in_period = max(period_days, 1)
            reviews_per_day = round(total_reviews / days_in_period, 2)
        else:
            earliest_review = reviews.last()
            latest_review = reviews.first()
            if earliest_review and latest_review:
                span_days = (latest_review.created_at - earliest_review.created_at).days
                if span_days <= 0:
                    span_days = 1
                reviews_per_day = round(total_reviews / span_days, 2)

    # Rating distribution
    rating_distribution = {}
    for i in range(1, 6):
        rating_distribution[i] = reviews.filter(rating=i).count()

    rating_distribution_rows = []
    for rating_value in range(5, 0, -1):
        rating_count = rating_distribution.get(rating_value, 0)
        rating_distribution_rows.append({
            'rating': rating_value,
            'count': rating_count,
            'percentage': 0,
        })

    if total_reviews:
        for rating_row in rating_distribution_rows:
            percentage_value = (rating_row['count'] / total_reviews) * 100
            rating_row['percentage'] = round(percentage_value, 2)

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
    sparkline = []
    sparkline_start_date = None
    sparkline_end_date = None
    if rating_history.exists():
        for point in rating_history:
            rating_value = float(point.rating)
            height = int(max(min((rating_value / 5) * 100, 100), 0))
            sparkline.append({
                'date': point.recorded_at.strftime('%d/%m'),
                'rating': rating_value,
                'height': height,
            })
        sparkline_start_date = sparkline[0]['date']
        sparkline_end_date = sparkline[-1]['date']

    if rating_history.count() >= 2:
        first_rating = rating_history.first().rating
        last_rating = rating_history.last().rating
        if last_rating > first_rating:
            trend = 'up'
        elif last_rating < first_rating:
            trend = 'down'
        else:
            trend = 'stable'
    
    recent_reviews_headers = [
        {
            'label': 'Note',
            'key': 'rating',
            'centered': True,
        },
        {
            'label': 'Source',
            'key': 'source',
            'centered': True,
        },
        {
            'label': 'Commentaire',
            'key': 'comment',
            'searchable': True,
            'popover_if_long': True,
            'popover_threshold': 50,
        },
        {
            'label': 'Reçu le',
            'key': 'created_at',
            'centered': True,
        },
    ]

    context = {
        'etablissement': etablissement,
        'period': period,
        'total_reviews': total_reviews,
        'avg_rating': round(avg_rating, 2) if avg_rating else 0,
        'internal_count': internal_count,
        'google_count': google_count,
        'positive_reviews': positive_reviews,
        'neutral_reviews': neutral_reviews,
        'negative_reviews': negative_reviews,
        'comment_coverage': comment_coverage,
        'reviews_per_day': reviews_per_day,
        'rating_distribution': rating_distribution,
        'rating_distribution_rows': rating_distribution_rows,
        'recent_reviews': recent_reviews,
        'recent_reviews_data': recent_reviews_data,
        'recent_reviews_headers': recent_reviews_headers,
        'rating_history': rating_history,
        'trend': trend,
        'sparkline': sparkline,
        'sparkline_start_date': sparkline_start_date,
        'sparkline_end_date': sparkline_end_date,
        'has_reviews': total_reviews > 0,
        'reviews_with_comment': reviews_with_comment,
    }
    
    return starshield_render(request, "etablissement/overview.html", context=context, page_name="etablissement")
