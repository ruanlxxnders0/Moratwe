from django import forms
from django.contrib.auth.forms import AuthenticationForm, UsernameField
from django.utils.translation import gettext_lazy as _


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