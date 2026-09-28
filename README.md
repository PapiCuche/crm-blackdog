# CRM BLACKDOG

CRM omnicanal SaaS multiempresa con agentes de IA (WhatsApp, Instagram, Messenger, TikTok), motor de precios, stock, pipeline comercial y cotizaciones.

**Estado:** Fase 0.5 cerrada (decisiones y scaffolding). Siguiente: Fase 1 — infraestructura base. Aún no hay código de aplicación.

## Documentación

| Qué | Dónde |
|---|---|
| Análisis inicial (A–U), backlog y roadmap | [docs/fase-0/](docs/fase-0/00-README.md) |
| Decisiones de arquitectura (ADR) | [docs/adr/](docs/adr/README.md) |
| Arquitectura viva: estructura, tenancy, seguridad, dependencias, CI | [docs/architecture/](docs/architecture/) |
| Plan y cierre de cada fase | [docs/phases/](docs/phases/) |

## Estructura

```text
backend/    Django (API, WebSockets, Celery)      — desde la Fase 1
frontend/   Next.js (UI)                           — desde la Fase 1
infra/      Docker local y despliegue
docs/       Documentación y ADRs
.github/    CI, Dependabot y plantillas
```

## Entorno local (servicios base)

Ver [infra/README.md](infra/README.md).

## Flujo de trabajo

GitHub Flow ([ADR-009](docs/adr/ADR-009-git-strategy.md)): ramas `feature/*` o `fix/*` → PR → CI → squash merge a `main`.
