FROM python:3.14

# set work directory
WORKDIR /app

# set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# install dependencies
RUN pip install --upgrade pip
COPY requirements.txt .
RUN pip install -r requirements.txt

# copy project
COPY . .

# collect static files
RUN python manage.py collectstatic --noinput

# Make entrypoint script executable
RUN chmod +x entrypoint.sh

# Expose port for web application
EXPOSE 8080

# Run entrypoint script with default 'webapp' argument
CMD ["/app/entrypoint.sh", "webapp"]