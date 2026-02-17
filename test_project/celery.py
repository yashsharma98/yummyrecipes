from __future__ import absolute_import, unicode_literals

import os

from celery import Celery

# Set default Django settings module for 'celery' command-line program
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "test_project.settings")

app = Celery("test_project")

# Using a string means the worker doesn’t need to serialize
# the configuration object to child processes.
app.config_from_object("django.conf:settings", namespace="CELERY")

# Load task modules from all registered Django apps
app.autodiscover_tasks()


@app.task(bind=True)
def debug_task(self):
    print(f"Request: {self.request!r}")
