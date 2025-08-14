import uuid
from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from users.models import CustomUser
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.urls import reverse
import qrcode
import qrcode.image.svg
from io import BytesIO
import base64

User = get_user_model()


class EmailTemplate(models.Model):
    """
    Model for storing reusable email templates for event invitations.
    """
    GUEST_CATEGORY_CHOICES = [
        ('all', _('All Categories')),
        ('regular', _('Regular')),
        ('vip', _('VIP')),
        ('vvip', _('VVIP')),
    ]
    
    name = models.CharField(_('name'), max_length=255)
    subject = models.CharField(_('subject'), max_length=255, help_text=_('You can use {{ event.title }} in the subject'))
    content = models.TextField(_('content'), help_text=_(
        'Available variables: {{ first_name }}, {{ last_name }}, {{ event.title }}, '
        '{{ event.date }}, {{ event.location }}, {{ event.description }}, {{ guest_category }}'
    ))
    guest_category = models.CharField(
        max_length=10,
        choices=GUEST_CATEGORY_CHOICES,
        default='all',
        verbose_name=_('Target Guest Category'),
        help_text=_('Which guest category this template is designed for')
    )
    is_default = models.BooleanField(_('is default'), default=False)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)

    class Meta:
        verbose_name = _('email template')
        verbose_name_plural = _('email templates')
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.is_default:
            # Ensure only one default template exists per guest category
            EmailTemplate.objects.filter(
                is_default=True, 
                guest_category=self.guest_category
            ).exclude(pk=self.pk).update(is_default=False)
        super().save(*args, **kwargs)


class Event(models.Model):
    """
    Model representing an event.
    """
    title = models.CharField(_('title'), max_length=255)
    description = models.TextField(_('description'), blank=True)
    date = models.DateTimeField(_('date'), null=True, default=timezone.now)
    location = models.CharField(_('location'), max_length=255)
    image = models.ImageField(_('image'), upload_to='event_images/', blank=True, null=True)
    organizer = models.ForeignKey(
        CustomUser, 
        on_delete=models.CASCADE, 
        related_name='organized_events', 
        verbose_name=_('organizer'),
        null=True  # Temporarily allow null for migration
    )
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    is_active = models.BooleanField(_('active'), default=True)

    class Meta:
        verbose_name = _('event')
        verbose_name_plural = _('events')
        ordering = ['-date']
    
    def __str__(self):
        return self.title
    
    @property
    def is_past(self):
        """
        Check if the event is in the past.
        """
        if not self.date:
            return False
        return self.date < timezone.now()


class BreakawaySession(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name="breakaways", verbose_name=_('event'))
    title = models.CharField(_('title'), max_length=255)
    panelists = models.ManyToManyField(CustomUser, related_name="panelist_sessions", verbose_name=_('panelists'))
    description = models.TextField(_('description'), blank=True)
    start_time = models.TimeField(_('start time'), null=True, blank=True)
    end_time = models.TimeField(_('end time'), null=True, blank=True)
    max_attendees = models.PositiveIntegerField(_('maximum attendees'), null=True, blank=True)
    
    class Meta:
        verbose_name = _('breakaway session')
        verbose_name_plural = _('breakaway sessions')
        ordering = ['start_time']
    
    def __str__(self):
        return f"{self.title} - {self.event.title}"


class RSVP(models.Model):
    STATUS_CHOICES = [
        ('pending', _('Pending')),
        ('accepted', _('Accepted')),
        ('declined', _('Declined')),
        ('maybe', _('Maybe')),
    ]
    
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='rsvps')
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='rsvps')
    status = models.CharField(_('status'), max_length=10, choices=STATUS_CHOICES, default='pending')
    response_date = models.DateTimeField(_('response date'), null=True, blank=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    notes = models.TextField(_('notes'), blank=True)
    number_of_guests = models.PositiveIntegerField(_('number of guests'), default=0)
    dietary_requirements = models.TextField(_('dietary requirements'), blank=True)
    is_registered_user = models.BooleanField(_('is registered user'), default=False)
    
    # QR Code and Check-in fields
    qr_code = models.ImageField(_('QR code'), upload_to="qr_codes/", blank=True, null=True)
    qr_code_data = models.UUIDField(_('QR code data'), default=uuid.uuid4, unique=True)
    checked_in = models.BooleanField(_('checked in'), default=False)
    selected_sessions = models.ManyToManyField(BreakawaySession, blank=True, related_name='attendees')
    
    class Meta:
        verbose_name = _('RSVP')
        verbose_name_plural = _('RSVPs')
        unique_together = ('event', 'user')
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.user.get_full_name()} - {self.event.title} ({self.get_status_display()})"
    
    def save(self, *args, **kwargs):
        is_new = self.pk is None
        
        # Get the old status if this is an existing RSVP
        if not is_new:
            old_instance = RSVP.objects.get(pk=self.pk)
            old_status = old_instance.status
            # If status changed to declined or pending, remove QR code
            if old_status != self.status and self.status in ['declined', 'pending'] and self.qr_code:
                # Delete the old QR code file
                self.qr_code.delete(save=False)
                self.qr_code = None
        
        if self.status != 'pending' and not self.response_date:
            self.response_date = timezone.now()
            
        super().save(*args, **kwargs)
        
        # Only generate QR code for accepted RSVPs that don't have one
        if (is_new or not self.qr_code) and self.status == 'accepted':
            self.generate_qr_code()
    
    @property
    def rsvp_details_completed(self):
        """
        Check if the user has completed their RSVP details.
        An RSVP is considered complete if the user has made a conscious decision
        about dietary requirements (even if "None" is selected).
        """
        # If dietary_requirements is not empty, it means they've been through the form
        # Note: We check for any value, including "None" which would be set when they 
        # explicitly select "None" in the dropdown
        return bool(self.dietary_requirements)
    
    def generate_qr_code(self):
        """
        Generate a QR code for the RSVP.
        """
        # Only generate QR code for accepted RSVPs
        if self.status != 'accepted':
            return
            
        import qrcode
        import json
        from io import BytesIO
        from django.core.files.base import ContentFile
        
        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        
        # Add data to QR code - format to match mobile app expectations
        qr_data = {
            'event_id': str(self.event.id),
            'user_id': str(self.user.id),
            'qr_code_data': str(self.qr_code_data)
        }
        
        # Use JSON encoding to match mobile app format
        qr.add_data(json.dumps(qr_data))
        qr.make(fit=True)
        
        # Create image from QR code
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        
        # Save the QR code to the RSVP model
        filename = f"rsvp_{self.id}_{self.qr_code_data}.png"
        self.qr_code.save(filename, ContentFile(buffer.getvalue()), save=True)


