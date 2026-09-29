"""Organizaciones (platform-owned, sin RLS de tenant; ADR-001 §2). Mínima para F1-04."""

import uuid

from django.db import models


class Organization(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "ACTIVE"
        TRIAL = "TRIAL"
        SUSPENDED = "SUSPENDED"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)  # UUIDv7: F1-05
    slug = models.SlugField(max_length=63, unique=True)
    name = models.CharField(max_length=200)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "organizations"

    def __str__(self) -> str:
        return self.slug
