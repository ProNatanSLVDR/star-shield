"""
Email service utility for sending HTML emails via Brevo API.

This module provides a simple interface for sending beautiful HTML emails
using Django templates and the Brevo email backend.
"""

import logging
from typing import Optional

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)


def send_email(
    to: list[str] | str,
    subject: str,
    template_name: str = "emails/basic_mail.html",
    context: Optional[dict] = None,
    from_email: Optional[str] = None,
    fail_silently: bool = False,
) -> None:
    """
    Send an HTML email using a Django template and Brevo backend.

    Args:
        to: Recipient email address(es). Can be a single string or a list of strings.
        subject: Email subject line.
        template_name: Path to the Django template to use (default: "emails/basic_mail.html").
        context: Dictionary of context variables to pass to the template.
        from_email: Sender email address. If None, uses DEFAULT_FROM_EMAIL from settings.
        fail_silently: If True, log errors but don't raise exceptions.

    Raises:
        Exception: If email sending fails and fail_silently is False.

    Example:
        # Simple email using base template
        send_email(
            to="user@example.com",
            subject="Welcome to StarShield",
            context={"user": "John", "text": "Welcome to our platform!"}
        )

        # Extended template email
        send_email(
            to=["user@example.com"],
            subject="Custom Email",
            template_name="emails/custom_email.html",
            context={"user": "Jane", "custom_data": "..."}
        )
    """
    if context is None:
        context = {}

    # Normalize recipient to list
    if isinstance(to, str):
        recipient_list = [to]
    else:
        recipient_list = to

    if not recipient_list:
        error_msg = "No recipient email addresses provided"
        logger.error(error_msg)
        if not fail_silently:
            raise ValueError(error_msg)
        return

    # Get sender email from settings if not provided
    if from_email is None:
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None)
        if not from_email:
            from_email = getattr(settings, "BREVO_SENDER_EMAIL", None)

    if not from_email:
        error_msg = "No sender email configured. Set DEFAULT_FROM_EMAIL or BREVO_SENDER_EMAIL in settings."
        logger.error(error_msg)
        if not fail_silently:
            raise ValueError(error_msg)
        return

    try:
        # Render HTML template
        html_content = render_to_string(template_name, context)

        # Create email message with HTML content
        message = EmailMultiAlternatives(
            subject=subject,
            body="",  # Plain text version (empty, HTML only)
            from_email=from_email,
            to=recipient_list,
        )

        # Attach HTML content
        message.attach_alternative(html_content, "text/html")

        # Send email (uses Brevo backend configured in settings)
        message.send(fail_silently=fail_silently)

        logger.info(f"Email sent successfully to {recipient_list} with subject: {subject}")

    except Exception as e:
        error_msg = f"Failed to send email to {recipient_list}: {str(e)}"
        logger.error(error_msg, exc_info=True)
        if not fail_silently:
            raise Exception(error_msg) from e
