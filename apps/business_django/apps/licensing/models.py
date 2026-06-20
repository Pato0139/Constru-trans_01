import uuid

from django.db import models


class Installation(models.Model):
    instance_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    customer_id = models.CharField(max_length=64, blank=True, default="")
    activated_at = models.DateTimeField(null=True, blank=True)
    last_validated_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    license_token = models.TextField(blank=True, default="")
    build_hash = models.CharField(max_length=64, blank=True, default="")
    manifest_hash = models.CharField(max_length=64, blank=True, default="")
    status = models.CharField(max_length=20, default="pending")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'licensing_installation'

    def __str__(self):
        return f"Installation {self.instance_id} ({self.status})"
