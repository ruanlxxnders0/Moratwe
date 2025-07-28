#!/usr/bin/env python3
"""
Test SendGrid API authentication.
"""

import os
import sys

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moratwe.settings.development')
import django
django.setup()

from sendgrid import SendGridAPIClient
from django.conf import settings

def test_sendgrid_auth():
    """Test SendGrid API authentication."""
    print("Testing SendGrid API Authentication")
    print("=" * 40)
    
    # Get API key from environment or settings
    api_key = os.environ.get('SENDGRID_API_KEY') or getattr(settings, 'SENDGRID_API_KEY', None)
    
    if not api_key:
        print("✗ SENDGRID_API_KEY not found")
        print("Please check your environment variables or settings.")
        return False
    
    print(f"API Key found: {api_key[:4]}...{api_key[-4:]}")
    
    try:
        # Test API connection
        sg = SendGridAPIClient(api_key)
        
        # Try a simple API call to test authentication
        response = sg.client.api_keys.get()
        
        if response.status_code == 200:
            print("✓ SendGrid API authentication successful!")
            print(f"Status Code: {response.status_code}")
            return True
        else:
            print(f"✗ SendGrid API authentication failed")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.body}")
            return False
            
    except Exception as e:
        print(f"✗ SendGrid API error: {e}")
        return False

if __name__ == "__main__":
    test_sendgrid_auth() 