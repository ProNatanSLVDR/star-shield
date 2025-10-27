from __future__ import annotations
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
import uuid
from google.oauth2.credentials import Credentials
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from django.core.validators import MaxValueValidator, MinValueValidator
from django.utils.translation import gettext_lazy as _
from apps.reviews.utils import google_stars_to_number

class UserManager(BaseUserManager):
    def _create_user(self, email: str, password: str | None, **extra_fields):
        if not email:
            raise ValueError("An email address is required.")

        normalized_email = self.normalize_email(email).lower()
        user = self.model(email=normalized_email, **extra_fields)

        if password and password.strip():
            user.set_password(password)
        else:
            user.set_unusable_password()

        user.save(using=self._db)
        return user

    def create_user(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", False)
        extra_fields.setdefault("is_superuser", False)
        extra_fields.setdefault("is_active", True)
        superuser = self._create_user(email, password, **extra_fields)

        try:
            # Import locally to avoid import cycles during migrations.
            from allauth.account.models import EmailAddress  # pylint: disable=import-error

            EmailAddress.objects.update_or_create(
                user=superuser,
                email=superuser.email,
                defaults={"verified": True, "primary": True},
            )
        except Exception as exc:  # pragma: no cover - defensive guard
            raise ValueError("Failed to auto-verify the superuser email address.") from exc

        return superuser

    def create_superuser(self, email: str, password: str | None = None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("is_active", True)

        if extra_fields.get("is_staff") is not True:
            raise ValueError("Superuser must have is_staff=True.")

        if extra_fields.get("is_superuser") is not True:
            raise ValueError("Superuser must have is_superuser=True.")

        if not password or not password.strip():
            raise ValueError("Superuser must have a password.")

        return self._create_user(email, password, **extra_fields)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)

    # Infos Personnelles
    first_name = models.CharField(max_length=150, blank=True)
    last_name = models.CharField(max_length=150, blank=True)

    # Misc
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS: list[str] = []

    def __str__(self) -> str:
        if self.first_name or self.last_name:
            return f"{self.first_name} {self.last_name}".strip()
        return self.email



# Google GMB
class GoogleCredentials(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="google_credential")

    is_valid = models.BooleanField(default=False)

    token = models.TextField()
    refresh_token = models.TextField(blank=True, null=True)
    token_uri = models.TextField()
    client_id = models.TextField()
    client_secret = models.TextField()
    scopes = models.TextField()

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    def get_valid_credentials(self) -> Credentials:
        creds = Credentials(
            token=self.token,
            refresh_token=self.refresh_token,
            token_uri=self.token_uri,
            client_id=self.client_id,
            client_secret=self.client_secret,
            scopes=self.scopes.split(),
        )
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError as e:
                print("Token revoked:", e)
                self.is_valid = False
                self.save()
                return False

            self.token = creds.token
            self.refresh_token = creds.refresh_token or self.refresh_token
            self.save()

        return creds


    def get_reviews_service(self):

        try:
            reviews_service = build(
                "mybusiness", 
                "v4", 
                static_discovery=False,
                discoveryServiceUrl='https://developers.google.com/my-business/samples/mybusiness_google_rest_v4p9.json',
                credentials=self.get_valid_credentials()
            )
            return reviews_service
        except Exception as e:
            print(f"Error building reviews service: {e}")
            return False

    def get_locations_service(self):
        try:
            locations_service = build("mybusinessbusinessinformation", "v1", credentials=self.get_valid_credentials())
            return locations_service
        except Exception as e:
            print(f"Error building locations service: {e}")
            return False

    def get_accounts_service(self):
        try:
            accounts_service = build("mybusinessaccountmanagement", "v1", credentials=self.get_valid_credentials())
            return accounts_service
        except Exception as e:
            print(f"Error building accounts service: {e}")
            return False


    def create_etablissement_from_location(self, account_id, location_id):
        """
        Crée ou met à jour un seul établissement à partir d'un location_id Google My Business.
        """

        # Services API
        locations_service = self.get_locations_service()

        try:
            # Récupération des informations de la location
            location = locations_service.locations().get(
                name=location_id,
                readMask="name,title,metadata,websiteUri"
            ).execute()

            metadata = location.get("metadata", {})
            
            # Création ou mise à jour de l'établissement
            etablissement, created = Etablissement.objects.update_or_create(
                google_credential=self,
                location_id=location["name"],
                account_id=account_id,
                defaults={
                    "title": location.get("title"),
                    "website_uri": location.get("websiteUri"),
                    "maps_uri": metadata.get("mapsUri"),
                    "new_reviews_uri": f"https://search.google.com/local/writereview?placeid={metadata.get('placeId')}",
                },
            )

            return etablissement

        except Exception as e:
            # Gestion d'erreur simple (peut être remplacée par du logging)
            print(f"Erreur lors de la création de l'établissement pour {location_id}: {e}")
            return None

    def list_available_locations(self):
        accounts_service = self.get_accounts_service()
        locations_service = self.get_locations_service()

        available_locations = []
        
        try:
            accounts = accounts_service.accounts().list().execute()
        except Exception:
            # If we can't list accounts, return empty
            return []
            
        for account in accounts.get("accounts", []):

            next_page_token = None
            while True:
                # Récupération des locations
                locations = locations_service.accounts().locations().list(
                    parent=account["name"],
                    readMask="name,title",
                    pageToken=next_page_token
                ).execute()

                available_locations.extend(locations.get("locations", []))

                next_page_token = locations.get("nextPageToken")
                if not next_page_token:
                    break

        for location in available_locations:
            location["account_id"] = account["name"]
            if Etablissement.objects.filter(location_id=location["name"], account_id=account["name"]).exists():
                location["exists"] = True
            else:
                location["exists"] = False
        
        return available_locations




# Etablissement
class Etablissement(models.Model):
    google_credential = models.ForeignKey("GoogleCredentials", on_delete=models.CASCADE, related_name="etablissements")

    location_id = models.CharField(max_length=255)
    account_id = models.CharField(max_length=255)

    title = models.CharField(max_length=255)
    website_uri = models.URLField(max_length=255, blank=True, null=True)
    maps_uri = models.URLField(max_length=255, blank=True, null=True)
    new_reviews_uri = models.URLField(max_length=255, blank=True, null=True)

    # access
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True, null=True)


    # settings
    review_threshold = models.PositiveSmallIntegerField(
        default=4,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Minimum rating that triggers a Google review redirect."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title


    def update_data(self, force_import=False):

        from apps.reviews.models import Review

        reviews_service = self.google_credential.get_reviews_service()

        print("start updating data for", self.title)

        continue_import = True
        import_count = 0
        next_page_token = None
        first_iteration = True

        # si force_import est True, on importe toutes les reviews, même si elles existent déjà
        # sinon, on importe uniquement les reviews qui n'existent pas encore
        while continue_import is True:

            # récupération des reviews
            try:
                reviews_data = reviews_service.accounts().locations().reviews().list(
                    parent=f"{self.account_id}/{self.location_id}",
                    pageSize=100,
                    pageToken=next_page_token
                ).execute()
            except Exception as e:
                print(f"Error fetching reviews for {self.title}: {e}")
                break
            
            # on crée l'historique des notes la première fois
            if first_iteration:
                first_iteration = False

                RatingHistory.objects.create(
                    etablissement=self,
                    rating=reviews_data.get("averageRating", 0),
                    total_reviews=reviews_data.get("totalReviewCount", 0),
                )

            # on importe les reviews
            reviews = reviews_data.get("reviews", [])
            for review in reviews:

                # on importe la review
                try:
                    new_review, created = Review.objects.update_or_create(
                        etablissement=self,
                        source='google',
                        google_review_id=review.get("reviewId"),

                        # les infos suivantes n'identifient pas un review unique, on les met à jour si elles changent
                        defaults={
                            'comment': review.get("comment", ""),
                            'rating': google_stars_to_number(review.get("starRating")),
                            'google_reviewer_data': review.get("reviewer"),
                            'writen_at': review.get("createTime"),
                        },
                    )
                    import_count += 1
                    print(f"imported {import_count} reviews")

                    # condition pour stopper l'importation
                    if force_import is False:
                        if created is False:
                            continue_import = False
                            break
                except Exception as e:
                    print(f"Error creating review: {e}")
                    continue

            # Check si y'a une page suivante
            next_page_token = reviews_data.get("nextPageToken", None)
            if next_page_token is None or continue_import is False:
                break


class RatingHistory(models.Model):
    etablissement = models.ForeignKey(Etablissement, on_delete=models.CASCADE, related_name='rating_history')

    rating = models.DecimalField(max_digits=3, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(5)])
    total_reviews = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    

    def __str__(self):
        return f"Rating {self.rating}★ for {self.etablissement.title} on {self.created_at.strftime('%Y-%m-%d')}"

