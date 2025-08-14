from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.utils.translation import gettext_lazy as _
from .models import CustomUser


class EmailAuthenticationForm(AuthenticationForm):
    """
    A custom authentication form that uses email addresses instead of usernames.
    """
    username = forms.EmailField(
        label=_("Email address"),
        widget=forms.EmailInput(attrs={
            'autofocus': True, 
            'class': 'appearance-none border border-gray-300 rounded w-full py-3 px-4 text-gray-700 leading-tight focus:outline-none focus:border-primary',
            'placeholder': 'you@example.com'
        }),
    )
    password = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'current-password', 
            'class': 'appearance-none border border-gray-300 rounded w-full py-3 px-4 text-gray-700 leading-tight focus:outline-none focus:border-primary'
        }),
    )
    
    error_messages = {
        'invalid_login': _(
            "Please enter a correct %(username)s and password. Note that both "
            "fields may be case-sensitive."
        ),
        'inactive': _("This account is inactive."),
    }
    
    def __init__(self, request=None, *args, **kwargs):
        """
        The 'request' parameter is set for custom auth use by subclasses.
        The form data comes in via the standard 'data' kwarg.
        """
        self.request = request
        self.user_cache = None
        super().__init__(request, *args, **kwargs)
        
        # Change the label for the username field
        self.fields['username'].label = _("Email address")


class CustomUserCreationForm(UserCreationForm):
    """
    A custom user creation form that uses email addresses and includes additional fields.
    """
    email = forms.EmailField(
        label=_("Email address"),
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'appearance-none border border-gray-300 rounded w-full py-3 px-4 text-gray-700 leading-tight focus:outline-none focus:border-primary',
            'placeholder': 'you@example.com'
        })
    )
    first_name = forms.CharField(
        label=_("First name"),
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'appearance-none border border-gray-300 rounded w-full py-3 px-4 text-gray-700 leading-tight focus:outline-none focus:border-primary',
            'placeholder': 'John'
        })
    )
    last_name = forms.CharField(
        label=_("Last name"),
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'appearance-none border border-gray-300 rounded w-full py-3 px-4 text-gray-700 leading-tight focus:outline-none focus:border-primary',
            'placeholder': 'Doe'
        })
    )
    phone_number = forms.CharField(
        label=_("Phone number"),
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'appearance-none border border-gray-300 rounded w-full py-3 px-4 text-gray-700 leading-tight focus:outline-none focus:border-primary',
            'placeholder': '+1234567890'
        })
    )
    password1 = forms.CharField(
        label=_("Password"),
        strip=False,
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'new-password',
            'class': 'appearance-none border border-gray-300 rounded w-full py-3 px-4 text-gray-700 leading-tight focus:outline-none focus:border-primary'
        }),
        help_text=_("Your password must contain at least 8 characters."),
    )
    password2 = forms.CharField(
        label=_("Password confirmation"),
        widget=forms.PasswordInput(attrs={
            'autocomplete': 'new-password',
            'class': 'appearance-none border border-gray-300 rounded w-full py-3 px-4 text-gray-700 leading-tight focus:outline-none focus:border-primary'
        }),
        strip=False,
        help_text=_("Enter the same password as before, for verification."),
    )

    class Meta:
        model = CustomUser
        fields = ("email", "first_name", "last_name", "phone_number", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Remove the username field since we use email
        if 'username' in self.fields:
            del self.fields['username']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if email and CustomUser.objects.filter(email=email).exists():
            raise forms.ValidationError(_("A user with this email address already exists."))
        return email

    def clean_phone_number(self):
        phone_number = self.cleaned_data.get('phone_number')
        if phone_number and phone_number.strip():
            # Check if phone number is already used (excluding empty/None values)
            if CustomUser.objects.filter(phone_number=phone_number.strip()).exists():
                raise forms.ValidationError(_("This phone number is already registered."))
            return phone_number.strip()
        # Return None for empty phone numbers to avoid uniqueness conflicts
        return None

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data["first_name"]
        user.last_name = self.cleaned_data["last_name"]
        # Use the cleaned phone number which will be None if empty
        user.phone_number = self.cleaned_data.get("phone_number")
        if commit:
            user.save()
        return user 