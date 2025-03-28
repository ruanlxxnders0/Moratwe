# Moratwe Deployment Guide

This guide provides instructions for deploying the Moratwe RSVP management solution to a production environment.

## Prerequisites

- A server with Ubuntu/Debian
- Python 3.8+
- PostgreSQL database
- Nginx
- Gunicorn
- SSL certificate (Let's Encrypt recommended)

## Server Setup

1. SSH into your server:
   ```
   ssh ubuntu@rsvps.moratwe.co.za
   ```

2. Install required packages:
   ```
   sudo apt update
   sudo apt install python3-pip python3-venv nginx postgresql postgresql-contrib
   ```

3. Create a database and user:
   ```
   sudo -u postgres psql
   CREATE DATABASE moratwe;
   CREATE USER moratweuser WITH PASSWORD 'your_secure_password';
   ALTER ROLE moratweuser SET client_encoding TO 'utf8';
   ALTER ROLE moratweuser SET default_transaction_isolation TO 'read committed';
   ALTER ROLE moratweuser SET timezone TO 'UTC';
   GRANT ALL PRIVILEGES ON DATABASE moratwe TO moratweuser;
   \q
   ```

## Project Deployment

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/moratwe.git
   cd moratwe
   ```

2. Create and activate a virtual environment:
   ```
   python3 -m venv venv
   source venv/bin/activate
   ```

3. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

4. Create a `.env` file with your environment variables:
   ```
   DJANGO_SECRET_KEY=your_secure_secret_key
   DJANGO_SETTINGS_MODULE=moratwe.settings.production
   DB_NAME=moratwe
   DB_USER=moratweuser
   DB_PASSWORD=your_secure_password
   DB_HOST=localhost
   EMAIL_HOST=your_smtp_server
   EMAIL_PORT=587
   EMAIL_HOST_USER=your_email
   EMAIL_HOST_PASSWORD=your_email_password
   DEFAULT_FROM_EMAIL=noreply@moratwe.co.za
   SITE_URL=https://rsvps.moratwe.co.za
   ```

5. Set up the production settings:
   ```
   nano moratwe/settings/production.py
   ```

   Make sure the `ALLOWED_HOSTS` includes your domain: `'rsvps.moratwe.co.za'`.

6. Run the deployment script:
   ```
   chmod +x deploy.sh
   ./deploy.sh
   ```
   
   This will:
   - Collect static files
   - Apply migrations
   - Set correct permissions
   - Restart Gunicorn and Nginx

## Gunicorn Configuration

1. Create a Gunicorn systemd service file:
   ```
   sudo nano /etc/systemd/system/gunicorn.service
   ```

2. Add the following content (update paths as needed):
   ```
   [Unit]
   Description=gunicorn daemon
   After=network.target

   [Service]
   User=ubuntu
   Group=www-data
   WorkingDirectory=/home/ubuntu/moratwe
   ExecStart=/home/ubuntu/moratwe/venv/bin/gunicorn \
             --access-logfile - \
             --workers 3 \
             --bind unix:/home/ubuntu/moratwe/moratwe.sock \
             moratwe.wsgi:application

   [Install]
   WantedBy=multi-user.target
   ```

3. Enable and start the service:
   ```
   sudo systemctl enable gunicorn
   sudo systemctl start gunicorn
   ```

## Nginx Configuration

1. Create a Nginx site configuration:
   ```
   sudo nano /etc/nginx/sites-available/moratwe
   ```

2. Add the following content:
   ```
   server {
       listen 80;
       server_name rsvps.moratwe.co.za;
       return 301 https://$host$request_uri;
   }

   server {
       listen 443 ssl;
       server_name rsvps.moratwe.co.za;

       ssl_certificate /etc/letsencrypt/live/rsvps.moratwe.co.za/fullchain.pem;
       ssl_certificate_key /etc/letsencrypt/live/rsvps.moratwe.co.za/privkey.pem;

       location = /favicon.ico { access_log off; log_not_found off; }
       
       location /static/ {
           root /home/ubuntu/moratwe;
           expires 30d;
       }

       location /media/ {
           root /home/ubuntu/moratwe;
           expires 30d;
       }

       location / {
           include proxy_params;
           proxy_pass http://unix:/home/ubuntu/moratwe/moratwe.sock;
           proxy_buffers 8 32k;
           proxy_buffer_size 64k;
       }
   }
   ```

3. Enable the site and restart Nginx:
   ```
   sudo ln -s /etc/nginx/sites-available/moratwe /etc/nginx/sites-enabled/
   sudo systemctl restart nginx
   ```

## SSL Certificate

1. Install Certbot:
   ```
   sudo apt install certbot python3-certbot-nginx
   ```

2. Obtain a certificate:
   ```
   sudo certbot --nginx -d rsvps.moratwe.co.za
   ```

3. Follow the prompts to complete the setup.

## Troubleshooting

If the site doesn't work after deployment, check:

1. Nginx logs:
   ```
   sudo tail -f /var/log/nginx/error.log
   ```

2. Gunicorn logs:
   ```
   sudo journalctl -u gunicorn
   ```

3. Django logs (in your project directory):
   ```
   tail -f logs/django.log
   ```

4. Make sure the static files are collected:
   ```
   ls -la staticfiles/
   ```

5. Verify permissions:
   ```
   sudo chown -R ubuntu:www-data /home/ubuntu/moratwe
   sudo chmod -R 755 /home/ubuntu/moratwe/staticfiles
   sudo chmod -R 755 /home/ubuntu/moratwe/media
   ```

6. Restart services:
   ```
   sudo systemctl restart gunicorn
   sudo systemctl restart nginx
   ```

Remember to check Django's `DEBUG` setting is set to `False` in production to see the proper error pages rather than debug traces. 