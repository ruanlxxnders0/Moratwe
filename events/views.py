import logging
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.core.cache import cache
from django.utils.translation import gettext as _
from django.http import Http404
from django.db import IntegrityError
from .models import Event, RSVP, EmailTemplate, EventInvitation, InviteeRSVP, BreakawaySession
from users.models import CustomUser
from django.contrib.auth import login
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.template import Template, Context
from django.urls import reverse
from userlists.models import Invitee

logger = logging.getLogger(__name__)
from django.utils.html import strip_tags
from django.contrib.auth.decorators import login_required
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import os

logger = logging.getLogger(__name__)


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
            send_confirmation_email(user, event, request)
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
        # Allow users to edit their name and mobile, but fallback to session data
        first_name = request.POST.get('first_name') or request.session.get('invitee_first_name')
        last_name = request.POST.get('last_name') or request.session.get('invitee_last_name')
        # Handle mobile number: use POST data if provided, otherwise fallback to session
        mobile = request.POST.get('mobile', '').strip()
        if not mobile:
            mobile = request.session.get('invitee_mobile', '')
        event_id = request.session.get('event_id')
        token = request.session.get('rsvp_token')
        password = request.POST.get('password')
        
        if not all([email, first_name, last_name, password, event_id, token]):
            messages.error(request, 'Missing required information.')
            return redirect('events:home')
        
        # Create new user
        try:
            # Handle empty phone number properly
            phone_number = mobile.strip() if mobile and mobile.strip() else None
            
            user = CustomUser.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                phone_number=phone_number
            )
        except IntegrityError as e:
            # Handle database integrity errors (like duplicate phone numbers)
            if 'phone_number' in str(e).lower():
                messages.error(request, 'This phone number is already registered. Please contact support if you believe this is an error.')
            elif 'email' in str(e).lower():
                messages.error(request, 'This email address is already registered. Please contact support if you believe this is an error.')
            else:
                messages.error(request, 'A user with this information already exists. Please contact support if you believe this is an error.')
            return render(request, 'events/register_from_invitation.html', {
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'mobile': mobile,
                'SITE_URL': settings.SITE_URL.rstrip('/')
            })
        except Exception as e:
            # Handle any other unexpected errors
            logger.error(f"Unexpected error during invitation registration: {e}")
            messages.error(request, 'An unexpected error occurred during registration. Please try again or contact support.')
            return render(request, 'events/register_from_invitation.html', {
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'mobile': mobile,
                'SITE_URL': settings.SITE_URL.rstrip('/')
            })
        
        # Log the user in (specify backend since we have multiple backends)
        login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        
        try:
            invitee_rsvp = InviteeRSVP.objects.get(token=token)
            event = invitee_rsvp.event
            
            # Update RSVP status
            invitee_rsvp.status = 'accepted'
            invitee_rsvp.timestamp = timezone.now()
            invitee_rsvp.save()
            
            # Create user RSVP
            try:
                rsvp = RSVP.objects.create(
                    event=event,
                    user=user,
                    status='accepted',
                    response_date=timezone.now(),
                    is_registered_user=True
                )
            except IntegrityError as e:
                # Handle potential duplicate RSVP
                logger.warning(f"RSVP creation conflict for user {user.id} and event {event.id}: {e}")
                rsvp, created = RSVP.objects.get_or_create(
                    event=event,
                    user=user,
                    defaults={
                        'status': 'accepted',
                        'response_date': timezone.now(),
                        'is_registered_user': True
                    }
                )
                if not created:
                    rsvp.status = 'accepted'
                    rsvp.response_date = timezone.now()
                    rsvp.save()
            
            # Send confirmation email (don't let email errors block the flow)
            try:
                send_confirmation_email(user, event, request)
            except Exception as e:
                logger.error(f"Error sending confirmation email to {user.email}: {e}")
                # Continue with the flow even if email fails
            
            # Clear session data
            for key in ['invitee_email', 'invitee_first_name', 'invitee_last_name', 
                       'invitee_mobile', 'event_id', 'rsvp_token']:
                request.session.pop(key, None)
            
            messages.success(request, 'Registration successful! You have accepted the invitation.')
            return redirect('events:event_detail', event_id=event.id)
            
        except InviteeRSVP.DoesNotExist:
            messages.error(request, 'Invalid invitation.')
            return redirect('events:home')
        except Exception as e:
            # Handle any other unexpected errors during RSVP processing
            logger.error(f"Unexpected error during RSVP processing for user {user.id}: {e}")
            messages.warning(request, 'Registration successful, but there was an issue processing your RSVP. Please contact support if needed.')
            return redirect('events:home')
    
    return render(request, 'events/register_from_invitation.html', {
        'email': request.session.get('invitee_email'),
        'first_name': request.session.get('invitee_first_name'),
        'last_name': request.session.get('invitee_last_name'),
        'mobile': request.session.get('invitee_mobile'),
        'SITE_URL': settings.SITE_URL.rstrip('/')
    })


def send_confirmation_email(user, event, request=None):
    """Send a confirmation email after RSVP acceptance."""
    # Get the RSVP to access the QR code
    try:
        rsvp = RSVP.objects.get(event=event, user=user)
    except RSVP.DoesNotExist:
        logger.error(f"Could not find RSVP for user {user.id} and event {event.id} when sending confirmation.")
        return

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
    qr_code_url = None
    if rsvp.qr_code:
        if request:
            qr_code_url = request.build_absolute_uri(rsvp.qr_code.url)
        else:
            qr_code_url = f"{settings.SITE_URL}{rsvp.qr_code.url}"

    context = Context({
        'first_name': user.first_name or 'Guest',
        'last_name': user.last_name or '',
        'event': event,
        'qr_code_url': qr_code_url,
        'event_url': f"{settings.SITE_URL.rstrip('/')}{reverse('events:event_detail', args=[event.id])}",
        'SITE_URL': settings.SITE_URL.rstrip('/')
    })
    
    subject = Template(template.subject).render(context)
    html_content = Template(template.content).render(context)

    message = Mail(
        from_email=settings.DEFAULT_FROM_EMAIL,
        to_emails=user.email,
        subject=subject,
        html_content=html_content
    )
    
    try:
        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        response = sg.send(message)
        logger.info(f"SendGrid confirmation email sent to {user.email}, status code: {response.status_code}")
    except Exception as e:
        logger.error(f"Error sending confirmation email via SendGrid to {user.email}: {e}")


def home(request):
    """Home page view."""
    events = Event.objects.filter(is_active=True, date__gte=timezone.now()).order_by('date')
    
    # If user is logged in, get their RSVP status for each event
    if request.user.is_authenticated:
        # Get all RSVPs for this user and these events
        user_rsvps = RSVP.objects.filter(
            user=request.user, 
            event__in=events
        ).select_related('event')
        
        # Create a dictionary for quick lookup: event_id -> rsvp
        rsvp_dict = {rsvp.event.id: rsvp for rsvp in user_rsvps}
        
        # Add RSVP information to each event
        for event in events:
            event.user_rsvp = rsvp_dict.get(event.id, None)
    
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
        send_confirmation_email(request.user, event, request)
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
