import os
import logging
import sys

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('logs/mail.log')
    ]
)

logger = logging.getLogger(__name__)

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moratwe.settings.development')
import django
django.setup()

from events.models import Event, EventInvitation, EmailTemplate
from userlists.models import UserList, Invitee
from django.template import Template, Context
from django.core.mail import EmailMultiAlternatives
from django.utils.html import strip_tags
from django.conf import settings
import uuid

logger.info("Starting test invitation script")

try:
    # Get the Community Meetup event
    event = Event.objects.get(id=63)
    logger.info(f"Found event: {event.title}")

    # Get the default template
    template = EmailTemplate.objects.get(is_default=True)
    logger.info("Found default email template")

    # Create a test invitee
    test_email = "nicelhage@hotmail.com"
    invitee = Invitee.objects.filter(email=test_email).first()
    logger.info(f"Looking for invitee with email: {test_email}")

    if invitee:
        logger.info(f"Found invitee: {invitee.first_name} {invitee.last_name}")
        
        # Log email settings
        logger.info(f"Email settings:")
        logger.info(f"EMAIL_BACKEND: {settings.EMAIL_BACKEND}")
        logger.info(f"EMAIL_HOST: {settings.EMAIL_HOST}")
        logger.info(f"EMAIL_PORT: {settings.EMAIL_PORT}")
        logger.info(f"EMAIL_USE_TLS: {settings.EMAIL_USE_TLS}")
        logger.info(f"EMAIL_HOST_USER: {settings.EMAIL_HOST_USER}")
        logger.info(f"DEFAULT_FROM_EMAIL: {settings.DEFAULT_FROM_EMAIL}")
        logger.info(f"SITE_URL: {settings.SITE_URL}")

        # Generate RSVP URLs
        invitee.rsvp_token = uuid.uuid4()
        invitee.save(update_fields=['rsvp_token'])
        base_url = settings.SITE_URL.rstrip('/')
        rsvp_urls = {
            'accept': f"{base_url}/events/rsvp/accept/?token={invitee.rsvp_token}&email={test_email}",
            'decline': f"{base_url}/events/rsvp/decline/?token={invitee.rsvp_token}&email={test_email}"
        }
        logger.info(f"Generated RSVP URLs: {rsvp_urls}")

        # Create context for template
        context = Context({
            'first_name': invitee.first_name or 'Guest',
            'last_name': invitee.last_name or '',
            'event': event,
            'rsvp_accept_url': rsvp_urls['accept'],
            'rsvp_decline_url': rsvp_urls['decline']
        })

        # Render the template
        subject = Template(template.subject).render(context)
        message = Template(template.content).render(context)
        logger.info(f"Rendered email template with subject: {subject}")

        # Create plain text version
        plain_message = strip_tags(message)

        try:
            # Send the email
            email = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[test_email]
            )
            email.attach_alternative(message, "text/html")
            email.send()
            logger.info(f"Email sent successfully to {test_email}")
            
            print(f"\nEmail sent successfully!")
            print(f"Subject: {subject}")
            print(f"To: {test_email}")
            print(f"\nCheck logs/mail.log for detailed information.")
            
        except Exception as e:
            logger.error(f"Failed to send email: {str(e)}", exc_info=True)
            print(f"\nError sending email: {str(e)}")
            print("Check logs/mail.log for detailed error information.")
    else:
        error_msg = f"No invitee found with email: {test_email}"
        logger.error(error_msg)
        print(f"\nError: {error_msg}")

except Exception as e:
    logger.error(f"Script error: {str(e)}", exc_info=True)
    print(f"\nScript error: {str(e)}")
    print("Check logs/mail.log for detailed error information.") 