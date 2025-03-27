import os
import logging
from django.conf import settings

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler('logs/django.log'),
        logging.StreamHandler()
    ]
)

# Set the Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moratwe.settings.development')
import django
django.setup()

from events.models import Event
from events.admin import EventAdmin
from django.contrib.admin.sites import AdminSite

# Get the Community Meetup event
event = Event.objects.get(id=63)

# Create an instance of EventAdmin
event_admin = EventAdmin(model=Event, admin_site=AdminSite())

# Create a mock request (None is sufficient for our test)
request = None

# Call the send_invitations_task directly
task_id = event_admin.send_invitations_task([event.id], str(event.id))

print(f"Started sending invitations for {event.title}")
print("Check the Django logs for progress") 