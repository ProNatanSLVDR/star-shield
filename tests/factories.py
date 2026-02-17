import factory
from django.contrib.auth import get_user_model

from apps.private.auths.models import (
    Etablissement,
    GoogleCredentials,
    QRCode,
    QRCodeScan,
    RatingHistory,
    WeeklyPerformanceSummary,
)
from apps.private.payments.models import StripeSubscription
from apps.public.reviews.models import Review, ReviewAnalytics
from apps.public.roulette.models import RouletteAnalytics, RoulettePrize, RouletteSpin
from apps.tasks_api.models import TaskExecution

User = get_user_model()


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    email = factory.Sequence(lambda n: f"user{n}@example.com")
    password = factory.PostGenerationMethodCall("set_password", "testpass123")
    first_name = factory.Faker("first_name")
    last_name = factory.Faker("last_name")
    is_active = True


class GoogleCredentialsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = GoogleCredentials

    user = factory.SubFactory(UserFactory)
    is_valid = True
    has_invalid_grants = False
    google_account_email = factory.LazyAttribute(lambda o: o.user.email)
    token = "fake-token"
    refresh_token = "fake-refresh-token"
    token_uri = "https://oauth2.googleapis.com/token"
    client_id = "fake-client-id"
    client_secret = "fake-client-secret"
    scopes = "https://www.googleapis.com/auth/business.manage"


class EtablissementFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Etablissement

    google_credential = factory.SubFactory(GoogleCredentialsFactory)
    location_id = factory.Sequence(lambda n: f"locations/{n}")
    account_id = factory.Sequence(lambda n: f"accounts/{n}")
    title = factory.Sequence(lambda n: f"Etablissement {n}")
    website_uri = "https://example.com"
    maps_uri = "https://maps.google.com/?cid=123"
    new_reviews_uri = "https://search.google.com/local/writereview?placeid=123"
    active = True
    review_threshold = 4
    slug = factory.Sequence(lambda n: f"etab-{n}")


class QRCodeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = QRCode

    etablissement = factory.SubFactory(EtablissementFactory)
    name = factory.Sequence(lambda n: f"QR Code {n}")
    routing = "feedback"


class QRCodeScanFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = QRCodeScan

    qr_code = factory.SubFactory(QRCodeFactory)


class RatingHistoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RatingHistory

    etablissement = factory.SubFactory(EtablissementFactory)
    rating = 4.5
    total_reviews = 100


class ReviewFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Review

    etablissement = factory.SubFactory(EtablissementFactory)
    rating = 4
    comment = "Great service!"
    source = "internal"


class ReviewAnalyticsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ReviewAnalytics

    etablissement = factory.SubFactory(EtablissementFactory)
    type = "feedback_viewed"


class RoulettePrizeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RoulettePrize

    etablissement = factory.SubFactory(EtablissementFactory)
    name = factory.Sequence(lambda n: f"Prize {n}")
    icon = "fa-gift"
    probability = 25.00
    is_nothing_prize = False


class RouletteSpinFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RouletteSpin

    etablissement = factory.SubFactory(EtablissementFactory)
    prize = factory.SubFactory(RoulettePrizeFactory)
    prize_name = factory.LazyAttribute(lambda o: o.prize.name)
    prize_icon = factory.LazyAttribute(lambda o: o.prize.icon)
    prize_code = factory.Sequence(lambda n: f"CODE{n:04d}")
    is_used = False


class StripeSubscriptionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = StripeSubscription

    etablissement = factory.SubFactory(EtablissementFactory)
    subscription_id = factory.Sequence(lambda n: f"sub_{n}")
    status = "active"
    price_id = "price_test123"
    cancel_at_period_end = False


class TaskExecutionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = TaskExecution

    task_type = "fetch_reviews"
    etablissement = factory.SubFactory(EtablissementFactory)
    status = "pending"
    metadata = factory.LazyFunction(dict)


class WeeklyPerformanceSummaryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = WeeklyPerformanceSummary

    etablissement = factory.SubFactory(EtablissementFactory)
    week_start_date = factory.LazyFunction(lambda: __import__("datetime").date(2026, 2, 9))
    short_summary = "Résumé court"
    summary_text = "Rapport complet"
    advice_text = "Conseils"
    metrics_data = factory.LazyFunction(dict)


class RouletteAnalyticsFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = RouletteAnalytics

    etablissement = factory.SubFactory(EtablissementFactory)
    type = "roulette_viewed"
