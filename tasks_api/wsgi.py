import os
from gevent import monkey
import grpc.experimental.gevent as grpc_gevent

grpc_gevent.init_gevent()
monkey.patch_all()

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tasks_api.settings")
os.environ.setdefault("DJANGO_CONFIGURATION", "Prod")

from configurations.wsgi import get_wsgi_application

application = get_wsgi_application()
