from django.db import models
from django.core.validators import EmailValidator
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
import re
from events.models import Event

# Create your models here.

class UserList(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['-created_at']

class Invitee(models.Model):
    GUEST_CATEGORY_CHOICES = [
        ('regular', _('Regular')),
        ('vip', _('VIP')),
        ('vvip', _('VVIP')),
    ]
    
    user_list = models.ForeignKey(UserList, on_delete=models.CASCADE, related_name='invitees')
    email = models.EmailField(validators=[EmailValidator()])
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    mobile_number = models.CharField(max_length=30, blank=True)
    guest_category = models.CharField(
        max_length=10, 
        choices=GUEST_CATEGORY_CHOICES, 
        default='regular',
        verbose_name=_('Guest Category'),
        help_text=_('Guest categorization level (Regular, VIP, VVIP)')
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user_list', 'email']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.email} ({self.user_list.name})"

    def get_full_name(self):
        """Return the full name of the invitee."""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        elif self.first_name:
            return self.first_name
        elif self.last_name:
            return self.last_name
        else:
            return self.email

    def clean(self):
        # Validate mobile number format if provided
        if self.mobile_number:
            # Remove any non-digit characters except for leading +
            if self.mobile_number.startswith('+'):
                # Keep the leading + sign
                cleaned_number = '+' + re.sub(r'\D', '', self.mobile_number[1:])
            else:
                cleaned_number = re.sub(r'\D', '', self.mobile_number)
            
            # Only validate length if we have a number
            if cleaned_number and not cleaned_number.startswith('+') and len(cleaned_number) < 10:
                raise ValidationError({'mobile_number': 'Please enter a valid mobile number (at least 10 digits)'})
            
            # Update the field with the cleaned version
            self.mobile_number = cleaned_number

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
