#!/usr/bin/env bash
# Render build script

set -o errexit   # exit on error

pip install --upgrade pip
pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate

# Create superuser if one doesn't exist yet
python manage.py shell -c "
from accounts.models import CustomUser
if not CustomUser.objects.filter(is_superuser=True).exists():
    u = CustomUser(
        email='$ADMIN_EMAIL',
        username='admin',
        full_name='Admin',
        student_id='ADMIN001',
        university='Cavendish University Uganda',
        course='Administration',
        phone_number='0000000000',
        is_staff=True,
        is_superuser=True,
        is_email_verified=True,
        is_verified=True,
    )
    u.set_password('$ADMIN_PASSWORD')
    u.save()
    print('Superuser created.')
else:
    print('Superuser already exists.')
"
