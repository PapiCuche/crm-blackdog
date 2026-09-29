"""`org_sequences` (ADR-004 §2): tenant-owned con RLS + FORCE y FK a `organizations`."""

from django.db import migrations, models

from core.db.operations import EnableRLS


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_tenancy_functions"),
        ("organizations", "0002_alter_organization_id"),
    ]

    operations = [
        migrations.CreateModel(
            name="OrgSequence",
            fields=[
                ("organization_id", models.UUIDField(editable=False)),
                (
                    "pk",
                    models.CompositePrimaryKey(
                        "organization_id",
                        "sequence_key",
                        blank=True,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("sequence_key", models.CharField(max_length=16)),
                ("next_value", models.BigIntegerField()),
            ],
            options={"db_table": "org_sequences"},
        ),
        EnableRLS("OrgSequence"),
        # ADR-004 §2: REFERENCES organizations(id). Solo en BD: el kernel no importa apps.
        migrations.RunSQL(
            "ALTER TABLE org_sequences ADD CONSTRAINT org_sequences_organization_fk "
            "FOREIGN KEY (organization_id) REFERENCES organizations (id)",
            "ALTER TABLE org_sequences DROP CONSTRAINT IF EXISTS org_sequences_organization_fk",
        ),
    ]
