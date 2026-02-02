"""
Brevo (formerly Sendinblue) email backend for Django.

This backend sends emails through Brevo's Transactional Email API.
"""

import base64
from typing import Any

import brevo_python
from brevo_python.rest import ApiException
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend
from django.core.mail.message import EmailMessage

from starshield.logger import logger


class BrevoEmailBackend(BaseEmailBackend):
    """
    Email backend that sends emails via Brevo API.
    """

    def __init__(self, fail_silently: bool = False, **kwargs: Any) -> None:
        super().__init__(fail_silently=fail_silently, **kwargs)
        self.api_key = getattr(settings, "BREVO_API_KEY", "")
        self.sender_email = getattr(settings, "BREVO_SENDER_EMAIL", "")
        self.sender_name = getattr(settings, "BREVO_SENDER_NAME", "StarShield")

        if not self.api_key:
            logger.warning("BREVO_API_KEY is not set. Emails will not be sent.")

        # Initialize Brevo API client
        self._api_instance = None
        if self.api_key:
            try:
                configuration = brevo_python.Configuration()
                configuration.api_key["api-key"] = self.api_key
                api_client = brevo_python.ApiClient(configuration)
                self._api_instance = brevo_python.TransactionalEmailsApi(api_client)
            except Exception as e:
                logger.error(f"Failed to initialize Brevo API client: {e}")
                if not fail_silently:
                    raise

    def send_messages(self, email_messages: list[EmailMessage]) -> int:
        """
        Send one or more EmailMessage objects and return the number of emails sent.

        Args:
            email_messages: List of EmailMessage objects to send

        Returns:
            Number of emails successfully sent
        """
        if not email_messages:
            return 0

        if not self.api_key:
            if not self.fail_silently:
                msg = "BREVO_API_KEY is not configured"
                raise ValueError(msg)
            logger.warning("BREVO_API_KEY not set, skipping email send")
            return 0

        if not self._api_instance:
            if not self.fail_silently:
                msg = "Brevo API client not initialized"
                raise ValueError(msg)
            logger.warning("Brevo API client not initialized, skipping email send")
            return 0

        num_sent = 0

        try:
            for message in email_messages:
                self._send_single_message(message)
                num_sent += 1
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            if not self.fail_silently:
                raise

        return num_sent

    def _send_single_message(self, message: EmailMessage) -> None:
        """
        Send a single EmailMessage via Brevo API.

        Args:
            message: EmailMessage object to send
        """
        # Prepare sender
        from_email = message.from_email or self.sender_email
        from_name = self.sender_name

        # Parse sender email and name if format is "Name <email@example.com>"
        if "<" in from_email and ">" in from_email:
            parts = from_email.rsplit("<", 1)
            from_name = parts[0].strip().strip('"').strip("'")
            from_email = parts[1].rstrip(">").strip()

        # Prepare recipients
        to_recipients = [{"email": email} for email in message.to]
        cc_recipients = [{"email": email} for email in (message.cc or [])]
        bcc_recipients = [{"email": email} for email in (message.bcc or [])]

        # Prepare email content
        send_smtp_email = brevo_python.SendSmtpEmail(
            sender={"name": from_name, "email": from_email},
            to=to_recipients,
            subject=message.subject,
        )

        # Add CC and BCC if present
        if cc_recipients:
            send_smtp_email.cc = cc_recipients
        if bcc_recipients:
            send_smtp_email.bcc = bcc_recipients

        # Set email content (HTML preferred, fallback to plain text)
        if hasattr(message, "alternatives") and message.alternatives:
            # Django's EmailMultiAlternatives provides alternatives
            html_content = None
            text_content = message.body

            for content, content_type in message.alternatives:
                if content_type == "text/html":
                    html_content = content
                elif content_type == "text/plain":
                    text_content = content

            if html_content:
                send_smtp_email.html_content = html_content
            if text_content:
                send_smtp_email.text_content = text_content
        else:
            # Plain text email
            send_smtp_email.text_content = message.body

        # Handle attachments if present
        if message.attachments:
            attachments = []
            for attachment in message.attachments:
                if len(attachment) == 3:
                    filename, content, _mimetype = attachment
                    # Brevo requires base64-encoded content
                    if isinstance(content, str):
                        content_bytes = content.encode("utf-8")
                    else:
                        content_bytes = content
                    content_b64 = base64.b64encode(content_bytes).decode("utf-8")
                    attachments.append(
                        {
                            "name": filename,
                            "content": content_b64,
                        }
                    )
            if attachments:
                send_smtp_email.attachment = attachments

        # Send email via Brevo API
        try:
            api_response = self._api_instance.send_transac_email(send_smtp_email)
            logger.info(f"Email sent successfully via Brevo. Message ID: {api_response.message_id}")
        except ApiException as e:
            error_msg = f"Brevo API error: {e.status} - {e.reason}"
            if e.body:
                error_msg += f" - {e.body}"
            logger.error(error_msg)
            raise Exception(error_msg) from e
