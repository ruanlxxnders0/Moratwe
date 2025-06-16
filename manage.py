#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from dotenv import load_dotenv


def main():
    """Run administrative tasks."""
    # Load environment variables from .env file
    load_dotenv()
    
    # Load SendGrid-specific environment variables
    dotenv_path = os.path.join(os.path.dirname(__file__), 'sendgrid.env')
    if os.path.exists(dotenv_path):
        load_dotenv(dotenv_path=dotenv_path)

    # Set the default settings module based on environment
    # Check if we're running in production environment by looking at DJANGO_ENV
    # This determines which settings module to use (production vs development)
    if os.environ.get('DJANGO_ENV') == 'production':
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moratwe.settings.production')
    else:
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moratwe.settings.development')
    
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
