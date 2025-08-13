from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from django.core.mail import send_mass_mail, send_mail
from django.conf import settings
from django.template import Template, Context
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, HttpResponseRedirect
from django.urls import path, reverse
from django.core.cache import cache
from django.utils.http import urlencode
from .models import Event, BreakawaySession, RSVP, EventInvitation, EmailTemplate, InviteeRSVP, TaskStatus
from userlists.models import UserList, Invitee
from django.utils.safestring import mark_safe
from django.shortcuts import render, get_object_or_404, redirect
import json
import threading
import uuid
import logging
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives
import csv
from datetime import datetime
from django.core.exceptions import ObjectDoesNotExist
from django.utils import timezone
import time
import os
import re

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
    inlines = [EventInvitationInline, BreakawaySessionInline]
    actions = ['send_invitations']
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'send-invitations-status/<str:task_id>/',
                self.admin_site.admin_view(self.invitation_status),
                name='send-invitations-status',
            ),
            path(
                'rsvp-dashboard/<int:event_id>/',
                self.admin_site.admin_view(self.rsvp_dashboard),
                name='rsvp-dashboard',
            ),
            path(
                'batch-process-rsvps/<int:object_id>/',
                self.admin_site.admin_view(self.batch_process_rsvps),
                name='batch-process-rsvps',
            ),
            path(
                'batch-process-rsvps-status/<str:task_id>/',
                self.admin_site.admin_view(self.batch_rsvp_status),
                name='batch-rsvp-status',
            ),
            path(
                'batch-process-rsvps-control/<str:task_id>/<str:action>/',
                self.admin_site.admin_view(self.batch_rsvp_control),
                name='batch-rsvp-control',
            ),
            path(
                'batch-process-invitations/<int:object_id>/',
                self.admin_site.admin_view(self.batch_process_invitations),
                name='batch-process-invitations',
            ),
            path(
                'batch-invitations-status/<str:task_id>/',
                self.admin_site.admin_view(self.batch_invitation_status),
                name='batch-invitation-status',
            ),
            path(
                'batch-invitations-control/<str:task_id>/<str:action>/',
                self.admin_site.admin_view(self.batch_invitation_control),
                name='batch-invitation-control',
            ),
            path(
                'batch-tasks-dashboard/',
                self.admin_site.admin_view(self.batch_tasks_dashboard),
                name='batch-tasks-dashboard',
            ),
            path(
                'export-dietary-requirements/<int:event_id>/',
                self.admin_site.admin_view(self.export_dietary_requirements),
                name='export_dietary_requirements',
            ),
            path(
                'test-cache-connection/',
                self.admin_site.admin_view(self.test_cache_connection),
                name='test-cache-connection',
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

    def rsvp_dashboard(self, request, event_id):
        """Display RSVP statistics and management dashboard for an event."""
        try:
            event = get_object_or_404(Event, id=event_id)
            
            # Get RSVP statistics with error handling
            try:
                user_rsvps = RSVP.objects.filter(event=event)
                invitee_rsvps = InviteeRSVP.objects.filter(event=event)
            except Exception as e:
                logger.error(f"Error fetching RSVPs for event {event_id}: {e}")
                messages.error(request, f"Error fetching RSVP data: {str(e)}")
                return redirect('admin:events_event_changelist')
            
            # Calculate total invitations sent (count InviteeRSVP records where email was actually sent)
            invitation_count = invitee_rsvps.filter(email_sent=True).count()
            
            # Calculate statistics with safe defaults
            try:
                accepted_count = user_rsvps.filter(status='accepted').count() + invitee_rsvps.filter(status='accepted').count()
                declined_count = user_rsvps.filter(status='declined').count() + invitee_rsvps.filter(status='declined').count()
                pending_count = user_rsvps.filter(status='pending').count() + invitee_rsvps.filter(status='pending').count()
                maybe_count = user_rsvps.filter(status='maybe').count()
                checked_in_count = user_rsvps.filter(checked_in=True).count()
            except Exception as e:
                logger.error(f"Error calculating RSVP statistics for event {event_id}: {e}")
                # Provide safe defaults
                accepted_count = declined_count = pending_count = maybe_count = checked_in_count = 0
            
            # Calculate response rate safely
            total_responses = accepted_count + declined_count + maybe_count
            response_rate = (total_responses / invitation_count * 100) if invitation_count > 0 else 0
            
            # Get total guest count (including +1s) with error handling
            try:
                total_guests = sum(rsvp.number_of_guests for rsvp in user_rsvps.filter(status='accepted'))
            except Exception as e:
                logger.error(f"Error calculating guest count for event {event_id}: {e}")
                total_guests = 0
            
            total_attendees = accepted_count + total_guests
            
            # Get dietary requirements with error handling
            dietary_requirements = []
            try:
                dietary_requirements = [
                    (
                        rsvp.user.email,
                        rsvp.user.get_full_name(),
                        rsvp.dietary_requirements,
                        rsvp.number_of_guests
                    )
                    for rsvp in user_rsvps.filter(status='accepted').exclude(dietary_requirements='')
                ]
            except Exception as e:
                logger.error(f"Error fetching dietary requirements for event {event_id}: {e}")
                dietary_requirements = []
            
            # Get breakaway session statistics with detailed attendee info
            session_stats = []
            try:
                sessions = BreakawaySession.objects.filter(event=event)
                for session in sessions:
                    try:
                        # Get RSVPs that selected this session
                        session_rsvps = user_rsvps.filter(
                            status='accepted',
                            selected_sessions=session
                        ).select_related('user')
                        
                        attendee_count = session_rsvps.count()
                        capacity = session.max_attendees or 0
                        capacity_pct = (attendee_count / capacity * 100) if capacity > 0 else 0
                        
                        # Get detailed attendee information
                        attendees = []
                        for rsvp in session_rsvps:
                            attendees.append({
                                'name': rsvp.user.get_full_name(),
                                'email': rsvp.user.email,
                                'number_of_guests': rsvp.number_of_guests,
                                'total_attendees': 1 + rsvp.number_of_guests,  # User + guests
                                'dietary_requirements': rsvp.dietary_requirements or 'None',
                                'rsvp_id': rsvp.id,
                            })
                        
                        # Calculate total attendees including guests
                        total_session_attendees = sum(attendee['total_attendees'] for attendee in attendees)
                        
                        session_stats.append({
                            'id': session.id,
                            'title': session.title,
                            'description': session.description,
                            'start_time': session.start_time,
                            'end_time': session.end_time,
                            'location': session.location,
                            'attendee_count': attendee_count,
                            'total_session_attendees': total_session_attendees,  # Including guests
                            'capacity': capacity,
                            'capacity_pct': capacity_pct,
                            'is_full': capacity > 0 and total_session_attendees >= capacity,
                            'attendees': attendees,
                            'available_spots': max(0, capacity - total_session_attendees) if capacity > 0 else None,
                        })
                    except Exception as e:
                        logger.error(f"Error processing session {session.id} for event {event_id}: {e}")
                        continue
            except Exception as e:
                logger.error(f"Error fetching breakaway sessions for event {event_id}: {e}")
                session_stats = []
            
            # Prepare context for template
            context = {
                'admin_site': self.admin_site,
                'title': f'RSVP Dashboard: {event.title}',
                'opts': self.model._meta,
                'event': event,
                
                # RSVP Statistics
                'invitation_count': invitation_count,
                'accepted_count': accepted_count,
                'declined_count': declined_count,
                'pending_count': pending_count,
                'maybe_count': maybe_count,
                'checked_in_count': checked_in_count,
                'response_rate': response_rate,
                'total_attendees': total_attendees,
                'dietary_requirements': dietary_requirements,
                'session_stats': session_stats,
                
                # Add links to manage RSVPs
                'rsvp_list_url': reverse('admin:events_rsvp_changelist') + f'?event__id__exact={event_id}',
                'invitee_rsvp_list_url': reverse('admin:events_inviteersvp_changelist') + f'?event__id__exact={event_id}',
            }
            
            return render(request, 'admin/events/rsvp_dashboard.html', context)
            
        except Exception as e:
            logger.error(f"Unexpected error in rsvp_dashboard for event {event_id}: {e}")
            messages.error(request, f"An error occurred while loading the RSVP dashboard: {str(e)}")
            return redirect('admin:events_event_changelist')
        
    def change_view(self, request, object_id, form_url='', extra_context=None):
        """Add a link to the RSVP dashboard in the event change view."""
        extra_context = extra_context or {}
        extra_context['show_rsvp_dashboard'] = True
        extra_context['rsvp_dashboard_url'] = reverse('admin:rsvp-dashboard', args=[object_id])
        extra_context['checkin_dashboard_url'] = reverse('admin:checkin-dashboard', args=[object_id])
        extra_context['batch_process_url'] = reverse('admin:batch-process-rsvps', args=[object_id])
        extra_context['batch_invitations_url'] = reverse('admin:batch-process-invitations', args=[object_id])
        extra_context['batch_tasks_dashboard_url'] = reverse('admin:batch-tasks-dashboard')
        return super().change_view(request, object_id, form_url, extra_context)
    
    def batch_process_rsvps(self, request, object_id):
        """Process RSVPs in batches for large events."""
        event = get_object_or_404(Event, id=object_id)
        
        if request.method == 'POST':
            action = request.POST.get('action')
            status = request.POST.get('status')
            batch_size = int(request.POST.get('batch_size', 50))
            
            # Validate inputs
            if action == 'update_status' and not status:
                messages.error(request, _("Please select a status when using the update status action."))
                return redirect('admin:batch-process-rsvps', object_id=object_id)
            
            # Generate a unique task ID
            task_id = str(uuid.uuid4())
            
            # Create task record in database
            from events.models import TaskStatus
            task = TaskStatus.create_task(
                task_id=task_id,
                task_type='rsvp',
                event_id=event.id,
                total_items=InviteeRSVP.objects.filter(event=event).count()
            )
            
            # Start the Celery task for processing RSVPs
            from events.tasks import process_rsvps_task
            process_rsvps_task.delay(task_id, event.id, action, status, batch_size)
            
            # Redirect to the monitoring page
            context = {
                'title': _('Batch Process RSVPs'),
                'opts': self.model._meta,
                'event': event,
                'task_id': task_id,
                'is_monitoring': True,
                'status_url': reverse('admin:batch-rsvp-status', args=[task_id]),
                'control_urls': {
                    'pause': reverse('admin:batch-rsvp-control', args=[task_id, 'pause']),
                    'resume': reverse('admin:batch-rsvp-control', args=[task_id, 'resume']),
                    'stop': reverse('admin:batch-rsvp-control', args=[task_id, 'stop']),
                },
            }
            
            return render(request, 'admin/events/batch_process_rsvps.html', context)
        
        # Initial page load (GET request)
        total_count = InviteeRSVP.objects.filter(event=event).count()
        pending_count = InviteeRSVP.objects.filter(event=event, status='pending').count()
        accepted_count = InviteeRSVP.objects.filter(event=event, status='accepted').count()
        declined_count = InviteeRSVP.objects.filter(event=event, status='declined').count()
        
        batch_sizes = [50, 100, 200, 500]
        
        context = {
            'title': _('Batch Process RSVPs'),
            'opts': self.model._meta,
            'event': event,
            'total_count': total_count,
            'pending_count': pending_count, 
            'accepted_count': accepted_count,
            'declined_count': declined_count,
            'batch_sizes': batch_sizes,
            'default_batch_size': 100,
            'is_monitoring': False,
        }
        
        return render(request, 'admin/events/batch_process_rsvps.html', context)
    
    def batch_process_rsvps_task(self, task_id, event_id, action, status_value, batch_size):
        """Background task to process RSVPs in batches."""
        logger.info(f"Starting RSVP batch task {task_id} for event: {event_id}")
        
        try:
            # Get event and base queryset
            event = Event.objects.get(id=event_id)
            invitee_rsvps_base = InviteeRSVP.objects.filter(event=event).order_by('invitee__email')
            total_count = invitee_rsvps_base.count()
            
            # Get task status from cache
            task_status = cache.get(f'rsvp_task_{task_id}')
            if not task_status:
                logger.error(f"No task status found for task {task_id}")
                return
            
            # Process RSVPs in chunks of batch_size
            offset = 0
            processed_count = 0
            
            while offset < total_count:
                # Check if the task has been paused or stopped
                task_status = cache.get(f'rsvp_task_{task_id}')
                if not task_status:
                    logger.error(f"Task status lost for task {task_id}")
                    return
                
                # Handle task control actions
                if task_status['status'] == 'pause':
                    logger.info(f"Task {task_id} paused at offset {offset}")
                    # Wait and check again
                    time.sleep(2)
                    continue
                elif task_status['status'] == 'stop':
                    logger.info(f"Task {task_id} stopped at offset {offset}")
                    
                    # Update final status
                    task_status.update({
                        'type': 'complete',
                        'progress': int(processed_count / total_count * 100) if total_count > 0 else 100,
                        'processed': processed_count,
                        'status': 'stopped'
                    })
                    cache.set(f'rsvp_task_{task_id}', task_status, timeout=3600)
                    return
                
                # Get current batch
                current_batch_size = min(batch_size, total_count - offset)
                
                if action == 'remind':
                    # Only get pending RSVPs for reminders
                    current_batch = invitee_rsvps_base.filter(status='pending')[offset:offset+current_batch_size]
                    emails_sent = self._process_rsvp_reminders(event, current_batch)
                    
                    logger.info(f"Task {task_id}: Sent {emails_sent} reminders (batch starting at {offset})")
                    
                elif action == 'update_status':
                    # Update status for all RSVPs in batch
                    current_batch = invitee_rsvps_base[offset:offset+current_batch_size]
                    updated = self._update_rsvp_statuses(current_batch, status_value)
                    
                    logger.info(f"Task {task_id}: Updated {updated} RSVPs to '{status_value}' (batch starting at {offset})")
                
                # Update progress
                batch_count = current_batch.count()
                processed_count += batch_count
                progress = int(processed_count / total_count * 100) if total_count > 0 else 100
                
                # Update task status
                task_status.update({
                    'type': 'update_progress',
                    'progress': progress,
                    'processed': processed_count,
                    'total': total_count,
                    'offset': offset + batch_count,
                    'batch_count': batch_count
                })
                cache.set(f'rsvp_task_{task_id}', task_status, timeout=3600)
                
                offset += batch_size
            
            # All done - update final status
            task_status.update({
                'type': 'complete',
                'progress': 100,
                'processed': processed_count,
                'status': 'complete'
            })
            cache.set(f'rsvp_task_{task_id}', task_status, timeout=3600)
            
            logger.info(f"Task {task_id} completed successfully. Processed {processed_count} RSVPs.")
            
        except Exception as e:
            logger.error(f"Error in RSVP batch task {task_id}: {str(e)}")
            
            # Update task status with error
            cache.set(f'rsvp_task_{task_id}', {
                'type': 'error',
                'error': str(e),
                'status': 'error'
            }, timeout=3600)
    
    def _process_rsvp_reminders(self, event, rsvps):
        """Process RSVP reminders for a batch of RSVPs."""
        emails_sent = 0
        
        # Get the reminder template
        reminder_template = EmailTemplate.objects.filter(name__icontains='reminder').first()
        if not reminder_template:
            reminder_template = EmailTemplate.objects.filter(is_default=True).first()
        
        if not reminder_template:
            logger.error("No email template found for reminders")
            return 0
        
        for invitee_rsvp in rsvps:
            invitee = invitee_rsvp.invitee
            try:
                # Generate RSVP URLs
                rsvp_urls = self.get_rsvp_urls(event.id, invitee.email)
                
                # Generate calendar links for email
                from .utils import get_calendar_email_html
                calendar_links_html = get_calendar_email_html(event, settings.SITE_URL.rstrip('/'))
                
                # Set up context for template
                context = Context({
                    'first_name': invitee.first_name or 'Guest',
                    'last_name': invitee.last_name or '',
                    'event': event,
                    'rsvp_accept_url': rsvp_urls['accept'],
                    'rsvp_decline_url': rsvp_urls['decline'],
                    'calendar_links': calendar_links_html,
                    'SITE_URL': settings.SITE_URL.rstrip('/')
                })
                
                # Render the template - for reminders, we may want to prefix the subject
                subject = "Reminder: " + Template(reminder_template.subject).render(context)
                message = Template(reminder_template.content).render(context)
                
                # Send email
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
                
            except Exception as e:
                logger.error(f"Error sending reminder to {invitee.email}: {str(e)}")
        
        return emails_sent
    
    def _update_rsvp_statuses(self, rsvps, status):
        """Update RSVP statuses for a batch of RSVPs."""
        updated = 0
        
        for rsvp in rsvps:
            try:
                rsvp.status = status
                rsvp.timestamp = timezone.now()
                rsvp.save()
                updated += 1
            except Exception as e:
                logger.error(f"Error updating RSVP for {rsvp.invitee.email}: {str(e)}")
        
        return updated

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
                            
                            # Generate calendar links for email
                            from .utils import get_calendar_email_html
                            calendar_links_html = get_calendar_email_html(event, settings.SITE_URL.rstrip('/'))
                            
                            context = Context({
                                'first_name': invitee.first_name or 'Guest',
                                'last_name': invitee.last_name or '',
                                'event': event,
                                'rsvp_accept_url': rsvp_urls['accept'],
                                'rsvp_decline_url': rsvp_urls['decline'],
                                'calendar_links': calendar_links_html,
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

    def export_dietary_requirements(self, request, event_id):
        """Export dietary requirements to CSV."""
        event = get_object_or_404(Event, id=event_id)
        
        # Get all RSVPs with dietary requirements
        rsvps_with_dietary = RSVP.objects.filter(
            event=event,
            status='accepted'
        ).exclude(dietary_requirements='')
        
        # Prepare CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="dietary_requirements_{event.title.replace(" ", "_")}_{datetime.now().strftime("%Y%m%d")}.csv"'
        
        writer = csv.writer(response)
        writer.writerow([
            'Email',
            'Name',
            'Dietary Requirements',
            'Number of Guests',
            'Total Portions',
            'Notes'
        ])
        
        for rsvp in rsvps_with_dietary:
            # Calculate total portions (person + guests)
            total_portions = 1 + rsvp.number_of_guests
            
            writer.writerow([
                rsvp.user.email,
                rsvp.user.get_full_name(),
                rsvp.dietary_requirements,
                rsvp.number_of_guests,
                total_portions,
                rsvp.notes
            ])
        
        return response

    def batch_process_invitations(self, request, object_id):
        """Batch process invitations for an event."""
        # Make sure the event exists
        try:
            event = Event.objects.get(pk=object_id)
        except Event.DoesNotExist:
            self.message_user(request, "Event not found", level=messages.ERROR)
            return HttpResponseRedirect(reverse('admin:events_event_changelist'))
            
        # Check that the event has invitations configured
        if not event.invitations.exists():
            self.message_user(
                request, 
                "This event has no invitations configured. Please add user lists to the event first.", 
                level=messages.ERROR
            )
            return HttpResponseRedirect(
                reverse('admin:events_event_change', args=[object_id])
            )
            
        # Count total invitees across all user lists for this event
        total_invitees = 0
        for invitation in event.invitations.all():
            total_invitees += invitation.user_list.invitees.count()
        
        context = {
            'event': event,
            'total_invitees': total_invitees,
            'batch_sizes': [10, 25, 50, 100, 250, 500],
            'default_batch_size': 100,
            'title': "Batch Process Invitations",
            'opts': self.model._meta,
        }
        
        # If this is a POST request, start the batch processing
        if request.method == 'POST':
            batch_size = int(request.POST.get('batch_size', 100))
            
            # Generate a task ID for tracking
            task_id = str(uuid.uuid4())
            logger.info(f"Starting batch invitation task {task_id} for event {event.id}")
            
            # Create a task in the database
            from events.models import TaskStatus
            task = TaskStatus.create_task(
                task_id=task_id,
                task_type='invitation',
                event_id=event.id,
                total_items=total_invitees
            )
            logger.info(f"Created task status record: {task}")
            
            # Start the Celery task
            from events.tasks import process_invitations_task
            process_invitations_task.delay(task_id, event.id, batch_size)
            
            # Update context for the monitoring template
            context.update({
                'is_monitoring': True,
                'task_id': task_id,
                'status_url': reverse('admin:batch-invitation-status', args=[task_id]),
                'control_urls': {
                    'pause': reverse('admin:batch-invitation-control', args=[task_id, 'pause']),
                    'resume': reverse('admin:batch-invitation-control', args=[task_id, 'resume']),
                    'stop': reverse('admin:batch-invitation-control', args=[task_id, 'stop']),
                },
            })
            
            logger.info(f"Started Celery task for invitations with ID: {task_id}")
            
            return render(request, 'admin/events/batch_process_invitations.html', context)
            
        # Initial form display
        return render(request, 'admin/events/batch_process_invitations.html', context)

    def _update_task_status(self, task_id, **kwargs):
        """Helper method to update task status in the database."""
        from events.models import TaskStatus
        return TaskStatus.update_task(task_id, **kwargs)
    
    def batch_process_invitations_task(self, task_id, event_id, batch_size):
        """Background task to process invitations in batches."""
        logger.info(f"======== STARTED invitation batch task {task_id} for event: {event_id} ========")
        
        try:
            # Import here to avoid circular imports
            from events.models import TaskStatus, Event, EmailTemplate, InviteeRSVP
            
            # Get event
            event = Event.objects.get(id=event_id)
            logger.info(f"Processing event: {event.title} (ID: {event_id})")
            
            # Set the thread name for easier identification in logs
            threading.current_thread().name = f"Invitation-Batch-{task_id[:8]}"
            
            # Double check that the task exists in the database
            task = TaskStatus.get_task(task_id)
            if not task:
                logger.error(f"CRITICAL ERROR: Task not found in database for task {task_id}")
                # Create a new one as a fallback
                task = TaskStatus.create_task(
                    task_id=task_id,
                    task_type='invitation',
                    event_id=event_id,
                    total_items=0
                )
                logger.info(f"Created new task status record: {task}")
            
            # Update status to indicate we're collecting invitees
            self._update_task_status(task_id, message='Gathering invitees...')
            
            # Collect all invitees from all user lists for this event
            invitees = []
            invitee_map = {}
            
            for invitation in event.invitations.all():
                list_invitees = invitation.user_list.invitees.all()
                template = invitation.email_template or EmailTemplate.objects.filter(is_default=True).first()
                logger.info(f"Processing invitation for list: {invitation.user_list.name} with {list_invitees.count()} invitees")
                
                if not template:
                    error_msg = "No email template found. Please create a default template or assign one to the invitation."
                    logger.error(error_msg)
                    self._update_task_status(
                        task_id,
                        status='error',
                        error=error_msg,
                        message=error_msg
                    )
                    return
                
                for invitee in list_invitees:
                    # Skip if no email
                    if not invitee.email:
                        logger.warning(f"Skipping invitee without email in list: {invitation.user_list.name}")
                        continue
                    
                    # Use the most recent invitation if an email appears in multiple lists
                    if invitee.email in invitee_map:
                        logger.info(f"Skipping duplicate invitee email: {invitee.email}")
                        continue
                    
                    invitee_map[invitee.email] = {
                        'invitee': invitee,
                        'template': template
                    }
                    invitees.append(invitee)
            
            # Update total count
            total_count = len(invitees)
            logger.info(f"Found {total_count} unique invitees to process")
            
            # Handle case with zero invitees
            if total_count == 0:
                logger.warning(f"No invitees found to process")
                self._update_task_status(
                    task_id,
                    status='complete',
                    progress=100,
                    processed=0,
                    total=0,
                    emails_sent=0,
                    failed=0,
                    message='No invitees found to process'
                )
                return
            
            # Update status with total count
            self._update_task_status(
                task_id,
                total=total_count,
                message=f'Found {total_count} invitees to process'
            )
            
            # Process invitees in chunks of batch_size
            offset = 0
            processed_count = 0
            emails_sent = 0
            failed_emails = []
            
            # Check if we're resuming from a pause
            task = TaskStatus.get_task(task_id)
            if task and task.status == 'resume' and task.offset > 0:
                offset = task.offset
                processed_count = task.processed
                emails_sent = task.emails_sent
                logger.info(f"Resuming from offset: {offset}, processed: {processed_count}, emails sent: {emails_sent}")
                
                # Update status to running
                self._update_task_status(
                    task_id, 
                    status='running',
                    message=f'Resuming from {processed_count} of {total_count} invitees. Sent {emails_sent} emails so far.'
                )
            
            # Main processing loop
            while offset < total_count:
                # Get the latest task status
                task = TaskStatus.get_task(task_id)
                if not task:
                    logger.error(f"Lost task status during execution for task {task_id}")
                    return
                
                # Handle task control actions
                current_status = task.status
                logger.info(f"Current task status: {current_status}, offset: {offset}/{total_count}")
                
                if current_status == 'pause':
                    logger.info(f"Task {task_id} paused at offset {offset}/{total_count}")
                    
                    # Make sure we properly indicate we're paused
                    self._update_task_status(
                        task_id,
                        status='pause',
                        message=f'Process paused at {processed_count} of {total_count} invitees.',
                        offset=offset
                    )
                    
                    # Wait and check if status changes
                    logger.info(f"Waiting in paused state...")
                    time.sleep(5)  # Wait longer between checks when paused
                    
                    # Continue to the next iteration of the main loop
                    continue
                    
                elif current_status == 'stop':
                    logger.info(f"Task {task_id} stopped at offset {offset}")
                    
                    # Update final status
                    self._update_task_status(
                        task_id,
                        status='stopped',
                        progress=int(processed_count / total_count * 100) if total_count > 0 else 100,
                        processed=processed_count,
                        emails_sent=emails_sent,
                        failed=len(failed_emails),
                        message='Process was stopped manually',
                        offset=offset
                    )
                    return
                
                # Get current batch
                current_batch_size = min(batch_size, total_count - offset)
                current_batch = invitees[offset:offset+current_batch_size]
                batch_emails_sent = 0
                
                logger.info(f"Processing batch starting at {offset}, size: {len(current_batch)}")
                
                # Process current batch
                for idx, invitee in enumerate(current_batch):
                    # Check status again before each email to quickly respond to pause/stop
                    if idx % 5 == 0:  # Check every 5 emails
                        latest_task = TaskStatus.get_task(task_id)
                        if latest_task and latest_task.status in ['pause', 'stop']:
                            logger.info(f"Detected {latest_task.status} command during batch processing. Breaking out of batch.")
                            break
                    
                    invitee_data = invitee_map[invitee.email]
                    template = invitee_data['template']
                    
                    # Log every 10th invitee or the first/last for visibility
                    should_log = (idx % 10 == 0) or (idx == 0) or (idx == len(current_batch) - 1)
                    log_prefix = f"[{offset+idx+1}/{total_count}] Processing invitee {invitee.email}"
                    
                    if should_log:
                        logger.info(f"{log_prefix} - starting")
                    
                    try:
                        # Check if RSVP already exists
                        existing_rsvp, created = InviteeRSVP.objects.get_or_create(
                            event=event,
                            invitee=invitee,
                            defaults={'status': 'pending', 'token': uuid.uuid4()}
                        )
                        
                        # Generate RSVP URLs
                        rsvp_urls = self.get_rsvp_urls(event.id, invitee.email)
                        
                        # Generate calendar links for email
                        from .utils import get_calendar_email_html
                        calendar_links_html = get_calendar_email_html(event, settings.SITE_URL.rstrip('/'))
                        
                        # Set up context for template
                        context = Context({
                            'first_name': invitee.first_name or 'Guest',
                            'last_name': invitee.last_name or '',
                            'event': event,
                            'rsvp_accept_url': rsvp_urls['accept'],
                            'rsvp_decline_url': rsvp_urls['decline'],
                            'calendar_links': calendar_links_html,
                            'SITE_URL': settings.SITE_URL.rstrip('/')
                        })
                        
                        # Render templates
                        subject = Template(template.subject).render(context)
                        message = Template(template.content).render(context)
                        
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
                        batch_emails_sent += 1
                        
                        if should_log:
                            logger.info(f"{log_prefix} - email sent successfully")
                        
                    except Exception as e:
                        error_msg = str(e)
                        logger.error(f"{log_prefix} - failed: {error_msg}")
                        failed_emails.append({
                            'email': invitee.email,
                            'error': error_msg
                        })
                    
                    # Update progress every 5 invitees within the batch or on the last one
                    if (idx + 1) % 5 == 0 or idx == len(current_batch) - 1:
                        processed_count = offset + idx + 1
                        progress = int(processed_count / total_count * 100) if total_count > 0 else 100
                        
                        # Check if we've been asked to pause or stop during progress update
                        latest_task = TaskStatus.get_task(task_id)
                        if latest_task and latest_task.status in ['pause', 'stop']:
                            logger.info(f"Detected {latest_task.status} command during progress update.")
                            break
                        
                        # Only update status if we're still allowed to
                        current_status = latest_task.status if latest_task else 'running'
                        if current_status not in ['complete', 'stopped', 'error', 'pause']:
                            # Update task status
                            self._update_task_status(
                                task_id,
                                progress=progress,
                                processed=processed_count,
                                emails_sent=emails_sent,
                                failed=len(failed_emails),
                                offset=offset + idx + 1,
                                message=f'Processed {processed_count} of {total_count} invitees. Sent {emails_sent} emails.'
                            )
                        
                        logger.info(f"Updated progress: {progress}%, processed: {processed_count}/{total_count}")
                
                # Check if we broke out of the loop due to pause or stop
                latest_task = TaskStatus.get_task(task_id)
                if latest_task and latest_task.status in ['pause', 'stop']:
                    logger.info(f"Not incrementing offset due to {latest_task.status} status")
                    # Break out of the main loop if stopped
                    if latest_task.status == 'stop':
                        logger.info(f"Breaking out of main loop due to stop command")
                        break
                    # Continue to the next iteration of the main loop, which will handle pause again
                    continue
                else:
                    # Only increment offset if we processed the entire batch
                    offset += current_batch_size
                
                # Log batch completion
                logger.info(f"Completed batch starting at {offset-current_batch_size}, sent {batch_emails_sent} emails, failed: {len(failed_emails)}")
            
            # For consistent reporting, make sure we have accurate counts
            final_message = f'Process completed. Sent {emails_sent} emails to {processed_count} invitees.'
            if len(failed_emails) > 0:
                final_message += f' {len(failed_emails)} failed.'
            
            # All done - update final status
            latest_task = TaskStatus.get_task(task_id)
            current_status = latest_task.status if latest_task else 'running'
            
            if current_status not in ['stopped', 'error', 'pause']:
                self._update_task_status(
                    task_id,
                    status='complete',
                    progress=100,
                    processed=processed_count,
                    emails_sent=emails_sent,
                    failed=len(failed_emails),
                    message=final_message,
                    offset=offset
                )
            elif current_status == 'pause':
                # Just update the counts but keep paused status
                self._update_task_status(
                    task_id,
                    processed=processed_count,
                    emails_sent=emails_sent,
                    failed=len(failed_emails),
                    message=f'Process paused at {processed_count} of {total_count} invitees.',
                    offset=offset
                )
            
            logger.info(f"======== COMPLETED task {task_id} successfully. Sent {emails_sent} invitations, failed {len(failed_emails)}. ========")
            
        except Exception as e:
            logger.error(f"CRITICAL ERROR in invitation batch task {task_id}: {str(e)}", exc_info=True)
            
            # Update task status with error
            from events.models import TaskStatus
            TaskStatus.update_task(
                task_id,
                status='error',
                error=str(e),
                message=f'Error: {str(e)}'
            )
            logger.info(f"Set error status in database")

    def batch_rsvp_status(self, request, task_id):
        """Return the current status of the RSVP batch processing task."""
        try:
            from events.models import TaskStatus
            task = TaskStatus.get_task(task_id)
            
            if not task:
                logger.warning(f"No status found for task {task_id}")
                return JsonResponse({
                    'type': 'unknown',
                    'progress': 0,
                    'processed': 0,
                    'total': 0,
                    'status': 'unknown',
                    'message': 'Task status not found'
                })
                
            # Return serializable dict of task status
            status_data = {
                'type': 'update_progress',
                'progress': task.progress,
                'processed': task.processed,
                'total': task.total,
                'status': task.status,
                'message': task.message,
                'last_update_time': task.updated_at.isoformat()
            }
            
            # Include any additional data
            if task.additional_data:
                for key, value in task.additional_data.items():
                    if key not in status_data:
                        status_data[key] = value
            
            return JsonResponse(status_data)
            
        except Exception as e:
            logger.error(f"Error retrieving status for task {task_id}: {str(e)}", exc_info=True)
            # Return a safe fallback
            return JsonResponse({
                'type': 'error',
                'status': 'error',
                'message': f'Server error: {str(e)}',
                'error': str(e)
            })
    
    def batch_rsvp_control(self, request, task_id, action):
        """Control the RSVP batch processing task (pause, resume, stop)."""
        try:
            from events.models import TaskStatus
            
            valid_actions = ['pause', 'resume', 'stop']
            if action not in valid_actions:
                logger.warning(f"Invalid action requested: {action}")
                return JsonResponse({'error': f'Invalid action: {action}'}, status=400)
            
            # Get the current task
            task = TaskStatus.get_task(task_id)
            if not task:
                logger.error(f"Task not found in database: {task_id}")
                return JsonResponse({'error': 'Task not found'}, status=404)
            
            # Keep track of the previous status
            prev_status = task.status
            
            # Translate 'stop' action to 'stopped' status
            status_to_set = 'stopped' if action == 'stop' else action
            
            # Update the task
            task = TaskStatus.update_task(
                task_id, 
                status=status_to_set,
                message=f'Status changed from {prev_status} to {status_to_set}'
            )
            
            if not task:
                logger.error(f"Failed to update task {task_id}")
                return JsonResponse({'error': 'Failed to update task status'}, status=500)
                
            logger.info(f"Control: Changed task {task_id} status from {prev_status} to {status_to_set}")
            
            # Add response data
            return JsonResponse({
                'success': True, 
                'status': status_to_set,
                'previous_status': prev_status,
                'timestamp': task.updated_at.isoformat()
            })
            
        except Exception as e:
            logger.error(f"Error updating task control status: {str(e)}", exc_info=True)
            return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)
    
    def batch_invitation_status(self, request, task_id):
        """Return the current status of the invitation batch processing task."""
        # Retrieve the task status from database
        logger.debug(f"Status request received for task {task_id}")
        
        try:
            from events.models import TaskStatus
            task = TaskStatus.get_task(task_id)
            
            if not task:
                logger.warning(f"No status found for task {task_id}")
                return JsonResponse({
                    'type': 'unknown',
                    'progress': 0,
                    'processed': 0,
                    'total': 0,
                    'emails_sent': 0,
                    'failed': 0,
                    'status': 'unknown',
                    'message': 'Task status not found - the task may have expired or never started'
                })
                
            # Return serializable dict of task status
            status_data = {
                'type': 'update_progress',
                'progress': task.progress,
                'processed': task.processed,
                'total': task.total,
                'emails_sent': task.emails_sent,
                'failed': task.failed,
                'status': task.status,
                'message': task.message,
                'last_update_time': task.updated_at.isoformat()
            }
            
            # Include any additional data
            if task.additional_data:
                for key, value in task.additional_data.items():
                    if key not in status_data:
                        status_data[key] = value
            
            logger.debug(f"Sending batch invitation status response: {status_data}")
            return JsonResponse(status_data)
            
        except Exception as e:
            logger.error(f"Error retrieving status for task {task_id}: {str(e)}", exc_info=True)
            # Return a safe fallback
            return JsonResponse({
                'type': 'error',
                'status': 'error',
                'message': f'Server error: {str(e)}',
                'error': str(e)
            })
            
    def batch_invitation_control(self, request, task_id, action):
        """Control the invitation batch processing task (pause, resume, stop)."""
        logger.info(f"Control request received for task {task_id}, action: {action}")
        
        try:
            from events.models import TaskStatus
            
            valid_actions = ['pause', 'resume', 'stop']
            if action not in valid_actions:
                logger.warning(f"Invalid action requested: {action}")
                return JsonResponse({'error': f'Invalid action: {action}'}, status=400)
            
            # Get the current task
            task = TaskStatus.get_task(task_id)
            if not task:
                logger.error(f"Task not found in database: {task_id}")
                return JsonResponse({'error': 'Task not found'}, status=404)
            
            # Keep track of the previous status
            prev_status = task.status
            
            # Special handling for resume to ensure we keep important fields
            if action == 'resume' and prev_status == 'pause':
                logger.info(f"Resuming task from offset: {task.offset}, " +
                           f"processed: {task.processed}, emails: {task.emails_sent}")
            
            # Translate 'stop' action to 'stopped' status
            status_to_set = 'stopped' if action == 'stop' else action
            
            # Update the task
            task = TaskStatus.update_task(
                task_id, 
                status=status_to_set,
                message=f'Status changed from {prev_status} to {status_to_set}'
            )
            
            if not task:
                logger.error(f"Failed to update task {task_id}")
                return JsonResponse({'error': 'Failed to update task status'}, status=500)
                
            logger.info(f"Control: Changed task {task_id} status from {prev_status} to {status_to_set}")
            
            # Add response data
            response_data = {
                'success': True, 
                'status': status_to_set,
                'previous_status': prev_status,
                'timestamp': task.updated_at.isoformat(),
                'verified': True
            }
            
            # Add offset info for resume actions
            if action == 'resume':
                response_data['resume_from_offset'] = task.offset
                response_data['resume_emails_sent'] = task.emails_sent
                response_data['resume_processed'] = task.processed
            
            return JsonResponse(response_data)
            
        except Exception as e:
            logger.error(f"Error updating task control status: {str(e)}", exc_info=True)
            return JsonResponse({'error': f'Server error: {str(e)}'}, status=500)

    def test_cache_connection(self, request):
        """Test the cache connection to diagnose issues."""
        logger.info("Testing cache connection...")
        
        # Create a unique test key
        test_key = f'cache_test_{uuid.uuid4()}'
        test_value = {
            'timestamp': timezone.now().isoformat(),
            'value': 'test value'
        }
        
        # Try to store a value
        try:
            cache.set(test_key, test_value, timeout=60)
            logger.info(f"Successfully set test value in cache with key: {test_key}")
            
            # Try to retrieve the value
            retrieved = cache.get(test_key)
            if retrieved == test_value:
                logger.info("Successfully retrieved test value from cache")
                success = True
            else:
                logger.error(f"Cache retrieval failed! Expected {test_value}, got {retrieved}")
                success = False
                
            # Clean up
            cache.delete(test_key)
            
            return JsonResponse({
                'success': success,
                'test_key': test_key,
                'expected': test_value,
                'retrieved': retrieved
            })
            
        except Exception as e:
            logger.error(f"Cache test failed with error: {str(e)}", exc_info=True)
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)

    def batch_tasks_dashboard(self, request):
        """Dashboard to view and manage all batch tasks."""
        # Get all task records from the database
        from events.models import TaskStatus, Event

        # Filter tasks based on query parameters
        task_type = request.GET.get('task_type')
        status = request.GET.get('status')
        event_id = request.GET.get('event_id')
        
        tasks = TaskStatus.objects.all()
        
        if task_type:
            tasks = tasks.filter(task_type=task_type)
        if status:
            tasks = tasks.filter(status=status)
        if event_id:
            tasks = tasks.filter(event_id=event_id)
            
        # Get events for the filter dropdown
        events = Event.objects.filter(id__in=tasks.values_list('event_id', flat=True).distinct())
        
        # Count tasks by status
        running_count = tasks.filter(status='running').count()
        paused_count = tasks.filter(status='pause').count()
        completed_count = tasks.filter(status='complete').count()
        error_count = tasks.filter(status='error').count()
        stopped_count = tasks.filter(status='stopped').count()
        
        # Add event details to each task
        tasks_with_events = []
        for task in tasks:
            event = None
            try:
                event = Event.objects.get(id=task.event_id)
            except Event.DoesNotExist:
                pass
                
            tasks_with_events.append({
                'task': task,
                'event': event,
                'control_urls': {
                    'pause': reverse('admin:batch-invitation-control', args=[task.task_id, 'pause']) 
                            if task.task_type == 'invitation' else 
                            reverse('admin:batch-rsvp-control', args=[task.task_id, 'pause']),
                    'resume': reverse('admin:batch-invitation-control', args=[task.task_id, 'resume']) 
                            if task.task_type == 'invitation' else 
                            reverse('admin:batch-rsvp-control', args=[task.task_id, 'resume']),
                    'stop': reverse('admin:batch-invitation-control', args=[task.task_id, 'stop']) 
                            if task.task_type == 'invitation' else 
                            reverse('admin:batch-rsvp-control', args=[task.task_id, 'stop'])
                },
                'status_url': reverse('admin:batch-invitation-status', args=[task.task_id])
                               if task.task_type == 'invitation' else
                               reverse('admin:batch-rsvp-status', args=[task.task_id]),
                'can_pause': task.status == 'running',
                'can_resume': task.status == 'pause',
                'can_stop': task.status in ['running', 'pause'],
                'age_minutes': int((timezone.now() - task.created_at).total_seconds() / 60)
            })
        
        context = {
            # Use 'Page Title' format for admin
            'title': 'Batch Tasks Dashboard',
            'app_label': 'events',
            'opts': self.model._meta,
            'tasks': tasks_with_events,
            'events': events,
            'task_types': dict(TaskStatus.TASK_TYPES),
            'statuses': dict(TaskStatus.STATUS_CHOICES),
            'current_filters': {
                'task_type': task_type,
                'status': status,
                'event_id': event_id
            },
            'running_count': running_count,
            'paused_count': paused_count,
            'completed_count': completed_count,
            'error_count': error_count,
            'stopped_count': stopped_count
        }
        
        return render(request, 'admin/events/batch_tasks_dashboard.html', context)


@admin.register(BreakawaySession)
class BreakawaySessionAdmin(admin.ModelAdmin):
    list_display = ('title', 'event', 'start_time', 'end_time', 'get_attendee_count')
    list_filter = ('event',)
    search_fields = ('title', 'description')
    filter_horizontal = ('panelists',)
    readonly_fields = ('get_attendees_display',)
    
    def get_attendee_count(self, obj):
        """Display the number of attendees who selected this session"""
        count = obj.attendees.filter(status='accepted').count()
        total_with_guests = sum(
            1 + rsvp.number_of_guests 
            for rsvp in obj.attendees.filter(status='accepted')
        )
        return f"{count} attendees ({total_with_guests} total incl. guests)"
    get_attendee_count.short_description = 'Attendees'
    
    def get_attendees_display(self, obj):
        """Display formatted list of attendees who selected this session"""
        if not obj.pk:
            return "Save the session first to see attendees."
        
        # Get all accepted RSVPs that selected this session
        attendees = obj.attendees.filter(status='accepted').select_related('user').order_by('user__first_name', 'user__last_name')
        
        if not attendees.exists():
            return mark_safe('<div style="padding: 20px; background-color: #1a1a1a; border-radius: 4px; border: 1px solid #555;"><p style="font-style: italic; color: #ccc; margin: 0; text-align: center;">No attendees have selected this session yet.</p></div>')
        
        # Calculate totals
        total_registrations = attendees.count()
        total_with_guests = sum(1 + rsvp.number_of_guests for rsvp in attendees)
        
        # Build HTML display
        html_parts = [
            f'<div style="margin-bottom: 15px; color: #fff;"><strong>Session Attendees ({total_registrations} registrations, {total_with_guests} total including guests)</strong></div>',
            '<div style="max-height: 300px; overflow-y: auto; border: 1px solid #555; border-radius: 4px; background-color: #1a1a1a;">',
            '<table style="width: 100%; border-collapse: collapse; font-size: 13px; color: #fff; background-color: #1a1a1a;">',
            '<thead style="background-color: #2c2c2c; color: #fff; position: sticky; top: 0;">',
            '<tr>',
            '<th style="padding: 10px 8px; text-align: left; border-bottom: 1px solid #555; font-weight: bold; color: #fff;">Name</th>',
            '<th style="padding: 10px 8px; text-align: left; border-bottom: 1px solid #555; font-weight: bold; color: #fff;">Email</th>',
            '<th style="padding: 10px 8px; text-align: center; border-bottom: 1px solid #555; font-weight: bold; color: #fff;">Guests</th>',
            '<th style="padding: 10px 8px; text-align: center; border-bottom: 1px solid #555; font-weight: bold; color: #fff;">Total</th>',
            '<th style="padding: 10px 8px; text-align: left; border-bottom: 1px solid #555; font-weight: bold; color: #fff;">Dietary Requirements</th>',
            '</tr>',
            '</thead>',
            '<tbody>'
        ]
        
        for i, rsvp in enumerate(attendees):
            bg_color = '#1a1a1a' if i % 2 == 0 else '#2a2a2a'
            dietary = rsvp.dietary_requirements.strip() if rsvp.dietary_requirements else 'None'
            
            # Prepare dietary display
            dietary_display = dietary if dietary != "None" else '<span style="color: #888; font-style: italic;">None</span>'
            guest_display = "+" + str(rsvp.number_of_guests) if rsvp.number_of_guests > 0 else "-"
            
            html_parts.extend([
                f'<tr style="background-color: {bg_color};">',
                f'<td style="padding: 10px 8px; border-bottom: 1px solid #555; color: #fff;"><strong>{rsvp.user.get_full_name()}</strong></td>',
                f'<td style="padding: 10px 8px; border-bottom: 1px solid #555; color: #fff;"><a href="mailto:{rsvp.user.email}" style="color: #79aec8; text-decoration: none;">{rsvp.user.email}</a></td>',
                f'<td style="padding: 10px 8px; text-align: center; border-bottom: 1px solid #555; color: #fff;">{guest_display}</td>',
                f'<td style="padding: 10px 8px; text-align: center; border-bottom: 1px solid #555; color: #fff;"><strong>{1 + rsvp.number_of_guests}</strong></td>',
                f'<td style="padding: 10px 8px; border-bottom: 1px solid #555; color: #fff;">{dietary_display}</td>',
                '</tr>'
            ])
        
        # Prepare capacity status
        if obj.max_attendees and total_with_guests >= obj.max_attendees:
            capacity_status = '<span style="color: #ff6b6b; font-weight: bold;">⚠️ FULL</span>'
        elif obj.max_attendees:
            capacity_status = f'<span style="color: #51cf66;">({obj.max_attendees - total_with_guests} spots available)</span>'
        else:
            capacity_status = ''
        
        html_parts.extend([
            '</tbody>',
            '</table>',
            '</div>',
            f'<div style="margin-top: 10px; font-size: 12px; color: #ccc; padding: 8px; background-color: #2a2a2a; border-radius: 3px; border: 1px solid #555;">',
            f'<strong style="color: #fff;">Capacity:</strong> {total_with_guests}/{obj.max_attendees if obj.max_attendees else "Unlimited"} {capacity_status}',
            '</div>'
        ])
        
        return mark_safe(''.join(html_parts))
    
    get_attendees_display.short_description = 'Attendees who selected this session'


@admin.register(RSVP)
class RSVPAdmin(admin.ModelAdmin):
    list_display = ('event', 'user_info', 'status', 'response_date', 'checked_in', 'number_of_guests', 'created_at')
    list_filter = ('checked_in', 'event', 'status', 'response_date', 'created_at')
    search_fields = ('user__email', 'user__first_name', 'user__last_name', 'notes', 'dietary_requirements')
    readonly_fields = ('created_at', 'updated_at', 'qr_code', 'qr_code_data')
    filter_horizontal = ('selected_sessions',)
    actions = ['export_as_csv', 'mark_as_checked_in', 'mark_as_not_checked_in']
    date_hierarchy = 'response_date'
    list_select_related = ('user', 'event')
    list_per_page = 50
    
    fieldsets = (
        (None, {
            'fields': ('event', 'user', 'status', 'response_date')
        }),
        (_('Guest Information'), {
            'fields': ('number_of_guests', 'notes', 'dietary_requirements')
        }),
        (_('Check-in Information'), {
            'fields': ('checked_in', 'qr_code', 'qr_code_data')
        }),
        (_('Session Selection'), {
            'fields': ('selected_sessions',)
        }),
        (_('Metadata'), {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at', 'is_registered_user')
        }),
    )
    
    def user_info(self, obj):
        return f"{obj.user.get_full_name()} ({obj.user.email})"
    user_info.short_description = _("User")
    user_info.admin_order_field = 'user__email'
    
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
            'Number of Guests',
            'Dietary Requirements',
            'Notes',
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
                rsvp.event.date.strftime('%Y-%m-%d %H:%M') if rsvp.event.date else '',
                rsvp.event.location,
                rsvp.user.email,
                rsvp.user.first_name,
                rsvp.user.last_name,
                rsvp.get_status_display(),
                rsvp.response_date.strftime('%Y-%m-%d %H:%M') if rsvp.response_date else '',
                'Yes' if rsvp.checked_in else 'No',
                rsvp.number_of_guests,
                rsvp.dietary_requirements,
                rsvp.notes,
                selected_sessions
            ])
        
        return response
    
    export_as_csv.short_description = _("Export selected RSVPs to CSV")
    
    def mark_as_checked_in(self, request, queryset):
        updated = queryset.update(checked_in=True)
        self.message_user(request, _(f"{updated} RSVPs marked as checked in."))
    mark_as_checked_in.short_description = _("Mark selected RSVPs as checked in")
    
    def mark_as_not_checked_in(self, request, queryset):
        updated = queryset.update(checked_in=False)
        self.message_user(request, _(f"{updated} RSVPs marked as not checked in."))
    mark_as_not_checked_in.short_description = _("Mark selected RSVPs as not checked in")


