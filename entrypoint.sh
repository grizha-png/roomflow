#!/bin/sh
set -e

echo "Waiting for PostgreSQL at ${POSTGRES_HOST}:${POSTGRES_PORT}..."
until pg_isready -h "${POSTGRES_HOST}" -p "${POSTGRES_PORT}" -U "${POSTGRES_USER}" -d "${POSTGRES_DB}"; do
  sleep 1
done

python manage.py migrate --noinput
python manage.py collectstatic --noinput

if [ -n "${DJANGO_SUPERUSER_USERNAME}" ] && [ -n "${DJANGO_SUPERUSER_EMAIL}" ] && [ -n "${DJANGO_SUPERUSER_PASSWORD}" ]; then
  python manage.py shell -c "
from django.contrib.auth import get_user_model;
User = get_user_model();
username = '${DJANGO_SUPERUSER_USERNAME}';
email = '${DJANGO_SUPERUSER_EMAIL}';
password = '${DJANGO_SUPERUSER_PASSWORD}';
if not User.objects.filter(username=username).exists():
    User.objects.create_superuser(username=username, email=email, password=password)
"
fi

exec "$@"

