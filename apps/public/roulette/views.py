import random
import string

from django.contrib.admin.sites import login_not_required
from django.http import JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.views.decorators.http import require_http_methods, require_POST

from apps.private.auths.models import Etablissement
from apps.public.reviews.utils import get_etablissement_by_identifier, get_valid_session_key, set_valid_session_key
from starshield.logger import logger

from .models import RouletteAnalytics, RoulettePrize, RouletteSpin


def generate_prize_code(etablissement: Etablissement) -> str:
    """Generate a unique alphanumeric prize code for an etablissement."""
    max_attempts = 100
    for _ in range(max_attempts):
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=9))
        if not RouletteSpin.objects.filter(prize_code=code).exists():
            return code
    raise ValueError("Failed to generate unique prize code")


def calculate_prize(etablissement: Etablissement) -> RoulettePrize | None:
    """Calculate which prize should be won based on probabilities."""
    prizes = etablissement.roulette_prizes.all()

    if not prizes.exists():
        return None

    # Calculate cumulative probabilities
    total_probability = sum(float(prize.probability) for prize in prizes)
    if total_probability != 100.0:
        logger.warning(f"Total probability for etablissement {etablissement.id} is {total_probability}%, not 100%")

    # Generate random number between 0 and 100
    random_value = random.uniform(0, 100)

    cumulative = 0
    for prize in prizes:
        cumulative += float(prize.probability)
        if random_value <= cumulative:
            return prize

    # Fallback to last prize (shouldn't happen if probabilities sum to 100)
    return prizes.last()


def get_last_spin_date(request, etablissement: Etablissement) -> timezone.datetime | None:
    """Get the last spin date from cookie."""
    cookie_name = f"roulette_last_spin_{etablissement.id}"
    cookie_value = request.COOKIES.get(cookie_name)

    if not cookie_value:
        return None

    try:
        return timezone.datetime.fromisoformat(cookie_value)
    except (ValueError, TypeError):
        return None


def can_spin(request, etablissement: Etablissement) -> tuple[bool, str]:
    """Check if user can spin the roulette."""
    if not etablissement.roulette_enabled:
        return False, "Roulette is not enabled for this establishment."

    last_spin = get_last_spin_date(request, etablissement)
    if last_spin:
        cooldown_days = etablissement.roulette_spin_cooldown_days
        days_since_spin = (timezone.now() - last_spin).days
        if days_since_spin < cooldown_days:
            days_remaining = cooldown_days - days_since_spin
            return False, f"You can spin again in {days_remaining} day(s)."

    # Timer validation is handled client-side
    # Backend just checks cooldown, client-side validates the 30-second timer
    return True, ""


@login_not_required
@require_http_methods(["GET"])
def roulette_view(request, identifier=None):
    """Main roulette page."""
    etablissement = get_etablissement_by_identifier(identifier)

    # Redirect to inactive page if establishment or roulette feature is inactive
    if not etablissement.active or not etablissement.roulette_enabled:
        return reverse("routing:feature_inactive", args=[identifier])

    # Track analytics
    analytics_key = f"roulette_viewed_{etablissement.id}"
    if not get_valid_session_key(request, analytics_key, valid_minutes=5):
        RouletteAnalytics.objects.create(
            etablissement=etablissement,
            type="roulette_viewed",
        )
        set_valid_session_key(request, analytics_key, True)

    # Check if user can spin
    can_spin_now, message = can_spin(request, etablissement)

    # Get prizes for wheel display
    prizes = etablissement.roulette_prizes.all()

    # Build review URL (simple, no return parameter)
    review_url = etablissement.new_reviews_uri

    context = {
        "etablissement": etablissement,
        "prizes": prizes,
        "can_spin": can_spin_now,
        "message": message,
        "review_url": review_url,
        "spin_url": reverse("roulette:spin", args=[identifier]),
    }

    return render(request, "roulette/wheel.html", context)


