import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moratwe.settings.development')
import django
django.setup()

from events.models import Event, EventInvitation
from userlists.models import UserList, Invitee

print("\nEvents:")
for event in Event.objects.all():
    print(f"- {event.title} (ID: {event.id})")
    print("  Invited Lists:")
    for invitation in event.invitations.all():
        print(f"  * {invitation.user_list.name}")

print("\nUser Lists:")
for user_list in UserList.objects.all():
    print(f"- {user_list.name} (ID: {user_list.id})")
    print("  Invitees:")
    for invitee in user_list.invitees.all():
        print(f"  * {invitee.email}") 