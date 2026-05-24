from celery import shared_task

from .services import validate_installation


@shared_task
def license_heartbeat():
    validate_installation()
