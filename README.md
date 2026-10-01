# Good Doggy CRM

CRM omnicanal SaaS multiempresa con agentes de IA (WhatsApp, Instagram, Messenger, TikTok), motor de precios, stock, pipeline comercial y cotizaciones.

**Estado:** Fase 1 — infraestructura base, en curso ([plan](docs/phases/phase-1.md), issue maestro #13). Aún no hay código de aplicación.

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

## Nombre del proyecto

El producto se llama **Good Doggy CRM** y el repositorio es `PapiCuche/crm-gooddoggy`. Antes se llamaba CRM BLACKDOG (`PapiCuche/crm-blackdog`); GitHub redirige el slug anterior.

El rebranding no renombró identificadores técnicos. Se conservan a propósito:

- `name: crm-blackdog` en [infra/docker/compose.yaml](infra/docker/compose.yaml): es el nombre de proyecto de Docker Compose y prefija volúmenes, redes y contenedores locales. Cambiarlo recrearía esos recursos y dejaría huérfano el volumen de PostgreSQL, así que queda como migración posterior.
- `crm_app`, `crm_migrator`, `crm-backend`, `crm-frontend` y el resto de nombres con `crm`: no son branding.

## Flujo de trabajo

Agentes y contribuidores: leer primero [AGENTS.md](AGENTS.md). Cada incremento es un issue `work-item` ([delivery-automation.md](docs/architecture/delivery-automation.md)).

GitHub Flow ([ADR-009](docs/adr/ADR-009-git-strategy.md)): ramas `feature/*` o `fix/*` → PR → CI → squash merge a `main`.
