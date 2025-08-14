import uuid
import logging
import time
from celery import shared_task
from celery.result import AsyncResult
from django.utils import timezone
from django.conf import settings
from django.template import Template, Context
from django.utils.html import strip_tags
from django.core.mail import EmailMultiAlternatives
from django.urls import reverse
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, To
import os

from events.models import Event, EmailTemplate, InviteeRSVP, TaskStatus

logger = logging.getLogger(__name__)

# Function to check if a task is revoked
def task_is_revoked(task_id):
    """Check if a task has been revoked."""
    if not task_id:
        return False
    result = AsyncResult(task_id)
    return result.state == 'REVOKED'


@shared_task(bind=True)
def process_invitations_task(self, task_id, event_id, batch_size):
    """Celery task to process invitations in batches."""
    logger.info(f"======== STARTED invitation batch task {task_id} for event: {event_id} ========")
    
    try:
        # Get event
        event = Event.objects.get(id=event_id)
        logger.info(f"Processing event: {event.title} (ID: {event_id})")
        
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
        TaskStatus.update_task(task_id, message='Gathering invitees...')
        
        # Collect all invitees from all user lists for this event
        invitees = []
        invitee_map = {}
        
        for invitation in event.invitations.all():
            list_invitees = invitation.user_list.invitees.all()
            logger.info(f"Processing invitation for list: {invitation.user_list.name} with {list_invitees.count()} invitees")
            
            for invitee in list_invitees:
                # Skip if no email
                if not invitee.email:
                    logger.warning(f"Skipping invitee without email in list: {invitation.user_list.name}")
                    continue
                
                # Use the most recent invitation if an email appears in multiple lists
                if invitee.email in invitee_map:
                    logger.info(f"Skipping duplicate invitee email: {invitee.email}")
                    continue
                
                # Select template based on guest category
                template = None
                
                # First, try to find a category-specific template
                if invitee.guest_category in ['vip', 'vvip', 'regular']:
                    template = EmailTemplate.objects.filter(
                        guest_category=invitee.guest_category,
                        is_default=True
                    ).first()
                    
                    if template:
                        logger.info(f"Using {invitee.guest_category.upper()} template for {invitee.email}")
                
                # If no category-specific template, use the invitation's assigned template
                if not template and invitation.email_template:
                    template = invitation.email_template
                    logger.info(f"Using invitation-assigned template for {invitee.email}")
                
                # If still no template, use a general default template
                if not template:
                    template = EmailTemplate.objects.filter(
                        guest_category='all',
                        is_default=True
                    ).first()
                    
                    if template:
                        logger.info(f"Using general default template for {invitee.email}")
                
                # Final fallback to any default template
                if not template:
                    template = EmailTemplate.objects.filter(is_default=True).first()
                    logger.warning(f"Using fallback default template for {invitee.email}")
                
                if not template:
                    error_msg = "No email template found. Please create a default template or assign one to the invitation."
                    logger.error(error_msg)
                    TaskStatus.update_task(
                        task_id,
                        status='error',
                        error=error_msg,
                        message=error_msg
                    )
                    return
                
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
            TaskStatus.update_task(
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
        TaskStatus.update_task(
            task_id,
            total=total_count,
            message=f'Found {total_count} invitees to process'
        )
        
        # Process invitees in chunks of batch_size
        offset = 0
        processed_count = 0
        emails_sent = 0
        emails_skipped = 0  # New counter for skipped emails
        failed_emails = []
        
        # Check if we're resuming from a pause
        task = TaskStatus.get_task(task_id)
        if task and task.status == 'resume' and task.offset > 0:
            offset = task.offset
            processed_count = task.processed
            emails_sent = task.emails_sent
            # Add emails_skipped to additional_data if it exists
            if task.additional_data and 'emails_skipped' in task.additional_data:
                emails_skipped = task.additional_data.get('emails_skipped', 0)
            logger.info(f"Resuming from offset: {offset}, processed: {processed_count}, emails sent: {emails_sent}, emails skipped: {emails_skipped}")
            
            # Update status to running immediately to prevent resume loop
            TaskStatus.update_task(
                task_id, 
                status='running',
                message=f'Resuming from {processed_count} of {total_count} invitees. Sent {emails_sent} emails so far.',
                additional_data={'emails_skipped': emails_skipped}
            )
        
        # Main processing loop
        while offset < total_count:
            # Check if the task has been revoked or terminated
            if task_is_revoked(self.request.id):
                logger.info(f"Task {task_id} was revoked")
                TaskStatus.update_task(
                    task_id,
                    status='stopped',
                    message='Task was revoked',
                    additional_data={'emails_skipped': emails_skipped}
                )
                return
                
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
                TaskStatus.update_task(
                    task_id,
                    status='pause',
                    message=f'Process paused at {processed_count} of {total_count} invitees.',
                    offset=offset,
                    additional_data={'emails_skipped': emails_skipped}
                )
                
                # Wait and check if status changes
                logger.info(f"Waiting in paused state...")
                time.sleep(5)  # Wait longer between checks when paused
                
                # Continue to the next iteration of the main loop
                continue
                
            elif current_status == 'stop':
                logger.info(f"Task {task_id} stopped at offset {offset}")
                
                # Update final status
                TaskStatus.update_task(
                    task_id,
                    status='stopped',
                    progress=int(processed_count / total_count * 100) if total_count > 0 else 100,
                    processed=processed_count,
                    emails_sent=emails_sent,
                    failed=len(failed_emails),
                    message='Process was stopped manually',
                    offset=offset,
                    additional_data={'emails_skipped': emails_skipped}
                )
                return
            
            # Get current batch
            current_batch_size = min(batch_size, total_count - offset)
            current_batch = invitees[offset:offset+current_batch_size]
            batch_emails_sent = 0
            batch_emails_skipped = 0
            
            logger.info(f"Processing batch starting at {offset}, size: {len(current_batch)}")
            
            # Prepare emails for batch sending
            messages_to_send = []
            
            # Process current batch
            for idx, invitee in enumerate(current_batch):
                # Check status again before each email to quickly respond to pause/stop
                if idx % 5 == 0:  # Check every 5 emails
                    latest_task = TaskStatus.get_task(task_id)
                    if latest_task and latest_task.status in ['pause', 'stop']:
                        logger.info(f"Detected {latest_task.status} command during batch processing. Breaking out of batch.")
                        break
                    
                    # Also check if the task has been revoked
                    if task_is_revoked(self.request.id):
                        logger.info(f"Task {task_id} was revoked during batch processing")
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
                    
                    # Only send email if it hasn't been sent yet
                    if existing_rsvp.email_sent:
                        logger.info(f"{log_prefix} - email already sent on {existing_rsvp.email_sent_at}, skipping")
                        emails_skipped += 1
                        batch_emails_skipped += 1
                        continue
                    
                    # Generate RSVP URLs
                    rsvp_urls = get_rsvp_urls(existing_rsvp.token, invitee.email)
                    
                    # Generate calendar links for email
                    from .utils import get_calendar_email_html
                    calendar_links_html = get_calendar_email_html(event, settings.SITE_URL.rstrip('/'))
                    
                    # Set up context for template
                    context = Context({
                        'first_name': invitee.first_name or "",
                        'last_name': invitee.last_name or "",
                        'guest_category': invitee.guest_category,
                        'guest_category_display': invitee.get_guest_category_display(),
                        'event': event,
                        'rsvp_accept_url': rsvp_urls['accept'],
                        'rsvp_decline_url': rsvp_urls['decline'],
                        'calendar_links': calendar_links_html,
                        'SITE_URL': settings.SITE_URL.rstrip('/')
                    })
                    
                    # Render email subject and content
                    subject = Template(template.subject).render(context)
                    html_content = Template(template.content).render(context)
                    
                    # Create Mail object for SendGrid
                    organizer_name = "Moratwe Events"
                    if event.organizer:
                        organizer_name = event.organizer.get_full_name() or "Moratwe Events"

                    message = Mail(
                        from_email=(settings.DEFAULT_FROM_EMAIL, organizer_name),
                        to_emails=To(invitee.email, invitee.get_full_name()),
                        subject=subject,
                        html_content=html_content
                    )
                    
                    # Note: Custom args removed to avoid SendGrid API issues
                    # The email will still be sent successfully without custom tracking
                    
                    messages_to_send.append((message, existing_rsvp))
                    
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
                        TaskStatus.update_task(
                            task_id,
                            progress=progress,
                            processed=processed_count,
                            emails_sent=emails_sent,
                            failed=len(failed_emails),
                            offset=offset + idx + 1,
                            message=f'Processed {processed_count} of {total_count} invitees. Sent {emails_sent} emails. Skipped {emails_skipped} already sent.',
                            additional_data={'emails_skipped': emails_skipped}
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
            
            # Send the batch of emails using SendGrid
            if messages_to_send:
                try:
                    sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
                    # Note: SendGrid's v3 API sends emails one by one, but the client manages connections efficiently.
                    # For true batching, you would use SMTP or explore SendGrid's marketing campaign APIs.
                    # Here we send them sequentially within the task.
                    for mail_obj, rsvp_obj in messages_to_send:
                        response = sg.send(mail_obj)
                        if 200 <= response.status_code < 300:
                            # Mark as sent
                            rsvp_obj.email_sent = True
                            rsvp_obj.email_sent_at = timezone.now()
                            rsvp_obj.save(update_fields=['email_sent', 'email_sent_at'])
                            batch_emails_sent += 1
                        else:
                            logger.error(f"Failed to send email to {rsvp_obj.invitee.email}: {response.body}")
                            failed_emails.append(rsvp_obj.invitee.email)
                
                except Exception as e:
                    logger.error(f"Error sending batch emails via SendGrid: {e}")
                    # Mark all in this batch as failed for simplicity
                    failed_emails.extend([rsvp.invitee.email for _, rsvp in messages_to_send])
            
            # Update counts
            emails_sent += batch_emails_sent
            
            # Log batch completion
            logger.info(f"Completed batch starting at {offset-current_batch_size}, sent {batch_emails_sent} emails, skipped {batch_emails_skipped}, failed: {len(failed_emails)}")
        
        # For consistent reporting, make sure we have accurate counts
        final_message = f'Process completed. Sent {emails_sent} emails to {processed_count} invitees.'
        if emails_skipped > 0:
            final_message += f' Skipped {emails_skipped} already sent.'
        if len(failed_emails) > 0:
            final_message += f' {len(failed_emails)} failed.'
        
        # All done - update final status
        latest_task = TaskStatus.get_task(task_id)
        current_status = latest_task.status if latest_task else 'running'
        
        if current_status not in ['stopped', 'error', 'pause']:
            TaskStatus.update_task(
                task_id,
                status='complete',
                progress=100,
                processed=processed_count,
                emails_sent=emails_sent,
                failed=len(failed_emails),
                message=f'Process complete. Sent {emails_sent} emails, skipped {emails_skipped}, failed {len(failed_emails)}.',
                additional_data={
                    'failed_emails': failed_emails,
                    'emails_skipped': emails_skipped
                }
            )
        elif current_status == 'pause':
            # Just update the counts but keep paused status
            TaskStatus.update_task(
                task_id,
                processed=processed_count,
                emails_sent=emails_sent,
                failed=len(failed_emails),
                message=f'Process paused at {processed_count} of {total_count} invitees.',
                offset=offset,
                additional_data={'emails_skipped': emails_skipped}
            )
        
        logger.info(f"======== COMPLETED task {task_id} successfully. Sent {emails_sent} invitations, skipped {emails_skipped}, failed {len(failed_emails)}. ========")
        
    except Exception as e:
        logger.error(f"Error in invitation batch task {task_id}: {e}", exc_info=True)
        TaskStatus.update_task(
            task_id,
            status='error',
            error=str(e),
            message=f'An unexpected error occurred: {e}'
        )


@shared_task(bind=True)
def process_rsvps_task(self, task_id, event_id, action, status_value=None, batch_size=50):
    """Celery task to process RSVPs in batches."""
    logger.info(f"Starting RSVP batch task {task_id} for event: {event_id}")
    
    try:
        # Get event and base queryset
        event = Event.objects.get(id=event_id)
        invitee_rsvps_base = InviteeRSVP.objects.filter(event=event).order_by('invitee__email')
        total_count = invitee_rsvps_base.count()
        
        # Create task status if not exists
        task = TaskStatus.get_task(task_id)
        if not task:
            task = TaskStatus.create_task(
                task_id=task_id,
                task_type='rsvp',
                event_id=event_id,
                total_items=total_count
            )
        
        # Process RSVPs in chunks of batch_size
        offset = 0
        processed_count = 0
        
        # Check if resuming from previous run
        if task.status == 'resume' and task.offset > 0:
            offset = task.offset
            processed_count = task.processed
            
            # Update status to running immediately to prevent resume loop
            TaskStatus.update_task(
                task_id, 
                status='running',
                message=f'Resuming from {processed_count} of {total_count} RSVPs.'
            )
            
        while offset < total_count:
            # Check if the task has been revoked or terminated
            if task_is_revoked(self.request.id):
                logger.info(f"Task {task_id} was revoked")
                TaskStatus.update_task(
                    task_id,
                    status='stopped',
                    message='Task was revoked'
                )
                return
                
            # Get latest task status
            task = TaskStatus.get_task(task_id)
            if not task:
                logger.error(f"Task status lost for task {task_id}")
                return
            
            # Handle task control actions
            if task.status == 'pause':
                logger.info(f"Task {task_id} paused at offset {offset}")
                # Update status for pause
                TaskStatus.update_task(
                    task_id,
                    status='pause',
                    message=f'Process paused at {processed_count} of {total_count} RSVPs.',
                    offset=offset
                )
                # Wait and check again
                time.sleep(5)
                continue
            elif task.status == 'stop':
                logger.info(f"Task {task_id} stopped at offset {offset}")
                
                # Update final status
                TaskStatus.update_task(
                    task_id,
                    status='stopped',
                    progress=int(processed_count / total_count * 100) if total_count > 0 else 100,
                    processed=processed_count,
                    message='Process was stopped manually',
                    offset=offset
                )
                return
            
            # Get current batch
            current_batch_size = min(batch_size, total_count - offset)
            
            if action == 'remind':
                # Only get pending RSVPs for reminders
                current_batch = invitee_rsvps_base.filter(status='pending')[offset:offset+current_batch_size]
                sent_count, failed_count = process_rsvp_reminders(event, current_batch)
                
                logger.info(f"Task {task_id}: Reminders sent to {sent_count} invitees with {failed_count} failures (batch starting at {offset})")
                
            elif action == 'update_status':
                # Update status for all RSVPs in batch
                current_batch = invitee_rsvps_base[offset:offset+current_batch_size]
                updated = update_rsvp_statuses(current_batch, status_value)
                
                logger.info(f"Task {task_id}: Updated {updated} RSVPs to '{status_value}' (batch starting at {offset})")
            
            # Update progress
            batch_count = current_batch.count()
            processed_count += batch_count
            progress = int(processed_count / total_count * 100) if total_count > 0 else 100
            
            # Update task status
            TaskStatus.update_task(
                task_id,
                progress=progress,
                processed=processed_count,
                total=total_count,
                offset=offset + batch_count,
                message=f"Processed {processed_count} of {total_count} RSVPs."
            )
            
            offset += batch_size
        
        # All done - update final status
        total_failed = 0  # We'd need to track this across batches if needed
        TaskStatus.update_task(
            task_id,
            status='complete',
            progress=100,
            processed=processed_count,
            message=f"Process completed. Processed {processed_count} RSVPs."
        )
        
        logger.info(f"Task {task_id} completed successfully. Processed {processed_count} RSVPs.")
        
    except Exception as e:
        logger.error(f"Error in RSVP processing task {task_id}: {e}", exc_info=True)
        TaskStatus.update_task(
            task_id,
            status='error',
            error=str(e),
            message=f'An unexpected error occurred: {e}'
        )


def process_rsvp_reminders(event, rsvps):
    """
    Send reminder emails to a list of invitees.
    """
    sent_count = 0
    failed_emails = []
    
    # Get the reminder email template
    template = EmailTemplate.objects.filter(name__iexact='Event Reminder').first()
    if not template:
        logger.error(f"No 'Event Reminder' template found for event {event.id}. Cannot send reminders.")
        return 0, len(rsvps)
    
    # Prepare emails
    messages_to_send = []
    for rsvp in rsvps:
        invitee = rsvp.invitee
        
        # Generate RSVP URLs
        rsvp_urls = get_rsvp_urls(rsvp.token, invitee.email)
        
        # Generate calendar links for email
        from .utils import get_calendar_email_html
        calendar_links_html = get_calendar_email_html(event, settings.SITE_URL.rstrip('/'))
        
        context = Context({
            'first_name': invitee.first_name,
            'last_name': invitee.last_name,
            'event': event,
            'rsvp_accept_url': rsvp_urls['accept'],
            'rsvp_decline_url': rsvp_urls['decline'],
            'calendar_links': calendar_links_html,
            'SITE_URL': settings.SITE_URL.rstrip('/')
        })
        
        subject = Template(template.subject).render(context)
        html_content = Template(template.content).render(context)
        
        message = Mail(
            from_email=(settings.DEFAULT_FROM_EMAIL, event.organizer.get_full_name() or 'Moratwe Events'),
            to_emails=To(invitee.email, invitee.get_full_name()),
            subject=subject,
            html_content=html_content
        )
        
        messages_to_send.append(message)
    
    # Send emails via SendGrid
    if messages_to_send:
        try:
            sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
            for mail in messages_to_send:
                response = sg.send(mail)
                if 200 <= response.status_code < 300:
                    sent_count += 1
                else:
                    failed_emails.append(mail.to[0].email)
        except Exception as e:
            logger.error(f"Error sending reminder emails via SendGrid: {e}")
            return 0, len(rsvps)
            
    return sent_count, len(failed_emails)


def update_rsvp_statuses(rsvps, status):
    """
    Update the status for a list of RSVPs.
    """
    for rsvp in rsvps:
        rsvp.status = status
        rsvp.save()


def get_rsvp_urls(token, email):
    """Generate absolute URLs for RSVP actions."""
    
    base_url = settings.SITE_URL.rstrip('/')
    
    accept_path = reverse('events:rsvp_accept')
    decline_path = reverse('events:rsvp_decline')
    
    # Construct URLs with query parameters
    accept_url = f"{base_url}{accept_path}?token={token}&email={email}"
    decline_url = f"{base_url}{decline_path}?token={token}&email={email}"
    
    return {
        'accept': accept_url,
        'decline': decline_url
    } 