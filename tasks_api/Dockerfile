FROM python:3.12

# set work directory
WORKDIR /app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV DJANGO_SETTINGS_MODULE=tasks_api.settings
ENV DJANGO_CONFIGURATION=Prod

# install dependencies
RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install -r requirements.txt

# copy project
COPY . .

# Expose port for API service (different from main web app)
EXPOSE 8080

# Run WSGI server for API
CMD ["gunicorn", "tasks_api.wsgi:application", "--bind", "0.0.0.0:8080", "--workers", "2"]

