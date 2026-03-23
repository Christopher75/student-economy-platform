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
    CustomUser.objects.create_superuser(
        email='$ADMIN_EMAIL',
        password='$ADMIN_PASSWORD',
        full_name='Admin',
    )
    print('Superuser created.')
else:
    print('Superuser already exists.')
"
