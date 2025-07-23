from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.utils.translation import gettext_lazy as _
from django.utils import timezone
import re
import secrets
import string


class CustomUserManager(BaseUserManager):
    """
    Custom user model manager where email is the unique identifier
    for authentication instead of username.
    """
    def create_user(self, email, password=None, **extra_fields):
        """
        Create and save a user with the given email and password.
        """
        if not email:
            raise ValueError('The Email field must be set')
        email = self.normalize_email(email).lower().strip()
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        """
        Create and save a SuperUser with the given email and password.
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    """
    Custom User model with email as the unique identifier
    instead of username for authentication.
    """
    username = None
    email = models.EmailField(unique=True)
    first_name = models.CharField(max_length=30, blank=True)
    last_name = models.CharField(max_length=30, blank=True)
    phone_number = models.CharField(max_length=30, unique=True)
    date_joined = models.DateTimeField(default=timezone.now)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_organizer = models.BooleanField(_('is organiser'), default=False)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email

    def get_full_name(self):
        """
        Return the first_name plus the last_name, with a space in between.
        """
        full_name = f"{self.first_name} {self.last_name}"
        return full_name.strip()

    def get_short_name(self):
        """Return the short name for the user."""
        return self.first_name
        
    def clean(self):
        super().clean()
        # Normalize email to lowercase to prevent case-sensitive duplicates
        if self.email:
            self.email = self.email.lower().strip()
        
        # Clean phone number if provided
        if self.phone_number:
            # Remove any non-digit characters except for leading +
            if self.phone_number.startswith('+'):
                # Keep the leading + sign
                cleaned_number = '+' + re.sub(r'\D', '', self.phone_number[1:])
            else:
                cleaned_number = re.sub(r'\D', '', self.phone_number)
            
            # Add + prefix for international format if it looks like an international number
            if not cleaned_number.startswith('+') and len(cleaned_number) > 10:
                cleaned_number = '+' + cleaned_number
                
            # Only update if the cleaned number is different
            if cleaned_number != self.phone_number:
                self.phone_number = cleaned_number

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)


class PasswordResetToken(models.Model):
    """
    Model to store password reset tokens in the database.
    """
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='password_reset_tokens')
    token = models.CharField(max_length=64, unique=True)
    created_at = models.DateTimeField(default=timezone.now)
    is_used = models.BooleanField(default=False)
    used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Password reset token for {self.user.email}"

    @property
    def is_expired(self):
        """Check if token is expired (24 hours)"""
        if self.is_used:
            return True
        
        expiry_time = self.created_at + timezone.timedelta(hours=24)
        return timezone.now() > expiry_time

    @property
    def is_valid(self):
        """Check if token is valid (not used and not expired)"""
        return not self.is_used and not self.is_expired

    def mark_as_used(self):
        """Mark token as used"""
        self.is_used = True
        self.used_at = timezone.now()
        self.save()

    @classmethod
    def generate_token(cls):
        """Generate a secure random token"""
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(64))

    @classmethod
    def create_for_user(cls, user):
        """Create a new password reset token for a user"""
        # Invalidate existing tokens for this user
        cls.objects.filter(user=user, is_used=False).update(is_used=True, used_at=timezone.now())
        
        # Create new token
        token = cls.generate_token()
        return cls.objects.create(user=user, token=token)

    @classmethod
    def cleanup_expired_tokens(cls):
        """Clean up expired tokens (can be run as a management command or cron job)"""
        expired_time = timezone.now() - timezone.timedelta(hours=24)
        expired_count = cls.objects.filter(created_at__lt=expired_time).delete()[0]
        return expired_count
