"""
Django Ninja authentication for bearer token validation.
"""

import logging
from ninja.security import HttpBearer
from django.conf import settings

logger = logging.getLogger(__name__)


class BearerTokenAuth(HttpBearer):
    """
    Bearer token authentication for Django Ninja API.
    
    Validates the Authorization: Bearer <token> header against
    the token configured in settings.TASKS_API_AUTH_TOKEN.
    
    If no token is configured in settings, authentication is skipped
    (development mode only).
    """

    def authenticate(self, request, token):
        """
        Authenticate the request using the bearer token.
        
        Args:
            request: The HTTP request object
            token: The token extracted from the Authorization header
            
        Returns:
            The token if authentication succeeds, None otherwise
        """
        auth_token = settings.TASKS_API_AUTH_TOKEN
        
        # If no token is configured, skip auth (development only)
        if not auth_token:
            return token
        
        # Validate the token matches the configured token
        if token == auth_token:
            return token
        
        # Log warning for invalid token attempts
        logger.warning(
            f"Invalid auth token in request from {request.META.get('REMOTE_ADDR')}"
        )
        return None

