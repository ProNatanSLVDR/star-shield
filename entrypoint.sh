#!/bin/bash
set -e

SERVICE_TYPE="${1:-webapp}"  # Default to 'webapp' if no argument

case "$SERVICE_TYPE" in
  web-app)
    exec gunicorn starshield.wsgi:application --bind 0.0.0.0:8080 --workers 4
    ;;
  tasks-api)
    exec gunicorn apps.tasks_api.wsgi:application --bind 0.0.0.0:8080 --workers 2 --worker-class gevent --worker-connection 500 --timeout 360 --keep-alive 5
    ;;
  migrate)
    exec python prod.manage.py migrate --noinput
    ;;
  *)
    echo "Unknown service type: $SERVICE_TYPE"
    exit 1
    ;;
esac
