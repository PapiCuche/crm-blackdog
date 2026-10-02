"""Convenciones de la API (ADR-014): error único, sesión con CSRF y rutas de plataforma."""

AUTH_SCHEME = "Session"  # `WWW-Authenticate` de un 401: no hay credenciales que pedir
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})  # RFC 9110: no cambian estado
