from django.core.mail.backends.base import BaseEmailBackend
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
import os
import logging

logger = logging.getLogger(__name__)

class SendGridEmailBackend(BaseEmailBackend):
    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently)
        self.api_key = os.environ.get('SENDGRID_API_KEY')
        if not self.api_key:
            raise ValueError('SENDGRID_API_KEY environment variable is not set')
        self.client = SendGridAPIClient(self.api_key)

    def send_messages(self, email_messages):
        if not email_messages:
            return 0

        sent_count = 0
        for message in email_messages:
            try:
                # Get the sender email and name
                from_email = message.from_email
                from_name = None
                if isinstance(from_email, tuple):
                    from_email, from_name = from_email

                # Create the email
                mail = Mail(
                    from_email=Email(from_email, from_name),
                    to_emails=[To(email) for email in message.to],
                    subject=message.subject,
                    html_content=message.body if message.content_subtype == 'html' else None,
                    plain_text_content=message.body if message.content_subtype == 'plain' else None
                )

                # Add CC recipients if any
                if message.cc:
                    mail.cc = [Email(email) for email in message.cc]

                # Add BCC recipients if any
                if message.bcc:
                    mail.bcc = [Email(email) for email in message.bcc]

                # Send the email
                response = self.client.send(mail)
                if response.status_code == 202:
                    sent_count += 1
                else:
                    if not self.fail_silently:
                        raise Exception(f'SendGrid API returned status code {response.status_code}')
                    logger.error(f'Failed to send email via SendGrid: {response.status_code}')

            except Exception as e:
                if not self.fail_silently:
                    raise
                logger.error(f'Error sending email via SendGrid: {str(e)}')

        return sent_count 