@login_not_required
@require_POST
def spin_roulette_view(request, identifier=None):
    """Handle roulette spin request."""
    etablissement = get_etablissement_by_identifier(identifier)

    if not etablissement.roulette_enabled:
        return JsonResponse({"error": "Roulette is not enabled."}, status=400)

    # Check cooldown (timer validation is handled client-side)
    last_spin = get_last_spin_date(request, etablissement)
    if last_spin:
        cooldown_days = etablissement.roulette_spin_cooldown_days
        days_since_spin = (timezone.now() - last_spin).days
        if days_since_spin < cooldown_days:
            days_remaining = cooldown_days - days_since_spin
            return JsonResponse({"error": f"You can spin again in {days_remaining} day(s)."}, status=400)

    # Track spin analytics
    analytics_key = f"roulette_spun_{etablissement.id}"
    if not get_valid_session_key(request, analytics_key, valid_minutes=1):
        RouletteAnalytics.objects.create(
            etablissement=etablissement,
            type="roulette_spun",
        )
        set_valid_session_key(request, analytics_key, True)

    # Calculate prize
    prize = calculate_prize(etablissement)

    if not prize:
        return JsonResponse({"error": "No prizes configured."}, status=400)

    # Handle result
    if prize.is_nothing_prize:
        # No prize won
        RouletteAnalytics.objects.create(
            etablissement=etablissement,
            type="no_prize",
        )

        response = JsonResponse(
            {
                "success": True,
                "prize": None,
                "prize_name": None,
                "prize_code": None,
                "message": "Thank you for trying!",
            }
        )
    else:
        # Prize won - generate code and save
        try:
            prize_code = generate_prize_code(etablissement)
            RouletteSpin.objects.create(
                etablissement=etablissement,
                prize=prize,
                prize_code=prize_code,
            )

            RouletteAnalytics.objects.create(
                etablissement=etablissement,
                type="prize_won",
            )

            response = JsonResponse(
                {
                    "success": True,
                    "prize": {
                        "id": prize.id,
                        "name": prize.name,
                        "icon": prize.icon,
                    },
                    "prize_name": prize.name,
                    "prize_code": prize_code,
                    "message": f"Congratulations! You won: {prize.name}",
                }
            )
        except Exception as e:
            logger.error(f"Error generating prize code: {e}", exc_info=True)
            return JsonResponse({"error": "Error processing prize. Please try again."}, status=500)

    # Set cookie for cooldown
    cookie_name = f"roulette_last_spin_{etablissement.id}"
    cookie_value = timezone.now().isoformat()
    max_age = etablissement.roulette_spin_cooldown_days * 24 * 60 * 60  # Convert days to seconds
    response.set_cookie(cookie_name, cookie_value, max_age=max_age)

    return response


@login_not_required
@require_http_methods(["GET", "POST"])
def verify_code_view(request, identifier=None, code=None):
    """Verify a prize code (public page, admin can mark as used)."""
    etablissement = get_etablissement_by_identifier(identifier)

    try:
        spin = RouletteSpin.objects.get(prize_code=code, etablissement=etablissement)
    except RouletteSpin.DoesNotExist:
        context = {
            "etablissement": etablissement,
            "code": code,
            "spin": None,
            "error": "Invalid code.",
        }
        return render(request, "roulette/verify.html", context)

    # Handle POST (mark as used - admin only)
    if request.method == "POST" and request.user.is_authenticated:
        if hasattr(request.user, "google_credential") and request.user.google_credential:
            user_etablissements = request.user.google_credential.etablissements.all()
            if spin.etablissement in user_etablissements:
                spin.is_used = True
                spin.save()
                context = {
                    "etablissement": etablissement,
                    "code": code,
                    "spin": spin,
                    "success": "Code marked as used.",
                }
                return render(request, "roulette/verify.html", context)

    context = {
        "etablissement": etablissement,
        "code": code,
        "spin": spin,
    }
    return render(request, "roulette/verify.html", context)
