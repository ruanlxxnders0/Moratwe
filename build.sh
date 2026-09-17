#!/usr/bin/env bash
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

if [[ -n "$ADMIN_EMAIL" && -n "$ADMIN_PASSWORD" ]]; then
  python manage.py shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
email = '$ADMIN_EMAIL'
password = '$ADMIN_PASSWORD'
user, created = User.objects.get_or_create(email=email, defaults={'is_staff': True, 'is_superuser': True})
if not created:
    user.is_staff = True
    user.is_superuser = True
user.set_password(password)
user.save()
print('Superuser ready:', email)
"
fi
