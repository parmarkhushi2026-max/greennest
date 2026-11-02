"""WSGI config for GreenNest."""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "greennest.settings")

application = get_wsgi_application()
