import uuid

from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from auths.models import User
from google.oauth2.credentials import Credentials
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from googleapiclient.discovery import build

class GoogleCredentials(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="google_credentials")

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

    def get_gmb_accounts(self):
        service = build('mybusinessbusinessinformation', 'v1', credentials=self.get_valid_credentials())
        response = service.accounts().locations().list().execute()
        return response




# Etablissement
class Etablissement(models.Model):
    name = models.CharField(max_length=255)

    # Google GMB
    google_credentials = models.ForeignKey("GoogleCredentials", on_delete=models.CASCADE)
    google_business_manager_account_id = models.CharField(max_length=255)

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True, null=True)
    review_threshold = models.PositiveSmallIntegerField(
        default=4,
        validators=[MinValueValidator(1), MaxValueValidator(5)],
        help_text="Minimum rating that triggers a Google review redirect."
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def get_public_identifier(self) -> str:
        """Return the best available identifier for public URLs."""
        return self.slug or str(self.uuid)

    def get_google_review_url(self) -> str:
        """Temporary stub for the Google review URL."""
        # TODO: Replace with actual Google review URL fetched from the connected GMB account.
        return "https://maps.google.com"



class Review(models.Model):
    etablissement = models.ForeignKey("Etablissement", on_delete=models.CASCADE)

    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Review {self.rating}★ for {self.etablissement}"