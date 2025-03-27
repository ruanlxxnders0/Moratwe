from django.db import models
from django.core.validators import EmailValidator
from django.core.exceptions import ValidationError
import re

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
    user_list = models.ForeignKey(UserList, on_delete=models.CASCADE, related_name='invitees')
    email = models.EmailField(validators=[EmailValidator()])
    first_name = models.CharField(max_length=100, blank=True)
    last_name = models.CharField(max_length=100, blank=True)
    mobile_number = models.CharField(max_length=20, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ['user_list', 'email']
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.email} ({self.user_list.name})"

    def clean(self):
        # Validate mobile number format if provided
        if self.mobile_number:
            # Remove any non-digit characters
            cleaned_number = re.sub(r'\D', '', self.mobile_number)
            if not cleaned_number.isdigit() or len(cleaned_number) < 10:
                raise ValidationError({'mobile_number': 'Please enter a valid mobile number'})

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)
