#!/bin/bash
# Deployment script for Moratwe web application

echo "Starting deployment process..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Install/update dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Collect static files
echo "Collecting static files..."
python manage.py collectstatic --no-input --settings=moratwe.settings.production

# Apply migrations
echo "Applying migrations..."
python manage.py migrate --settings=moratwe.settings.production

# Set proper permissions for static and media files
echo "Setting file permissions..."
if [ -d "staticfiles" ]; then
    chmod -R 755 staticfiles
fi

if [ -d "media" ]; then
    chmod -R 755 media
fi

# Restart Gunicorn (if using Gunicorn)
echo "Restarting Gunicorn service..."
sudo systemctl restart gunicorn

# Reload Nginx (if using Nginx)
echo "Reloading Nginx..."
sudo systemctl reload nginx

echo "Deployment completed!" 