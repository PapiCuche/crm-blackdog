"""`audit_logs` se define en SQL (particionada por mes): ver migrations/0001_audit_logs.py.

Este módulo existe para que Django emita `post_migrate` para la app (mantenimiento de
particiones en `apps.py`). La escritura es solo vía `apps.audit.services.record`.
"""
