from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.core.mail import send_mass_mail
from django.conf import settings
from django.template import Template, Context
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.urls import path, reverse
from django.core.cache import cache
from django.utils.http import urlencode
from .models import Event, BreakawaySession, RSVP, EventInvitation, EmailTemplate, InviteeRSVP
from userlists.models import UserList, Invitee
from django.utils.safestring import mark_safe
import json
import threading
import uuid
import logging
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives
import csv
from datetime import datetime

# Create a logger for this module
logger = logging.getLogger(__name__)


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ('name', 'subject', 'is_default', 'created_at')
    list_filter = ('is_default',)
    search_fields = ('name', 'subject', 'content')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('name', 'subject', 'content', 'is_default')
        }),
        (_('Timestamps'), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


class BreakawaySessionInline(admin.TabularInline):
    model = BreakawaySession
    extra = 1


class RSVPInline(admin.TabularInline):
    model = RSVP
    extra = 0
    readonly_fields = ('user', 'created_at', 'checked_in', 'qr_code')
    can_delete = False


class EventInvitationInline(admin.TabularInline):
    model = EventInvitation
    extra = 1
    readonly_fields = ('sent_at',)


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('title', 'date', 'location', 'is_active', 'organizer')
    list_filter = ('is_active', 'date')
    search_fields = ('title', 'description', 'location')
    inlines = [EventInvitationInline, BreakawaySessionInline, RSVPInline]
    actions = ['send_invitations']
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'send-invitations-status/<str:task_id>/',
                self.admin_site.admin_view(self.invitation_status),
                name='send-invitations-status',
            ),
        ]
        return custom_urls + urls

    def invitation_status(self, request, task_id):
        """Return the current status of the invitation sending task."""
        status = cache.get(f'invitation_task_{task_id}', {
            'type': 'update_progress',
            'progress': 0,
            'emails_sent': 0,
            'total': 0
        })
        return JsonResponse(status)
    
    def get_rsvp_urls(self, event_id, invitee_email):
        """Generate RSVP accept and decline URLs for an invitee."""
        base_url = settings.SITE_URL.rstrip('/')
        
        # Get the first invitee with this email (in case of duplicates)
        invitee = Invitee.objects.filter(email=invitee_email).first()
        if not invitee:
            raise ValueError(f"No invitee found for email: {invitee_email}")
        
        # Create or get InviteeRSVP
        invitee_rsvp, created = InviteeRSVP.objects.get_or_create(
            invitee=invitee,
            event_id=event_id,
            defaults={'token': uuid.uuid4()}
        )
        
        if created:
            invitee_rsvp.token = uuid.uuid4()
            invitee_rsvp.save()
        
        params = urlencode({
            'token': invitee_rsvp.token,
            'email': invitee_email
        })
        
        return {
            'accept': f"{base_url}/events/rsvp/accept/?{params}",
            'decline': f"{base_url}/events/rsvp/decline/?{params}"
        }
    
    def send_invitations_task(self, event_ids, task_id):
        """
        Background task to send invitations.
        """
        logger.info(f"Starting invitation task {task_id} for events: {event_ids}")
        
        total_invitees = 0
        emails_sent = 0
        failed_emails = []
        
        try:
            # First, count total invitees
            for event in Event.objects.filter(id__in=event_ids):
                for invitation in event.invitations.all():
                    total_invitees += invitation.user_list.invitees.count()
            
            logger.info(f"Total invitees to process: {total_invitees}")
            
            # Update initial status
            cache.set(f'invitation_task_{task_id}', {
                'type': 'update_progress',
                'progress': 0,
                'emails_sent': 0,
                'total': total_invitees
            }, timeout=3600)
            
            for event in Event.objects.filter(id__in=event_ids):
                logger.info(f"Processing event: {event.title} (ID: {event.id})")
                
                for invitation in event.invitations.all():
                    template = invitation.email_template
                    if not template:
                        template = EmailTemplate.objects.filter(is_default=True).first()
                        if not template:
                            logger.error("No email template found (neither custom nor default)")
                            continue
                    
                    logger.info(f"Using template: {template.name}")
                    
                    for invitee in invitation.user_list.invitees.all():
                        if not invitee.email:
                            logger.warning(f"Skipping invitee without email in list: {invitation.user_list.name}")
                            continue
                        
                        try:
                            # Generate RSVP URLs for this invitee
                            rsvp_urls = self.get_rsvp_urls(event.id, invitee.email)
                            
                            context = Context({
                                'first_name': invitee.first_name or 'Guest',
                                'last_name': invitee.last_name or '',
                                'event': event,
                                'rsvp_accept_url': rsvp_urls['accept'],
                                'rsvp_decline_url': rsvp_urls['decline'],
                                'SITE_URL': settings.SITE_URL.rstrip('/')
                            })
                            
                            subject = Template(template.subject).render(context)
                            message = Template(template.content).render(context)
                            
                            logger.info(f"Attempting to send email to: {invitee.email}")
                            
                            # Log email content for debugging
                            logger.debug(f"Email content for {invitee.email}:")
                            logger.debug(f"Subject: {subject}")
                            logger.debug(f"Accept URL: {rsvp_urls['accept']}")
                            logger.debug(f"Decline URL: {rsvp_urls['decline']}")
                            
                            # Check if SITE_URL is configured
                            if not hasattr(settings, 'SITE_URL'):
                                logger.error("SITE_URL is not configured in settings")
                                raise ValueError("SITE_URL is not configured in settings")
                            
                            # Check if DEFAULT_FROM_EMAIL is configured
                            if not settings.DEFAULT_FROM_EMAIL:
                                logger.error("DEFAULT_FROM_EMAIL is not configured in settings")
                                raise ValueError("DEFAULT_FROM_EMAIL is not configured in settings")
                            
                            # Send the email
                            plain_message = strip_tags(message)
                            email = EmailMultiAlternatives(
                                subject=subject,
                                body=plain_message,
                                from_email=settings.DEFAULT_FROM_EMAIL,
                                to=[invitee.email]
                            )
                            email.attach_alternative(message, "text/html")
                            email.send()
                            
                            emails_sent += 1
                            
                            # Update progress
                            progress = int((emails_sent / total_invitees) * 100)
                            cache.set(f'invitation_task_{task_id}', {
                                'type': 'update_progress',
                                'progress': progress,
                                'emails_sent': emails_sent,
                                'total': total_invitees
                            }, timeout=3600)
                            
                            logger.info(f"Successfully sent email to: {invitee.email}")
                            
                        except Exception as e:
                            logger.error(f"Failed to send email to {invitee.email}: {str(e)}")
                            failed_emails.append({
                                'email': invitee.email,
                                'error': str(e)
                            })
                            continue
            
            # Final status update
            cache.set(f'invitation_task_{task_id}', {
                'type': 'complete',
                'progress': 100,
                'emails_sent': emails_sent,
                'total': total_invitees,
                'failed': failed_emails
            }, timeout=3600)
            
            logger.info(f"Invitation task completed. Sent {emails_sent} emails.")
            if failed_emails:
                logger.warning(f"Failed to send {len(failed_emails)} emails: {failed_emails}")
            
        except Exception as e:
            logger.error(f"Error in send_invitations_task: {str(e)}")
            cache.set(f'invitation_task_{task_id}', {
                'type': 'error',
                'error': str(e)
            }, timeout=3600)
    
    def send_invitations(self, request, queryset):
        """
        Custom admin action to send invitations to all user lists associated with selected events.
        """
        if not queryset.exists():
            self.message_user(request, _("No events selected."), messages.WARNING)
            return
        
        # Check if required settings are configured
        if not hasattr(settings, 'SITE_URL'):
            self.message_user(
                request,
                _("SITE_URL is not configured in settings. Please configure it before sending invitations."),
                messages.ERROR
            )
            return
            
        if not settings.DEFAULT_FROM_EMAIL:
            self.message_user(
                request,
                _("DEFAULT_FROM_EMAIL is not configured in settings. Please configure it before sending invitations."),
                messages.ERROR
            )
            return
        
        task_id = str(uuid.uuid4())
        event_ids = list(queryset.values_list('id', flat=True))
        
        logger.info(f"Starting invitation process for events: {event_ids}")
        
        # Start the background thread
        thread = threading.Thread(
            target=self.send_invitations_task,
            args=(event_ids, task_id)
        )
        thread.daemon = True
        thread.start()
        
        # Show message to user
        self.message_user(
            request,
            mark_safe(_(
                f'Started sending invitations. '
                f'<a href="#" class="invitation-progress" data-task-id="{task_id}">'
                f'Click here to check progress</a>'
            )),
            messages.INFO
        )
    
    send_invitations.short_description = _("Send invitations to selected events")

    class Media:
        js = ('admin/js/invitation_progress.js',)


