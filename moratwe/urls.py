"""
URL configuration for moratwe project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from django.views.decorators.csrf import csrf_protect
from django.core.mail import send_mail
from django.contrib import messages
from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from users.views import CustomUserDetailsView, privacy_policy
from users.forms import EmailAuthenticationForm
from django.views.generic import TemplateView
from django.shortcuts import render, redirect
import logging

logger = logging.getLogger(__name__)

# Landing page view
def landing_page(request):
    """Home landing page for the public marketing site."""
    context = {
        'SITE_URL': settings.SITE_URL.rstrip('/'),
        'app_features': [
            {
                'title': 'QR Code Scanning',
                'description': 'Quickly scan event QR codes for seamless check-in and session management.'
            },
            {
                'title': 'Event Calendar',
                'description': 'Keep track of all your events and sessions in one place.'
            },
            {
                'title': 'User Profiles',
                'description': 'Manage your personal information and preferences easily.'
            },
            {
                'title': 'Event Details & Breakaway Sessions',
                'description': 'View comprehensive event information and select sessions to attend.'
            },
            {
                'title': 'Instant Notifications',
                'description': 'Receive real-time updates about event changes and announcements.'
            }
        ]
    }
    return render(request, 'home.html', context)

# Contact form view
@csrf_protect
def contact_form(request):
    """Handle contact form submission."""
    if request.method == 'POST':
        name = request.POST.get('name', '')
        email = request.POST.get('email', '')
        subject = request.POST.get('subject', '')
        message = request.POST.get('message', '')
        
        # Construct the email message
        email_subject = f"Contact Form: {subject}"
        email_message = f"""
        Contact Form Submission:
        
        Name: {name}
        Email: {email}
        Subject: {subject}
        
        Message:
        {message}
        """
        
        # Send the email
        try:
            send_mail(
                email_subject,
                email_message,
                settings.DEFAULT_FROM_EMAIL,
                ['info@moratwe.co.za'],
                fail_silently=False,
            )
            messages.success(request, 'Your message has been sent. Thank you for contacting us!')
        except Exception as e:
            logger.error(f"Email sending failed: {e}")
            messages.error(request, 'There was an error sending your message. Please try again later.')
        
        return redirect('landing')
    
    # If not a POST request, redirect to the home page
    return redirect('landing')

schema_view = get_schema_view(
    openapi.Info(
        title="Moratwe API",
        default_version='v1',
        description="API for Moratwe application",
        terms_of_service="https://www.moratwe.com/terms/",
        contact=openapi.Contact(email="contact@moratwe.com"),
        license=openapi.License(name="BSD License"),
    ),
    public=True,
    permission_classes=(permissions.AllowAny,),
)

urlpatterns = [
    # Landing page
    path('', landing_page, name='landing'),
    
    # Contact form
    path('contact/', contact_form, name='contact'),
    
    # Admin
    path('admin/', admin.site.urls),
    
    # Authentication URLs
    path('accounts/login/', auth_views.LoginView.as_view(
        template_name='users/login.html',
        authentication_form=EmailAuthenticationForm
    ), name='login'),
    path('accounts/logout/', auth_views.LogoutView.as_view(next_page='/'), name='logout'),
    path('accounts/', include('django.contrib.auth.urls')),
    
    # API endpoints
    path('api/', include('api.urls')),
    
    # User details endpoint
    path('api/users/me/', CustomUserDetailsView.as_view(), name='user-details'),
    
    # Privacy Policy
    path('privacy-policy/', TemplateView.as_view(template_name='privacy_policy.html'), name='privacy-policy'),
    
    # Events
    path('events/', include('events.urls')),
    
    # Swagger documentation
    path('swagger<format>/', schema_view.without_ui(cache_timeout=0), name='schema-json'),
    path('swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    path('redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),
]

# Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
