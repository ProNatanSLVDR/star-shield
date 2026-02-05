import random
import string

from django.contrib.admin.sites import login_not_required
from django.http import Http404
from django.shortcuts import redirect, render
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
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
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


def is_in_cooldown(request, etablissement: Etablissement) -> bool:
    """Check if user is currently in cooldown period."""
    cookie_name = f"roulette_last_spin_{etablissement.id}"
    cookie_value = request.COOKIES.get(cookie_name)

    if not cookie_value:
        return False

    try:
        last_spin = timezone.datetime.fromisoformat(cookie_value)
        cooldown_days = etablissement.roulette_spin_cooldown_days
        days_since_spin = (timezone.now() - last_spin).days
        return days_since_spin < cooldown_days
    except (ValueError, TypeError):
        # Invalid cookie format - treat as not in cooldown
        return False


@login_not_required
@require_http_methods(["GET"])
def roulette_view(request, identifier=None):
    """Main roulette page."""
    etablissement = get_etablissement_by_identifier(identifier)

    # Redirect to inactive page if establishment or roulette feature is inactive
    if not etablissement.active or not etablissement.roulette_enabled:
        return redirect("routing:feature_inactive")

    # Check if user is in cooldown - redirect to cooldown page if so
    if is_in_cooldown(request, etablissement):
        return redirect(reverse("roulette:cooldown", args=[identifier]))

    # Track analytics
    analytics_key = f"roulette_viewed_{etablissement.id}"
    if not get_valid_session_key(request, analytics_key, valid_minutes=5):
        RouletteAnalytics.objects.create(
            etablissement=etablissement,
            type="roulette_viewed",
        )
        set_valid_session_key(request, analytics_key, True)

    # Check if user can spin
    can_spin_now = not is_in_cooldown(request, etablissement)

    # Build review URL
    review_url = etablissement.new_reviews_uri

    context = {
        "etablissement": etablissement,
        "can_spin": can_spin_now,
        "review_url": review_url,
        "spin_url": reverse("roulette:spin", args=[identifier]),
        "prizes": etablissement.roulette_prizes.all(),
    }

    return render(request, "roulette/wheel.html", context)


@login_not_required
@require_POST
def spin_roulette_view(request, identifier=None):
    """Handle roulette spin request - redirects to result page."""
    etablissement = get_etablissement_by_identifier(identifier)

    if not etablissement.roulette_enabled:
        return redirect("routing:feature_inactive")

    # Check cooldown
    if is_in_cooldown(request, etablissement):
        return redirect(reverse("roulette:cooldown", args=[identifier]))

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
        # No prizes configured - redirect to result page with no code
        return redirect(reverse("roulette:result", args=[identifier]))

    # Set cookie for cooldown
    cookie_name = f"roulette_last_spin_{etablissement.id}"
    cookie_value = timezone.now().isoformat()
    max_age = etablissement.roulette_spin_cooldown_days * 24 * 60 * 60  # Convert days to seconds

    # Handle result
    if prize.is_nothing_prize:
        # No prize won
        RouletteAnalytics.objects.create(
            etablissement=etablissement,
            type="no_prize",
        )
        response = redirect(reverse("roulette:result", args=[identifier]))
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

            response = redirect(reverse("roulette:result", args=[identifier, prize_code]))
        except Exception as e:
            logger.error(f"Error generating prize code: {e}", exc_info=True)
            # On error, redirect to no prize result
            response = redirect(reverse("roulette:result", args=[identifier]))

    # Set cookie on response
    response.set_cookie(cookie_name, cookie_value, max_age=max_age)
    return response


@login_not_required
@require_http_methods(["GET"])
def roulette_cooldown_view(request, identifier=None):
    """Display cooldown page when user has already spun recently."""
    etablissement = get_etablissement_by_identifier(identifier)

    # Redirect to inactive page if establishment or roulette feature is inactive
    if not etablissement.active or not etablissement.roulette_enabled:
        return redirect("routing:feature_inactive")

    # If user is not in cooldown, redirect to wheel page
    if not is_in_cooldown(request, etablissement):
        return redirect(reverse("roulette:wheel", args=[identifier]))

    context = {
        "etablissement": etablissement,
    }

    return render(request, "roulette/cooldown.html", context)


@login_not_required
@require_http_methods(["GET"])
def roulette_result_view(request, identifier=None, prize_code=None):
    """Display roulette result - prize won or nothing won."""
    etablissement = get_etablissement_by_identifier(identifier)

    if not etablissement.active or not etablissement.roulette_enabled:
        return redirect(reverse("routing:feature_inactive", args=[identifier]))

    # If prize_code provided, verify it exists and belongs to this etablissement
    spin = None
    if prize_code:
        try:
            spin = RouletteSpin.objects.get(prize_code=prize_code, etablissement=etablissement)
        except RouletteSpin.DoesNotExist:
            # Invalid code - treat as no prize
            prize_code = None

    prizes = etablissement.roulette_prizes.all()
    nothing_prize = prizes.filter(is_nothing_prize=True).first()
    stop_on_prize = spin.prize if spin else nothing_prize

    context = {
        "etablissement": etablissement,
        "prize_code": prize_code,
        "spin": spin,
        "prizes": prizes,
        "stop_on_prize": stop_on_prize,
    }

    return render(request, "roulette/result.html", context)


@login_not_required
@require_http_methods(["GET", "POST"])
def verify_code_view(request, identifier=None, code=None):
    """Verify a prize code (public page, user can mark as used)."""
    if not identifier:
        raise Http404("Etablissement identifier is required.")
    etablissement = get_etablissement_by_identifier(identifier)
    base_context = {
        "etablissement": etablissement,
        "identifier": identifier,
    }
    if not code:
        code_input = request.GET.get("code", "").strip()
        if code_input:
            return redirect(reverse("roulette:verify", args=[identifier, code_input]))

        context = {
            **base_context,
            "code": None,
            "spin": None,
        }
        return render(request, "roulette/verify.html", context)

    code = code.strip()
    spin = (
        RouletteSpin.objects.filter(prize_code__iexact=code, etablissement=etablissement)
        .select_related("prize")
        .first()
    )
    error = None

    if request.method == "POST" and request.POST.get("action") == "redeem":
        if not spin:
            error = "Code invalide ou introuvable."
        elif not spin.is_used:
            spin.is_used = True
            spin.save(update_fields=["is_used"])
            return redirect(reverse("roulette:verify", args=[identifier, spin.prize_code]))

    if not spin and not error:
        error = "Code invalide ou introuvable."

    context = {
        **base_context,
        "code": spin.prize_code if spin else code,
        "spin": spin,
        "error": error,
    }
    return render(request, "roulette/verify.html", context)
