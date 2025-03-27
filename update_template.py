import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'moratwe.settings.development')
import django
django.setup()

from events.models import EmailTemplate
from django.conf import settings

html_template = '''<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            margin: 0;
            padding: 0;
        }
        .container {
            max-width: 600px;
            margin: 0 auto;
            padding: 20px;
        }
        .header {
            text-align: center;
            padding: 20px 0;
        }
        .event-image {
            width: 100%;
            max-width: 600px;
            height: auto;
            border-radius: 8px;
            margin: 20px 0;
        }
        .event-details {
            background-color: #f8f9fa;
            border-radius: 8px;
            padding: 20px;
            margin: 20px 0;
        }
        .button {
            display: inline-block;
            padding: 12px 24px;
            margin: 10px;
            border-radius: 25px;
            text-decoration: none;
            font-weight: bold;
            text-align: center;
        }
        .accept {
            background-color: #28a745;
            color: white;
        }
        .decline {
            background-color: #dc3545;
            color: white;
        }
        .app-stores {
            text-align: center;
            margin: 30px 0;
        }
        .app-button {
            display: inline-block;
            margin: 10px;
            max-width: 200px;
        }
        .footer {
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 1px solid #eee;
            font-size: 12px;
            color: #666;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>You're Invited!</h1>
        </div>

        <p>Dear {{ first_name }},</p>

        <p>You are cordially invited to:</p>
        
        <div class="event-details">
            <h2>{{ event.title }}</h2>
            {% if event.image %}
            <img src="{{ SITE_URL }}{{ event.image.url }}" alt="{{ event.title }}" class="event-image" style="width: 100%; max-width: 600px; height: auto; border-radius: 8px; margin: 20px 0;">
            {% endif %}
            
            <h3>Event Details:</h3>
            <p><strong>Date:</strong> {{ event.date|date:"l, F j, Y" }}</p>
            <p><strong>Time:</strong> {{ event.date|date:"g:i A" }}</p>
            <p><strong>Location:</strong> {{ event.location }}</p>
            
            {% if event.description %}
            <h3>Description:</h3>
            <p>{{ event.description }}</p>
            {% endif %}
        </div>

        <div style="text-align: center;">
            <h3>Will you attend?</h3>
            <a href="{{ rsvp_accept_url }}" class="button accept">Accept</a>
            <a href="{{ rsvp_decline_url }}" class="button decline">Decline</a>
        </div>

        <div class="app-stores">
            <h3>Get the Moratwe App</h3>
            <p>Download our mobile app to manage your invitations and stay updated:</p>
            <div>
                <a href="https://apps.apple.com/app/moratwe" class="app-button">
                    <img src="{{ SITE_URL }}/static/images/app-store-badge.svg" alt="Download on the App Store" style="max-width: 200px;">
                </a>
            </div>
            <div>
                <a href="https://play.google.com/store/apps/details?id=com.moratwe.app" class="app-button">
                    <img src="{{ SITE_URL }}/static/images/google-play-badge.png" alt="Get it on Google Play" style="max-width: 200px;">
                </a>
            </div>
        </div>

        <div class="footer">
            <p>This invitation was sent to you via Moratwe Events.</p>
            <p>If you have any questions, please contact us at support@moratwe.com</p>
        </div>
    </div>
</body>
</html>'''

# Update the default template
template = EmailTemplate.objects.get(is_default=True)
template.content = html_template
template.save()

print("Email template updated successfully!") 