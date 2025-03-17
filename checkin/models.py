from django.db import models
from django.conf import settings
from django.utils.translation import gettext_lazy as _
import qrcode
from io import BytesIO
from django.core.files import File
from PIL import Image
import uuid


class CheckIn(models.Model):
    """
    Model representing a check-in for an event.
    """
    rsvp = models.ForeignKey(
        'events.RSVP',
        on_delete=models.CASCADE,
        related_name='checkins',
        verbose_name=_('RSVP'),
        null=True,  # Temporarily allow null for migration
    )
    checked_in_at = models.DateTimeField(_('checked in at'), auto_now_add=True)
    checked_in_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='performed_checkins',
        verbose_name=_('checked in by')
    )
    
    class Meta:
        verbose_name = _('check-in')
        verbose_name_plural = _('check-ins')
        ordering = ['-checked_in_at']
    
    def __str__(self):
        if self.rsvp:
            return f"{self.rsvp.user.email} - {self.rsvp.event.title} - {self.checked_in_at}"
        return f"Check-in at {self.checked_in_at}"
    
    def save(self, *args, **kwargs):
        """
        Update the RSVP checked_in status when a check-in is created.
        """
        super().save(*args, **kwargs)
        
        # Update the RSVP checked_in status
        if self.rsvp and not self.rsvp.checked_in:
            self.rsvp.checked_in = True
            self.rsvp.save(update_fields=['checked_in'])


# Note: We don't need the CheckInCode model anymore since the RSVP model now has a QR code field
