#!/bin/sh
set -eu
APP_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
cd "$APP_DIR"
case "${1:-}" in
  web|jobs) role=$1 ;;
  *) printf '%s\n' 'Expected service role: web or jobs.' >&2; exit 2 ;;
esac
# No automatic schema changes on service startup. Apply migrations explicitly.
python manage.py check --deploy
python manage.py migrate --check
if [ "${PAYMENTS_MODE:-disabled}" = live ]; then
  python manage.py readiness
fi
if [ "$role" = jobs ]; then
  exec python manage.py process_jobs --loop
fi
exec gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3 --timeout 90 --access-logfile -
