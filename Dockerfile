FROM python:3.12

# set work directory
WORKDIR /app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=starshield.settings
ENV DJANGO_CONFIGURATION=Prod

# install dependencies
RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install -r requirements.txt

# copy project
COPY . .

# collect static files
RUN python manage.py collectstatic --noinput

# Expose port for web application
EXPOSE 8080

# Run WSGI server for production
CMD ["gunicorn", "starshield.wsgi:application", "--bind", "0.0.0.0:8080", "--workers", "4"]