@admin.register(InviteeRSVP)
class InviteeRSVPAdmin(admin.ModelAdmin):
    list_display = ('invitee_info', 'event', 'status', 'timestamp', 'created_at', 'email_sent', 'email_sent_at')
    list_filter = ('status', 'event', 'timestamp', 'created_at', 'email_sent')
    search_fields = ('invitee__email', 'invitee__first_name', 'invitee__last_name', 'event__title')
    readonly_fields = ('token', 'created_at', 'updated_at', 'email_sent_at')
    actions = ['export_as_csv', 'mark_as_accepted', 'mark_as_declined', 'mark_as_pending']
    date_hierarchy = 'timestamp'
    list_select_related = ('invitee', 'event')
    list_per_page = 50
    raw_id_fields = ('invitee', 'event')
    
    fieldsets = (
        (None, {
            'fields': ('invitee', 'event', 'status', 'timestamp', 'token')
        }),
        (_('Email Status'), {
            'fields': ('email_sent', 'email_sent_at'),
        }),
        (_('Metadata'), {
            'classes': ('collapse',),
            'fields': ('created_at', 'updated_at')
        }),
    )
    
    def invitee_info(self, obj):
        return f"{obj.invitee.first_name} {obj.invitee.last_name} ({obj.invitee.email})"
    invitee_info.short_description = _("Invitee")
    invitee_info.admin_order_field = 'invitee__email'
    
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
            'Email Sent',
            'Email Sent At',
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
                invitee_rsvp.event.date.strftime('%Y-%m-%d %H:%M') if invitee_rsvp.event.date else '',
                invitee_rsvp.event.location,
                invitee_rsvp.invitee.email,
                invitee_rsvp.invitee.first_name,
                invitee_rsvp.invitee.last_name,
                invitee_rsvp.get_status_display(),
                invitee_rsvp.timestamp.strftime('%Y-%m-%d %H:%M') if invitee_rsvp.timestamp else '',
                'Yes' if invitee_rsvp.email_sent else 'No',
                invitee_rsvp.email_sent_at.strftime('%Y-%m-%d %H:%M') if invitee_rsvp.email_sent_at else '',
                invitee_rsvp.created_at.strftime('%Y-%m-%d %H:%M'),
                invitee_rsvp.updated_at.strftime('%Y-%m-%d %H:%M')
            ])
        
        return response
    
    export_as_csv.short_description = _("Export selected InviteeRSVPs to CSV")
    
    def mark_as_accepted(self, request, queryset):
        updated = queryset.update(status='accepted', timestamp=timezone.now())
        self.message_user(request, _(f"{updated} Invitee RSVPs marked as accepted."))
    mark_as_accepted.short_description = _("Mark selected Invitee RSVPs as accepted")
    
    def mark_as_declined(self, request, queryset):
        updated = queryset.update(status='declined', timestamp=timezone.now())
        self.message_user(request, _(f"{updated} Invitee RSVPs marked as declined."))
    mark_as_declined.short_description = _("Mark selected Invitee RSVPs as declined")
    
    def mark_as_pending(self, request, queryset):
        updated = queryset.update(status='pending', timestamp=None)
        self.message_user(request, _(f"{updated} Invitee RSVPs marked as pending."))
    mark_as_pending.short_description = _("Mark selected Invitee RSVPs as pending")

# Add a separate entry for Batch Tasks in the admin sidebar
class BatchTasksDashboard(admin.ModelAdmin):
    model = TaskStatus
    
    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path(
                '',
                self.admin_site.admin_view(self.dashboard_view),
                name='batch-tasks-dashboard-link',
            ),
        ]
        return custom_urls + urls
    
    def dashboard_view(self, request):
        """Redirect to the batch tasks dashboard view."""
        return redirect('admin:batch-tasks-dashboard')

# Register with a custom name to appear in the admin sidebar
admin.site.register(TaskStatus, BatchTasksDashboard)
