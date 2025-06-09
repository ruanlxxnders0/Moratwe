from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.cache import cache
from django.utils.translation import gettext as _
from django.http import Http404
from .models import Event, RSVP, EmailTemplate, EventInvitation, InviteeRSVP, BreakawaySession
from users.models import CustomUser
from django.contrib.auth import login
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.template import Template, Context
from django.urls import reverse
from userlists.models import Invitee
from django.utils.html import strip_tags
from django.contrib.auth.decorators import login_required


def handle_rsvp(request, action):
    """Handle RSVP accept/decline responses."""
    token = request.GET.get('token')
    email = request.GET.get('email')
    
    if not token or not email:
        raise Http404(_("Invalid RSVP link"))
    
    # Get invitation data from the invitee model
    try:
        invitee_rsvp = InviteeRSVP.objects.select_related('invitee__user_list', 'event').get(token=token)
        invitee = invitee_rsvp.invitee
        event = invitee_rsvp.event
        
        if invitee.email != email:
            raise Http404(_("Invalid RSVP link"))
        
        try:
            user = CustomUser.objects.get(email=email)
        except CustomUser.DoesNotExist:
            # User doesn't exist, redirect to registration
            request.session['invitee_email'] = email
            request.session['invitee_first_name'] = invitee.first_name
            request.session['invitee_last_name'] = invitee.last_name
            request.session['invitee_mobile'] = invitee.mobile_number
            request.session['event_id'] = event.id
            request.session['rsvp_token'] = token
            
            return redirect('events:register_from_invitation')
        
        # Update RSVP status
        invitee_rsvp.status = 'accepted' if action == 'accept' else 'declined'
        invitee_rsvp.timestamp = timezone.now()
        invitee_rsvp.save()
        
        # Create or update user RSVP
        rsvp, created = RSVP.objects.get_or_create(
            event=event,
            user=user,
            defaults={
                'status': 'accepted' if action == 'accept' else 'declined',
                'response_date': timezone.now(),
                'is_registered_user': True
            }
        )
        
        if not created:
            rsvp.status = 'accepted' if action == 'accept' else 'declined'
            rsvp.response_date = timezone.now()
            rsvp.save()
        
        # Show appropriate message
        if action == 'accept':
            messages.success(request, _("Thank you for accepting the invitation!"))
            # Send confirmation email
            send_confirmation_email(user, event)
        else:
            messages.info(request, _("Thank you for letting us know you can't make it."))
        
        return redirect('events:event_detail', event_id=event.id)
        
    except InviteeRSVP.DoesNotExist:
        raise Http404(_("Invalid RSVP link"))


def rsvp_accept(request):
    """Handle RSVP accept responses."""
    return handle_rsvp(request, 'accept')


def rsvp_decline(request):
    """Handle RSVP decline responses."""
    return handle_rsvp(request, 'decline')


def register_from_invitation(request):
    if request.method == 'POST':
        email = request.session.get('invitee_email')
        first_name = request.session.get('invitee_first_name')
        last_name = request.session.get('invitee_last_name')
        mobile = request.session.get('invitee_mobile')
        event_id = request.session.get('event_id')
        token = request.session.get('rsvp_token')
        password = request.POST.get('password')
        
        if not all([email, first_name, last_name, password, event_id, token]):
            messages.error(request, 'Missing required information.')
            return redirect('events:home')
        
        # Create new user
        user = CustomUser.objects.create_user(
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            phone_number=mobile
        )
        
        # Log the user in
        login(request, user)
        
        try:
            invitee_rsvp = InviteeRSVP.objects.get(token=token)
            event = invitee_rsvp.event
            
            # Update RSVP status
            invitee_rsvp.status = 'accepted'
            invitee_rsvp.timestamp = timezone.now()
            invitee_rsvp.save()
            
            # Create user RSVP
            rsvp = RSVP.objects.create(
                event=event,
                user=user,
                status='accepted',
                response_date=timezone.now(),
                is_registered_user=True
            )
            
            # Send confirmation email
            send_confirmation_email(user, event)
            
            # Clear session data
            for key in ['invitee_email', 'invitee_first_name', 'invitee_last_name', 
                       'invitee_mobile', 'event_id', 'rsvp_token']:
                request.session.pop(key, None)
            
            messages.success(request, 'Registration successful! You have accepted the invitation.')
            return redirect('events:event_detail', event_id=event.id)
            
        except InviteeRSVP.DoesNotExist:
            messages.error(request, 'Invalid invitation.')
            return redirect('events:home')
    
    return render(request, 'events/register_from_invitation.html', {
        'email': request.session.get('invitee_email'),
        'first_name': request.session.get('invitee_first_name'),
        'last_name': request.session.get('invitee_last_name'),
        'mobile': request.session.get('invitee_mobile'),
        'SITE_URL': settings.SITE_URL.rstrip('/')
    })


