"""
Custom Django Allauth adapter to use StarShield email styling.

This adapter overrides the default email rendering to use the custom
basic_mail.html template with StarShield branding.
"""

import logging
from typing import Any

from allauth.account.adapter import DefaultAccountAdapter
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.safestring import mark_safe

logger = logging.getLogger(__name__)


class CustomAccountAdapter(DefaultAccountAdapter):
    """
    Custom account adapter that renders emails using StarShield's custom template.
    """

    def render_mail(
        self, template_prefix: str, email: str, context: dict[str, Any], **kwargs: Any
    ) -> EmailMultiAlternatives:
        """
        Render email using custom StarShield template.

        Args:
            template_prefix: Template prefix (e.g., 'account/email/email_confirmation')
            email: Email address of recipient
            context: Context variables passed by Allauth

        Returns:
            EmailMultiAlternatives object with HTML content
        """
        # Extract user from context
        user = context.get("user")
        user_display = ""
        if user:
            # Get user display name (email if no name available)
            if hasattr(user, "get_full_name") and user.get_full_name():
                user_display = user.get_full_name()
            elif hasattr(user, "email"):
                user_display = user.email
            elif isinstance(user, str):
                user_display = user
            else:
                user_display = email

        # Map Allauth context to custom template format
        custom_context = {
            "user": user_display,
            "text": "",
            "text2": "",
        }

        # Determine email type and format content accordingly
        if "email_confirmation" in template_prefix:
            # Email verification
            code = context.get("code", "")
            activate_url = context.get("activate_url", "")

            if code:
                # Code-based verification
                custom_context["text"] = (
                    "Merci de vous être inscrit sur StarShield. "
                    "Pour finaliser votre inscription, veuillez utiliser le code de vérification suivant :"
                )
                custom_context["text2"] = mark_safe(f"<strong style='font-size: 24px; color: #0b6efd;'>{code}</strong>")
            elif activate_url:
                # Link-based verification
                custom_context["text"] = (
                    "Merci de vous être inscrit sur StarShield. "
                    "Pour finaliser votre inscription, veuillez cliquer sur le lien suivant :"
                )
                custom_context["text2"] = mark_safe(
                    f'<a href="{activate_url}" style="color: #0b6efd; text-decoration: none;">{activate_url}</a>'
                )
            else:
                custom_context["text"] = (
                    "Merci de vous être inscrit sur StarShield. "
                    "Veuillez vérifier votre adresse e-mail pour finaliser votre inscription."
                )

        elif "password_reset" in template_prefix:
            # Password reset
            password_reset_url = context.get("password_reset_url", "")

            if password_reset_url:
                custom_context["text"] = (
                    "Vous avez demandé la réinitialisation de votre mot de passe sur StarShield. "
                    "Cliquez sur le lien suivant pour créer un nouveau mot de passe :"
                )
                custom_context["text2"] = mark_safe(
                    f'<a href="{password_reset_url}" style="color: #0b6efd; text-decoration: none;">Réinitialiser mon mot de passe</a>'
                )
            else:
                custom_context["text"] = (
                    "Vous avez demandé la réinitialisation de votre mot de passe sur StarShield. "
                    "Veuillez suivre les instructions dans cet email."
                )

        elif "email_change" in template_prefix:
            # Email change confirmation
            new_email = context.get("new_email", "")
            activate_url = context.get("activate_url", "")

            if activate_url:
                custom_context["text"] = (
                    f"Vous avez demandé de changer votre adresse e-mail pour {new_email}. "
                    "Cliquez sur le lien suivant pour confirmer ce changement :"
                )
                custom_context["text2"] = mark_safe(
                    f'<a href="{activate_url}" style="color: #0b6efd; text-decoration: none;">Confirmer le changement d\'e-mail</a>'
                )
            else:
                custom_context["text"] = (
                    f"Vous avez demandé de changer votre adresse e-mail pour {new_email}. "
                    "Veuillez suivre les instructions dans cet email."
                )

        elif "password_set" in template_prefix:
            # Password set (for social accounts)
            password_set_url = context.get("password_set_url", "")

            if password_set_url:
                custom_context["text"] = (
                    "Pour sécuriser votre compte StarShield, veuillez définir un mot de passe. "
                    "Cliquez sur le lien suivant :"
                )
                custom_context["text2"] = mark_safe(
                    f'<a href="{password_set_url}" style="color: #0b6efd; text-decoration: none;">Définir mon mot de passe</a>'
                )
            else:
                custom_context["text"] = "Pour sécuriser votre compte StarShield, veuillez définir un mot de passe."

        else:
            # Generic fallback - try to extract message from context
            message = context.get("message", "")
            if message:
                custom_context["text"] = str(message)
            else:
                custom_context["text"] = "Vous avez reçu cet email de StarShield."

        # Render using custom template
        try:
            # First, get the default email message to extract subject and other metadata
            default_msg = super().render_mail(template_prefix, email, context, **kwargs)

            # Render custom HTML content
            html_content = render_to_string("emails/basic_mail.html", custom_context)

            # Create new EmailMultiAlternatives with custom HTML
            msg = EmailMultiAlternatives(
                subject=default_msg.subject,
                body="",  # Plain text version (empty, HTML only)
                from_email=default_msg.from_email or self.get_from_email(),
                to=default_msg.to,
            )

            # Copy any additional recipients
            if hasattr(default_msg, "cc") and default_msg.cc:
                msg.cc = default_msg.cc
            if hasattr(default_msg, "bcc") and default_msg.bcc:
                msg.bcc = default_msg.bcc

            # Attach HTML content
            msg.attach_alternative(html_content, "text/html")

            return msg
        except Exception as e:
            logger.error(f"Failed to render custom email template: {e}", exc_info=True)
            # Fallback to default Allauth rendering
            return super().render_mail(template_prefix, email, context, **kwargs)
