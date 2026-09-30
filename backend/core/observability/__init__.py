"""Observabilidad de aplicación (ADR-011): logs JSON, correlación y reporte de errores.

Único módulo que puede importar `sentry_sdk` (import-linter). El scrubbing es `core.redaction`.
"""
