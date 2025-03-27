import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moratwe.settings.development')
import django
django.setup()

from events.models import Event, EventInvitation, EmailTemplate
from userlists.models import UserList

# Get the Community Meetup event
event = Event.objects.get(id=63)
template = EmailTemplate.objects.get(is_default=True)

# Create invitations for all user lists
for user_list in UserList.objects.all():
    EventInvitation.objects.create(
        event=event,
        user_list=user_list,
        email_template=template
    )
    print(f"Created invitation for {user_list.name}")

print("\nAll invitations created for:", event.title)
print("Invited lists:", [i.user_list.name for i in event.invitations.all()]) 