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
from rest_framework import permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from users.views import CustomUserDetailsView, privacy_policy
from django.views.generic import TemplateView
import logging

logger = logging.getLogger(__name__)

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
    path('admin/', admin.site.urls),
    
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
