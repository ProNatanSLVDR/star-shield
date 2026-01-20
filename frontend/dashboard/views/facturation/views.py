from django.contrib.auth.decorators import login_required
from django.conf import settings
from frontend.dashboard.render import starshield_render


@login_required
def facturation_view(request):
    """
    Display billing/facturation page with subscription information.
    Only reads from existing database records - no Stripe API calls.
    Shows aggregated subscription data by price_id.
    """
    user = request.user

    # Get active établissements count
    active_etablissements_count = 0
    plan_breakdown = {}  # {price_id: count}

    if hasattr(user, "google_credential"):
        etablissements = user.google_credential.etablissements.all()
        active_etablissements_count = etablissements.filter(active=True).count()

        # Aggregate subscriptions by price_id
        for etablissement in etablissements:
            subscriptions = etablissement.stripe_subscription.filter(status="active")
            for subscription in subscriptions:
                if subscription.price_id:
                    if subscription.price_id not in plan_breakdown:
                        plan_breakdown[subscription.price_id] = 0
                    plan_breakdown[subscription.price_id] += 1

    # Get monthly, trimestrial, and yearly price IDs from settings
    monthly_price_id = settings.STRIPE_PRODUCTS.get("basic_subscription", {}).get("monthly")
    trimestrial_price_id = settings.STRIPE_PRODUCTS.get("basic_subscription", {}).get("trimestrial")
    yearly_price_id = settings.STRIPE_PRODUCTS.get("basic_subscription", {}).get("yearly")

    # Categorize plan breakdown into monthly, trimestrial, and yearly counts
    monthly_count = 0
    trimestrial_count = 0
    yearly_count = 0

    for price_id, count in plan_breakdown.items():
        if price_id == monthly_price_id:
            monthly_count += count
        elif price_id == trimestrial_price_id:
            trimestrial_count += count
        elif price_id == yearly_price_id:
            yearly_count += count

    context = {
        "active_etablissements_count": active_etablissements_count,
        "monthly_count": monthly_count,
        "trimestrial_count": trimestrial_count,
        "yearly_count": yearly_count,
    }

    return starshield_render(
        request,
        "facturation/index.html",
        context=context,
        page_name="facturation",
    )