def send_confirmation_email(user, event):
    """Send a confirmation email after RSVP acceptance."""
    # Get the RSVP to access the QR code
    rsvp = RSVP.objects.get(event=event, user=user)
    
    # Try to get a confirmation template, fall back to default if none exists
    template = EmailTemplate.objects.filter(name='RSVP Confirmation').first()
    if not template:
        # Create a confirmation template if it doesn't exist
        template = EmailTemplate.objects.create(
            name='RSVP Confirmation',
            subject='Your RSVP Confirmation for {{ event.title }}',
            content="""
            <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
                <h1 style="color: #333;">RSVP Confirmation</h1>
                
                <p>Dear {{ first_name }},</p>
                
                <p>Thank you for accepting the invitation to:</p>
                
                <div style="background-color: #f5f5f5; padding: 20px; margin: 20px 0; border-radius: 5px;">
                    <h2 style="color: #333; margin-top: 0;">{{ event.title }}</h2>
                    <p><strong>Date:</strong> {{ event.date|date:"l, F j, Y" }}</p>
                    <p><strong>Time:</strong> {{ event.date|date:"g:i A" }}</p>
                    <p><strong>Location:</strong> {{ event.location }}</p>
                    {% if event.description %}
                    <p><strong>Description:</strong> {{ event.description }}</p>
                    {% endif %}
                </div>
                
                {% if qr_code_url %}
                <div style="text-align: center; margin: 20px 0;">
                    <h3 style="color: #333;">Your Check-in QR Code</h3>
                    <img src="{{ qr_code_url }}" alt="RSVP QR Code" style="width: 200px; height: 200px;">
                    <p style="color: #666; font-size: 0.9em;">Present this QR code at the event for check-in</p>
                </div>
                {% endif %}
                
                <p>You can view the event details and manage your RSVP at any time by visiting:</p>
                <p><a href="{{ event_url }}" style="color: #007bff;">{{ event_url }}</a></p>
                
                <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #eee;">
                    <p style="color: #666; font-size: 0.9em;">
                        Get the Moratwe App to manage your RSVPs and stay updated on the go:
                    </p>
                    <p style="color: #666; font-size: 0.9em;">
                        <a href="https://apps.apple.com/app/moratwe" style="color: #007bff;">iOS App Store</a> | 
                        <a href="https://play.google.com/store/apps/details?id=com.moratwe.app" style="color: #007bff;">Google Play Store</a>
                    </p>
                </div>
            </div>
            """
        )
    
    # Build the context with all necessary information
    context = Context({
        'first_name': user.first_name or 'Guest',
        'last_name': user.last_name or '',
        'event': event,
        'qr_code_url': f"{settings.SITE_URL}{rsvp.qr_code.url}" if rsvp.qr_code else None,
        'event_url': f"{settings.SITE_URL}/events/{event.id}/",
        'SITE_URL': settings.SITE_URL.rstrip('/')
    })
    
    subject = Template(template.subject).render(context)
    message = Template(template.content).render(context)
    plain_message = strip_tags(message)
    
    send_mail(
        subject=subject,
        message=plain_message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        html_message=message,
        fail_silently=False,
    )


def home(request):
    """Home page view."""
    events = Event.objects.filter(is_active=True, date__gte=timezone.now()).order_by('date')
    return render(request, 'events/home.html', {
        'events': events,
        'SITE_URL': settings.SITE_URL.rstrip('/')
    })


def event_detail(request, event_id):
    """Event detail view."""
    try:
        event = Event.objects.get(id=event_id)
        user_rsvp = None
        if request.user.is_authenticated:
            user_rsvp = RSVP.objects.filter(event=event, user=request.user).first()
        
        return render(request, 'events/event_detail.html', {
            'event': event,
            'user_rsvp': user_rsvp,
            'SITE_URL': settings.SITE_URL.rstrip('/')
        })
    except Event.DoesNotExist:
        messages.error(request, 'Event not found.')
        return redirect('events:home')


