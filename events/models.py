from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
from users.models import CustomUser
from django.utils import timezone
import uuid


class Event(models.Model):
    """
    Model representing an event.
    """
    title = models.CharField(_('title'), max_length=255)
    description = models.TextField(_('description'), blank=True)
    date = models.DateTimeField(_('date'), null=True, default=timezone.now)
    location = models.CharField(_('location'), max_length=255)
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
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='rsvps', verbose_name=_('event'))
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='rsvps', verbose_name=_('user'))
    qr_code = models.ImageField(_('QR code'), upload_to="qr_codes/", blank=True, null=True)
    selected_sessions = models.ManyToManyField(BreakawaySession, blank=True, related_name='attendees', verbose_name=_('selected sessions'))
    created_at = models.DateTimeField(_('created at'), auto_now_add=True)
    checked_in = models.BooleanField(_('checked in'), default=False)
    qr_code_data = models.UUIDField(_('QR code data'), default=uuid.uuid4, unique=True)
    
    class Meta:
        verbose_name = _('RSVP')
        verbose_name_plural = _('RSVPs')
        unique_together = ('event', 'user')
        ordering = ['created_at']
    
    def __str__(self):
        return f"{self.user.email} - {self.event.title}"
    
    def save(self, *args, **kwargs):
        """
        Generate QR code on save if it doesn't exist.
        """
        is_new = self.pk is None
        super().save(*args, **kwargs)
        
        if is_new or not self.qr_code:
            self.generate_qr_code()
    
    def generate_qr_code(self):
        """
        Generate a QR code for the RSVP.
        """
        import qrcode
        from io import BytesIO
        from django.core.files.base import ContentFile
        
        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        
        # Add data to QR code
        qr_data = {
            'rsvp_id': str(self.id),
            'event_id': str(self.event.id),
            'user_id': str(self.user.id),
            'qr_code_data': str(self.qr_code_data)
        }
        
        qr.add_data(str(qr_data))
        qr.make(fit=True)
        
        # Create image from QR code
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format="PNG")
        
        # Save the QR code to the RSVP model
        filename = f"rsvp_{self.id}_{self.qr_code_data}.png"
        self.qr_code.save(filename, ContentFile(buffer.getvalue()), save=True)