@admin.register(BreakawaySession)
class BreakawaySessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'event', 'start_time', 'end_time')
    list_filter = ('event',)
    search_fields = ('title', 'description')
    filter_horizontal = ('panelists',)


@admin.register(RSVP)
class RSVPAdmin(admin.ModelAdmin):
    list_display = ('event', 'user', 'checked_in', 'created_at')
    list_filter = ('checked_in', 'event')
    search_fields = ('user__email', 'user__first_name', 'user__last_name')
    readonly_fields = ('created_at', 'qr_code')
    filter_horizontal = ('selected_sessions',)
    actions = ['export_as_csv']
    
    def export_as_csv(self, request, queryset):
        """Export selected RSVPs to CSV."""
        meta = self.model._meta
        field_names = [
            'Event Title',
            'Event Date',
            'Event Location',
            'User Email',
            'User First Name',
            'User Last Name',
            'RSVP Status',
            'Response Date',
            'Checked In',
            'Selected Sessions'
        ]
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="rsvps_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(field_names)
        
        for rsvp in queryset:
            selected_sessions = ', '.join([session.title for session in rsvp.selected_sessions.all()])
            writer.writerow([
                rsvp.event.title,
                rsvp.event.date.strftime('%Y-%m-%d %H:%M'),
                rsvp.event.location,
                rsvp.user.email,
                rsvp.user.first_name,
                rsvp.user.last_name,
                rsvp.status,
                rsvp.response_date.strftime('%Y-%m-%d %H:%M') if rsvp.response_date else '',
                'Yes' if rsvp.checked_in else 'No',
                selected_sessions
            ])
        
        return response
    
    export_as_csv.short_description = _("Export selected RSVPs to CSV")


