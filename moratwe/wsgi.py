"""
WSGI config for moratwe project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/4.2/howto/deployment/wsgi/
"""

import os
from dotenv import load_dotenv
from django.core.wsgi import get_wsgi_application

# Load environment variables from .env file
load_dotenv()

# Load SendGrid-specific environment variables
# Assumes sendgrid.env is in the project root, one level up from this file's directory
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'sendgrid.env')
if os.path.exists(dotenv_path):
    load_dotenv(dotenv_path=dotenv_path)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moratwe.settings')

application = get_wsgi_application()
