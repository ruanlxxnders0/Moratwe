#!/usr/bin/env python3
"""
Debug SendGrid 401 Unauthorized issues on live server.
Run this script on your production server to diagnose the problem.
"""

import os
import sys
import subprocess
import json

def run_command(command):
    """Run a shell command and return the output."""
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout.strip(), result.stderr.strip(), result.returncode
    except Exception as e:
        return "", str(e), 1

def check_environment():
    """Check environment variables and file permissions."""
    print("=" * 60)
    print("ENVIRONMENT VARIABLES CHECK")
    print("=" * 60)
    
    # Check if running as the correct user
    stdout, stderr, code = run_command("whoami")
    print(f"Current user: {stdout}")
    
    # Check environment variables
    env_vars = [
        'SENDGRID_API_KEY',
        'DEFAULT_FROM_EMAIL',
        'DJANGO_SETTINGS_MODULE',
        'PYTHONPATH'
    ]
    
    for var in env_vars:
        value = os.environ.get(var)
        if value:
            if 'KEY' in var or 'PASSWORD' in var:
                masked = value[:4] + '*' * (len(value) - 8) + value[-4:] if len(value) > 8 else '***'
                print(f"✓ {var}: {masked}")
            else:
                print(f"✓ {var}: {value}")
        else:
            print(f"✗ {var}: NOT SET")
    
    # Check for .env files
    print(f"\nEnvironment files:")
    env_files = ['/home/ubuntu/moratwe_web/.env', '/home/ubuntu/moratwe_web/sendgrid.env']
    for env_file in env_files:
        if os.path.exists(env_file):
            print(f"✓ {env_file} exists")
            try:
                with open(env_file, 'r') as f:
                    content = f.read()
                    if 'SENDGRID_API_KEY' in content:
                        print(f"  - Contains SENDGRID_API_KEY")
                    else:
                        print(f"  - Does NOT contain SENDGRID_API_KEY")
            except Exception as e:
                print(f"  - Error reading file: {e}")
        else:
            print(f"✗ {env_file} does NOT exist")

def check_processes():
    """Check running processes."""
    print("\n" + "=" * 60)
    print("PROCESS CHECK")
    print("=" * 60)
    
    # Check Django processes
    stdout, stderr, code = run_command("ps aux | grep -E '(django|manage.py|gunicorn)' | grep -v grep")
    if stdout:
        print("Django/Gunicorn processes:")
        print(stdout)
    else:
        print("No Django/Gunicorn processes found")
    
    # Check Celery processes
    stdout, stderr, code = run_command("ps aux | grep celery | grep -v grep")
    if stdout:
        print(f"\nCelery processes:")
        print(stdout)
    else:
        print("\nNo Celery processes found")

def check_systemd_services():
    """Check systemd services."""
    print("\n" + "=" * 60)
    print("SYSTEMD SERVICES CHECK")
    print("=" * 60)
    
    services = ['celery', 'celerybeat', 'gunicorn', 'nginx']
    for service in services:
        stdout, stderr, code = run_command(f"systemctl is-active {service}")
        status = stdout if stdout else "not found"
        print(f"{service}: {status}")
        
        # Check environment variables in service files
        stdout, stderr, code = run_command(f"systemctl show {service} -p Environment")
        if stdout and 'Environment=' in stdout:
            print(f"  Environment: {stdout}")

def test_sendgrid_directly():
    """Test SendGrid API directly."""
    print("\n" + "=" * 60)
    print("SENDGRID API TEST")
    print("=" * 60)
    
    api_key = os.environ.get('SENDGRID_API_KEY')
    if not api_key:
        print("✗ SENDGRID_API_KEY not found in environment")
        return
    
    print(f"✓ API Key found: {api_key[:4]}...{api_key[-4:]}")
    
    try:
        # Test using curl
        curl_cmd = f'curl -X GET "https://api.sendgrid.com/v3/api_keys" -H "Authorization: Bearer {api_key}" -H "Content-Type: application/json"'
        stdout, stderr, code = run_command(curl_cmd)
        
        if code == 0:
            try:
                response = json.loads(stdout)
                print("✓ SendGrid API connection successful!")
                print(f"Response: {json.dumps(response, indent=2)[:200]}...")
            except json.JSONDecodeError:
                print("✓ SendGrid API responded (but not JSON)")
                print(f"Response: {stdout[:200]}...")
        else:
            print(f"✗ SendGrid API test failed")
            print(f"Error: {stderr}")
            print(f"Output: {stdout}")
    
    except Exception as e:
        print(f"✗ Error testing SendGrid API: {e}")

def test_python_sendgrid():
    """Test SendGrid using Python."""
    print("\n" + "=" * 60)
    print("PYTHON SENDGRID TEST")
    print("=" * 60)
    
    try:
        # Set Django settings
        os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moratwe.settings.production')
        import django
        django.setup()
        
        from sendgrid import SendGridAPIClient
        from django.conf import settings
        
        # Get API key
        api_key = getattr(settings, 'SENDGRID_API_KEY', None) or os.environ.get('SENDGRID_API_KEY')
        if not api_key:
            print("✗ SENDGRID_API_KEY not found in Django settings or environment")
            return
        
        print(f"✓ API Key from Django: {api_key[:4]}...{api_key[-4:]}")
        
        # Test SendGrid client
        sg = SendGridAPIClient(api_key)
        response = sg.client.api_keys.get()
        
        if response.status_code == 200:
            print("✓ Python SendGrid client connection successful!")
            print(f"Status Code: {response.status_code}")
        else:
            print(f"✗ Python SendGrid client failed")
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.body}")
    
    except Exception as e:
        print(f"✗ Error testing Python SendGrid: {e}")

def check_celery_environment():
    """Check Celery worker environment."""
    print("\n" + "=" * 60)
    print("CELERY ENVIRONMENT CHECK")
    print("=" * 60)
    
    try:
        # Check if we can import Celery modules
        from moratwe.celery import app as celery_app
        print("✓ Celery app import successful")
        
        # Check Celery configuration
        print(f"Celery broker URL: {celery_app.conf.broker_url}")
        print(f"Celery result backend: {celery_app.conf.result_backend}")
        
        # Test a simple task
        from events.tasks import process_invitations_task
        print("✓ Task import successful")
        
    except Exception as e:
        print(f"✗ Error checking Celery: {e}")

def main():
    """Main debugging function."""
    print("SENDGRID DEBUG SCRIPT FOR LIVE SERVER")
    print("=" * 60)
    print("This script will diagnose SendGrid 401 Unauthorized issues")
    print("=" * 60)
    
    check_environment()
    check_processes()
    check_systemd_services()
    test_sendgrid_directly()
    test_python_sendgrid()
    check_celery_environment()
    
    print("\n" + "=" * 60)
    print("DEBUGGING COMPLETE")
    print("=" * 60)
    print("\nNext steps:")
    print("1. If SENDGRID_API_KEY is missing from environment, add it to your systemd service files")
    print("2. If the API key is present but SendGrid test fails, check if the key is valid")
    print("3. If Python test works but Celery doesn't, restart Celery services")
    print("4. Check that all services are using the same environment variables")

if __name__ == "__main__":
    main() 