class EventInvitation(models.Model):
    """
    Model representing an invitation sent to a user list for an event.
    """
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='invitations')
    user_list = models.ForeignKey('userlists.UserList', on_delete=models.CASCADE, related_name='event_invitations')
    email_template = models.ForeignKey(
        EmailTemplate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        verbose_name=_('email template'),
        help_text=_('Select the email template to use for this invitation')
    )
    sent_at = models.DateTimeField(_('sent at'), auto_now_add=True)
    
    class Meta:
        verbose_name = _('event invitation')
        verbose_name_plural = _('event invitations')
        unique_together = ('event', 'user_list')
        ordering = ['-sent_at']
    
    def __str__(self):
        return f"{self.user_list.name} - {self.event.title}"


class InviteeRSVP(models.Model):
    """
    Model representing an invitee's RSVP status for a specific event.
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined')
    ]
    
    invitee = models.ForeignKey('userlists.Invitee', on_delete=models.CASCADE, related_name='rsvps')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='invitee_rsvps')
    status = models.CharField(_('status'), max_length=10, choices=STATUS_CHOICES, default='pending')
    timestamp = models.DateTimeField(_('timestamp'), null=True, blank=True)
    token = models.UUIDField(_('token'), null=True, blank=True, unique=True)
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    updated_at = models.DateTimeField(_('updated at'), auto_now=True)
    email_sent = models.BooleanField(_('email sent'), default=False, help_text=_('Whether an invitation email has been sent'))
    email_sent_at = models.DateTimeField(_('email sent at'), null=True, blank=True)

    class Meta:
        unique_together = ['invitee', 'event']
        ordering = ['-created_at']
        verbose_name = _('invitee RSVP')
        verbose_name_plural = _('invitee RSVPs')

    def __str__(self):
        return f"{self.invitee.email} - {self.event.title} ({self.get_status_display()})"


class TaskStatus(models.Model):
    """Model to track background task status and progress."""
    
    STATUS_CHOICES = (
        ('running', _('Running')),
        ('pause', _('Paused')),
        ('complete', _('Complete')),
        ('stopped', _('Stopped')),
        ('error', _('Error')),
    )
    
    TASK_TYPES = (
        ('invitation', _('Send Invitations')),
        ('rsvp', _('Process RSVPs')),
    )
    
    task_id = models.CharField(max_length=36, primary_key=True)
    task_type = models.CharField(max_length=20, choices=TASK_TYPES)
    event_id = models.IntegerField()
    
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='running')
    progress = models.IntegerField(default=0)
    processed = models.IntegerField(default=0)
    total = models.IntegerField(default=0)
    offset = models.IntegerField(default=0)
    emails_sent = models.IntegerField(default=0)
    failed = models.IntegerField(default=0)
    
    message = models.TextField(blank=True)
    error = models.TextField(blank=True)
    
    # Additional data stored as JSON
    additional_data = models.JSONField(blank=True, default=dict)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = _('Task Status')
        verbose_name_plural = _('Task Statuses')
        ordering = ['-updated_at']
    
    def __str__(self):
        return f"{self.get_task_type_display()} - {self.get_status_display()} ({self.task_id})"
        
    @classmethod
    def create_task(cls, task_id, task_type, event_id, total_items=0):
        """Create a new task status record."""
        task = cls(
            task_id=task_id,
            task_type=task_type,
            event_id=event_id,
            status='running',
            total=total_items,
            message=f'Task started with {total_items} items to process'
        )
        task.save()
        return task
    
    @classmethod
    def get_task(cls, task_id):
        """Get a task by ID."""
        try:
            return cls.objects.get(task_id=task_id)
        except cls.DoesNotExist:
            return None
    
    @classmethod
    def update_task(cls, task_id, **kwargs):
        """Update a task's status and progress."""
        try:
            task = cls.objects.get(task_id=task_id)
            for key, value in kwargs.items():
                setattr(task, key, value)
            task.updated_at = timezone.now()
            task.save()
            return task
        except cls.DoesNotExist:
            return None
