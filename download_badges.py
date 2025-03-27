import os
import requests
from django.conf import settings

def download_badges():
    # Create static/images directory if it doesn't exist
    os.makedirs('static/images', exist_ok=True)
    
    # URLs for the badges
    app_store_url = "https://developer.apple.com/app-store/marketing/guidelines/images/badge-download-on-the-app-store.svg"
    play_store_url = "https://play.google.com/intl/en_us/badges/static/images/badges/en_badge_web_generic.png"
    
    # Download App Store badge (SVG)
    response = requests.get(app_store_url)
    if response.status_code == 200:
        with open('static/images/app-store-badge.svg', 'wb') as f:
            f.write(response.content)
        print("Downloaded App Store badge (SVG)")
    
    # Download Play Store badge (PNG)
    response = requests.get(play_store_url)
    if response.status_code == 200:
        with open('static/images/google-play-badge.png', 'wb') as f:
            f.write(response.content)
        print("Downloaded Play Store badge (PNG)")

if __name__ == "__main__":
    download_badges() 