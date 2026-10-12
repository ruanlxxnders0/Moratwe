import uuid

from django.conf import settings
from django.template import Context, Template
from django.urls import reverse
from django.utils import timezone

from .models import EmailTemplate

TEMPLATE_NAME = 'SMME RSVP Invitation'


def send_smme_rsvp_email(reg, base_url=None):
    """Email an SMME their personal Confirm/Decline RSVP links. Raises on failure."""
    from .tasks import send_via_sendgrid

    template = EmailTemplate.objects.filter(name=TEMPLATE_NAME).first()
    if not template:
        raise RuntimeError(f'Email template "{TEMPLATE_NAME}" not found.')

    site = (base_url or settings.SITE_URL).rstrip('/')
    if not reg.rsvp_token:
        reg.rsvp_token = uuid.uuid4()

    context = Context({
        'first_name': reg.name,
        'last_name': reg.surname,
        'company': reg.company,
        'event': reg.event,
        'rsvp_confirm_url': f"{site}{reverse('events:smme_rsvp', args=[reg.rsvp_token, 'confirm'])}",
        'rsvp_decline_url': f"{site}{reverse('events:smme_rsvp', args=[reg.rsvp_token, 'decline'])}",
        'SITE_URL': site,
    })
    subject = Template(template.subject).render(context)
    html = Template(template.content).render(context)
    organizer = reg.event.organizer.get_full_name() if reg.event.organizer else ''
    send_via_sendgrid(subject, html, reg.email, organizer or 'Moratwe Events')

    reg.rsvp_email_sent_at = timezone.now()
    reg.save(update_fields=['rsvp_token', 'rsvp_email_sent_at', 'updated_at'])
