# infra/

Infraestructura local y (más adelante) de despliegue.

## Entorno local (Fase 0.5: servicios base)

```bash
cp infra/env/.env.example infra/env/.env      # completar contraseñas locales
docker compose -f infra/docker/compose.yaml --env-file infra/env/.env up -d
```

| Servicio | Puerto local | Uso |
|---|---|---|
| postgres (18) | 5432 | BD `crm`; roles `crm_migrator` (migraciones) y `crm_app` (runtime, sin BYPASSRLS) — ver ADR-002 |
| redis (8) | 6379 | Broker de Celery, capa de Channels y caché (en local, una instancia sin expulsión) |
| mailpit | 8025 (UI), 1025 (SMTP) | Captura de emails en desarrollo |

Los roles se crean **solo en el primer arranque** del volumen (`postgres/init/`). Para recrearlos: `docker compose … down -v`.

El emulador S3 local se añade en la Fase 1 (decisión D-ENG-2, ver ADR-008). En la Fase 1 también se añaden los servicios `backend`, `worker`, `ws`, `frontend` y `proxy` (Caddy, topología same-origin de ADR-003).
