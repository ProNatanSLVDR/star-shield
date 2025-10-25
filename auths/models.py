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

    def create_etablissement_from_location(self, account_id, location_id):
        """
        Crée ou met à jour un seul établissement à partir d'un location_id Google My Business.
        """
        creds = self.get_valid_credentials()
        if not creds:
            return False

        # Services API
        locations_service = build("mybusinessbusinessinformation", "v1", credentials=creds)

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
        creds = self.get_valid_credentials()
        if not creds:
            return False

        accounts_service = build("mybusinessaccountmanagement", "v1", credentials=creds)
        locations_service = build("mybusinessbusinessinformation", "v1", credentials=creds)

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

    def get_public_identifier(self) -> str:
        """Return the best available identifier for public URLs."""
        return self.slug or str(self.uuid)



    def update_reviews(self):
        """Populate reviews from Google My Business until finding an already existing review."""
        from apps.reviews.models import Review
        
        creds = self.google_credential.get_valid_credentials()
        if not creds:
            return False

        try:
            service = build("mybusiness", "v4", credentials=creds)
        except Exception as e:
            print(f"Error building reviews service for {self.title}: {e}")
            return False


        count_added = 0
        next_page_token = None
        found_existing = False

        while not found_existing:
            try:
                reviews_data = service.accounts().locations().reviews().list(
                    name=self.location_id,
                    pageSize=100,
                    pageToken=next_page_token
                ).execute()
            except Exception as e:
                print(f"Error fetching reviews for {self.title}: {e}")
                break

            reviews = reviews_data.get("reviews", [])
            
            for review in reviews:
                # Create unique identifier to check if review already exists
                review_comment = review.get("comment", "")
                review_rating = review.get("rating")

                # Try to get or create review
                try:
                    review_obj, created = Review.objects.get_or_create(
                        etablissement=self,
                        comment=review_comment,
                        rating=review_rating,
                        source='google'
                    )
                    
                    if created:
                        count_added += 1
                    else:
                        # Found an existing review, stop here
                        found_existing = True
                        break
                except Exception as e:
                    print(f"Error creating review: {e}")
                    continue

            # Check for next page
            next_page_token = reviews_data.get("nextPageToken")
            if not next_page_token or found_existing:
                break

        return count_added


class RatingHistory(models.Model):
    etablissement = models.ForeignKey(Etablissement, on_delete=models.CASCADE, related_name='rating_history')

    rating = models.DecimalField(max_digits=3, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(5)])
    
    total_reviews = models.PositiveIntegerField(default=0)

    google_rating = models.DecimalField(max_digits=3, decimal_places=2, validators=[MinValueValidator(0), MaxValueValidator(5)], null=True, blank=True)
    google_review_count = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    

    def __str__(self):
        return f"Rating {self.rating}★ for {self.etablissement.title} on {self.created_at.strftime('%Y-%m-%d')}"