@admin.register(InviteeRSVP)
class InviteeRSVPAdmin(admin.ModelAdmin):
    list_display = ('invitee', 'event', 'status', 'timestamp')
    list_filter = ('status', 'event', 'timestamp')
    search_fields = ('invitee__email', 'event__title')
    readonly_fields = ('created_at', 'updated_at')
    actions = ['export_as_csv']
    
    def export_as_csv(self, request, queryset):
        """Export selected InviteeRSVPs to CSV."""
        meta = self.model._meta
        field_names = [
            'Event Title',
            'Event Date',
            'Event Location',
            'Invitee Email',
            'Invitee First Name',
            'Invitee Last Name',
            'RSVP Status',
            'Response Date',
            'Created At',
            'Updated At'
        ]
        
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="invitee_rsvps_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow(field_names)
        
        for invitee_rsvp in queryset:
            writer.writerow([
                invitee_rsvp.event.title,
                invitee_rsvp.event.date.strftime('%Y-%m-%d %H:%M'),
                invitee_rsvp.event.location,
                invitee_rsvp.invitee.email,
                invitee_rsvp.invitee.first_name,
                invitee_rsvp.invitee.last_name,
                invitee_rsvp.status,
                invitee_rsvp.timestamp.strftime('%Y-%m-%d %H:%M') if invitee_rsvp.timestamp else '',
                invitee_rsvp.created_at.strftime('%Y-%m-%d %H:%M'),
                invitee_rsvp.updated_at.strftime('%Y-%m-%d %H:%M')
            ])
        
        return response
    
    export_as_csv.short_description = _("Export selected InviteeRSVPs to CSV")