@login_required
def update_rsvp(request, event_id):
    """Handle RSVP updates from the event detail page."""
    if request.method != 'POST':
        # messages.error(request, _("Invalid request method."))
        return redirect('events:event_detail', event_id=event_id)
    
    event = get_object_or_404(Event, id=event_id)
    status = request.POST.get('status')
    
    if status not in ['accepted', 'declined']:
        messages.error(request, _("Invalid RSVP status."))
        return redirect('events:event_detail', event_id=event_id)
    
    # Create or update RSVP
    rsvp, created = RSVP.objects.get_or_create(
        event=event,
        user=request.user,
        defaults={
            'status': status,
            'response_date': timezone.now(),
            'is_registered_user': True
        }
    )
    
    if not created:
        rsvp.status = status
        rsvp.response_date = timezone.now()
        rsvp.save()
    
    # Update invitee RSVP if exists
    try:
        # Try to get the first Invitee matching the email
        invitee = Invitee.objects.filter(email=request.user.email).first()
        if invitee: # Check if an invitee was actually found
            invitee_rsvp = InviteeRSVP.objects.get(invitee=invitee, event=event)
            invitee_rsvp.status = status
            invitee_rsvp.timestamp = timezone.now()
            invitee_rsvp.save()
        # If no invitee is found by that email, it will also pass silently,
        # which is consistent with the original Invitee.DoesNotExist handling.
    except InviteeRSVP.DoesNotExist: # Only catch InviteeRSVP.DoesNotExist here
        pass
    # No longer need to catch Invitee.DoesNotExist as .first() returns None if not found
    # and the `if invitee:` handles it.
    # MultipleObjectsReturned is also avoided by .first().
    # You might want to add logging here if multiple invitees are found,
    # e.g., if Invitee.objects.filter(email=request.user.email).count() > 1
    
    # Send confirmation email for accepted RSVPs
    if status == 'accepted':
        send_confirmation_email(request.user, event)
        messages.success(request, _("Thank you for accepting the invitation!"))
        
        # If this is a new acceptance or they're changing from declined to accepted,
        # redirect to the edit RSVP form for dietary requirements
        if created or rsvp.dietary_requirements == '':
            messages.info(request, _("Please provide your dietary requirements and preferences."))
            return redirect('events:edit_rsvp', event_id=event_id)
    else:
        messages.info(request, _("Thank you for letting us know you can't make it."))
    
    return redirect('events:event_detail', event_id=event_id)


@login_required
def edit_rsvp(request, event_id):
    """Edit detailed RSVP information including dietary requirements."""
    event = get_object_or_404(Event, id=event_id)
    
    # Check if the user has already accepted the invitation
    try:
        rsvp = RSVP.objects.get(event=event, user=request.user)
        if rsvp.status != 'accepted':
            messages.error(request, _("You must accept the invitation before providing additional details."))
            return redirect('events:event_detail', event_id=event.id)
    except RSVP.DoesNotExist:
        messages.error(request, _("You haven't RSVP'd to this event yet."))
        return redirect('events:event_detail', event_id=event.id)
    
    if request.method == 'POST':
        # Process form data
        number_of_guests = int(request.POST.get('number_of_guests', 0))
        notes = request.POST.get('notes', '')
        
        # Handle dietary requirements from dropdown or text field
        dietary_select = request.POST.get('dietary_requirements_select', '')
        if dietary_select == 'other':
            dietary_requirements = request.POST.get('dietary_requirements', '')
        else:
            dietary_requirements = dietary_select
        
        # Update RSVP with additional information
        rsvp.number_of_guests = number_of_guests
        rsvp.dietary_requirements = dietary_requirements
        rsvp.notes = notes
        rsvp.save()
        
        # Handle breakaway session selection
        if event.breakaways.exists():
            # Clear existing selections
            rsvp.selected_sessions.clear()
            
            # Add new selections
            selected_session_ids = request.POST.getlist('selected_sessions')
            if selected_session_ids:
                sessions = BreakawaySession.objects.filter(id__in=selected_session_ids, event=event)
                rsvp.selected_sessions.add(*sessions)
        
        messages.success(request, _("Your RSVP details have been updated."))
        return redirect('events:event_detail', event_id=event.id)
    
    return render(request, 'events/edit_rsvp.html', {
        'event': event,
        'rsvp': rsvp,
        'SITE_URL': settings.SITE_URL.rstrip('/')
    })
