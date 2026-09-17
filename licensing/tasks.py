from celery import shared_task

from .services import validate_installation


@shared_task(name="licensing.license_heartbeat")
def license_heartbeat():
    return validate_installation().status
