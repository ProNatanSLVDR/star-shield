from __future__ import annotations

import logging
import uuid

from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models.signals import pre_save
from django.dispatch import receiver
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from . import choices

logger = logging.getLogger(__name__)


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
    profile_picture = models.ImageField(upload_to="profile_pictures/", blank=True, null=True)

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
    has_invalid_grants = models.BooleanField(default=False)

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
                logger.error(f"Google OAuth token refresh failed for user {self.user_id}: {e}")
                self.is_valid = False
                self.save()
                raise

            self.token = creds.token
            self.refresh_token = creds.refresh_token or self.refresh_token
            self.save()

        return creds

    def get_reviews_service(self):
        try:
            credentials = self.get_valid_credentials()
            reviews_service = build(
                "mybusiness",
                "v4",
                static_discovery=False,
                discoveryServiceUrl="https://developers.google.com/my-business/samples/mybusiness_google_rest_v4p9.json",
                credentials=credentials,
            )
            return reviews_service
        except Exception as e:
            logger.error(f"Error building reviews service for user {self.user_id}: {e}", exc_info=True)
            return None

    def get_locations_service(self):
        try:
            credentials = self.get_valid_credentials()
            locations_service = build(
                "mybusinessbusinessinformation",
                "v1",
                credentials=credentials,
            )
            return locations_service
        except Exception as e:
            logger.error(f"Error building locations service for user {self.user_id}: {e}", exc_info=True)
            return None

    def get_accounts_service(self):
        try:
            credentials = self.get_valid_credentials()
            accounts_service = build(
                "mybusinessaccountmanagement",
                "v1",
                credentials=credentials,
            )
            return accounts_service
        except Exception as e:
            logger.error(f"Error building accounts service for user {self.user_id}: {e}", exc_info=True)
            return None

    def create_etablissement_from_location(self, account_id, location_id):
        """
        Crée ou met à jour un seul établissement à partir d'un location_id Google My Business.
        """

        # Services API
        locations_service = self.get_locations_service()

        if locations_service is None:
            logger.error(f"Failed to initialize locations service for user {self.user_id}")
            return None

        try:
            # Récupération des informations de la location
            location = locations_service.locations().get(name=location_id, readMask="name,title,metadata,websiteUri").execute()

            metadata = location.get("metadata", {})
        except Exception as e:
            logger.error(f"Erreur lors de la création de l'établissement pour {location_id} (user {self.user_id}): {e}", exc_info=True)
            return None

        try:
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
            logger.error(f"Erreur lors de la création de l'établissement pour {location_id} (user {self.user_id}): {e}", exc_info=True)
            return None

    def list_available_locations(self):
        accounts_service = self.get_accounts_service()
        locations_service = self.get_locations_service()

        if accounts_service is None or locations_service is None:
            logger.error(f"Failed to initialize Google services for user {self.user_id}")
            return []

        available_locations = []
        try:
            accounts = accounts_service.accounts().list().execute()
        except Exception as e:
            logger.error(f"Error fetching accounts for user {self.user_id}: {e}", exc_info=True)
            return []

        for account in accounts.get("accounts", []):
            next_page_token = None
            while True:
                # Récupération des locations
                locations = (
                    locations_service.accounts()
                    .locations()
                    .list(
                        parent=account["name"],
                        readMask="name,title",
                        pageToken=next_page_token,
                    )
                    .execute()
                )

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
        validators=[MinValueValidator(3), MaxValueValidator(5)],
        help_text="Note minimale pour redirection Google.",
    )
    target_rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
        help_text="Note cible que vous souhaitez atteindre à l'avenir.",
    )
    review_page_label = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Nom pour l'établissement sur la page de feedback.",
    )
    review_page_text = models.CharField(
        max_length=255,
        default="Votre avis nous aide à offrir un meilleur service !",
        help_text="Texte à afficher sur la page de feedback.",
    )
    review_accent_color = models.CharField(
        max_length=7,
        default="#0066ff",
        help_text="Couleur d'accent pour la page de feedback (format hexadécimal).",
    )
    review_show_etablissement_pill = models.BooleanField(
        default=True,
        help_text="Afficher ou masquer le badge avec le nom de l'établissement.",
    )

    # QR code settings
    qr_fill_color = models.CharField(
        max_length=7,
        default="#000000",
        help_text="Couleur de remplissage du QR code (format hexadécimal).",
    )
    qr_fill_color_secondary = models.CharField(
        max_length=7,
        default="#000000",
        help_text="Couleur secondaire pour les dégradés (format hexadécimal).",
    )
    qr_background_color = models.CharField(
        max_length=7,
        default="#FFFFFF",
        help_text="Couleur de fond du QR code (format hexadécimal).",
    )
    qr_style = models.CharField(
        max_length=20,
        choices=choices.QR_STYLE_CHOICES,
        default="square",
        help_text="Style des modules du QR code.",
    )
    qr_color_mask = models.CharField(
        max_length=20,
        choices=choices.QR_COLOR_MASK_CHOICES,
        default="solid",
        help_text="Style de masque de couleur pour le QR code.",
    )
    qr_logo = models.ImageField(
        upload_to="qr_logos/",
        blank=True,
        null=True,
        help_text="Logo à afficher au centre du QR code.",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_reviews_update = models.DateTimeField(blank=True, null=True)

    def __str__(self):
        return self.title


class RatingHistory(models.Model):
    etablissement = models.ForeignKey(Etablissement, on_delete=models.CASCADE, related_name="rating_history")

    rating = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
    )
    total_reviews = models.PositiveIntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Rating {self.rating}★ for {self.etablissement.title} on {self.created_at.strftime('%Y-%m-%d')}"


@receiver(pre_save, sender=User)
def delete_old_profile_picture(sender, instance, **kwargs):
    """
    Signal handler to delete old profile picture from GCP Storage when user uploads a new one.
    """
    if instance.pk:
        try:
            old_instance = User.objects.get(pk=instance.pk)
            if old_instance.profile_picture and old_instance.profile_picture != instance.profile_picture:
                if old_instance.profile_picture.name:
                    try:
                        old_instance.profile_picture.delete(save=False)
                    except Exception as e:
                        logger.warning(f"Failed to delete old profile picture for user {instance.pk}: {e}")
        except User.DoesNotExist:
            pass
        except Exception as e:
            logger.error(
                f"Error deleting old profile picture for user {instance.pk}: {e}",
                exc_info=True,
            )


@receiver(pre_save, sender=Etablissement)
def delete_old_qr_logo(sender, instance, **kwargs):
    """
    Signal handler to delete old QR logo from storage when a new one is uploaded.
    """
    if instance.pk:
        try:
            old_instance = Etablissement.objects.get(pk=instance.pk)
            if old_instance.qr_logo and old_instance.qr_logo != instance.qr_logo:
                if old_instance.qr_logo.name:
                    try:
                        old_instance.qr_logo.delete(save=False)
                    except Exception as e:
                        logger.warning(f"Failed to delete old QR logo for etablissement {instance.pk}: {e}")
        except Etablissement.DoesNotExist:
            pass
        except Exception as e:
            logger.error(
                f"Error deleting old QR logo for etablissement {instance.pk}: {e}",
                exc_info=True,
            )
