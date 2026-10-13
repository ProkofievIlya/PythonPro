#!/bin/sh
set -e
python manage.py migrate --noinput
python manage.py collectstatic --noinput
if [ -f datadump.json ]; then
  set +e
  python -c "import os,django; os.environ.setdefault('DJANGO_SETTINGS_MODULE','bookstore.settings'); django.setup(); from catalog.models import Book; raise SystemExit(0 if Book.objects.exists() else 1)"
  empty=$?
  set -e
  if [ "$empty" -eq 1 ]; then
    python manage.py loaddata datadump.json
  fi
fi
exec "$@"
