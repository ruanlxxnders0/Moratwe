"""
Template tags for the events app.
"""
from django import template
from events.utils import get_calendar_buttons_html, get_calendar_email_html

register = template.Library()


@register.simple_tag
def calendar_buttons(event, site_url=None):
    """
    Template tag to generate individual calendar buttons.
    
    Usage:
        {% load events_extras %}
        {% calendar_buttons event SITE_URL %}
    """
    return get_calendar_buttons_html(event, site_url)


@register.simple_tag
def calendar_email_links(event, site_url=None):
    """
    Template tag to generate calendar links for email templates.
    
    Usage:
        {% load events_extras %}
        {% calendar_email_links event SITE_URL %}
    """
    return get_calendar_email_html(event, site_url)
