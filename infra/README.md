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
| redis (8.8.3) | 6379 | Broker de Celery, capa de Channels y caché (en local, una instancia sin expulsión) |
| garage (v2.4.1) | 3900 (S3) | Emulador S3 local de un nodo (ADR-012 §6). Bucket privado `STORAGE_BUCKET` y clave creados al arrancar. **Solo local y CI** (AGPL-3.0, OBS-F1-01-2) |
| mailpit (v1.31.3) | 8025 (UI), 1025 (SMTP) | Captura de emails en desarrollo |

Los roles se crean **solo en el primer arranque** del volumen (`postgres/init/`). Para recrearlos: `docker compose … down -v`.

### Credenciales de BD por proceso (producción)

| Proceso | Variable | Rol |
|---|---|---|
| web, worker, ws, beat | `DATABASE_URL` | `crm_app` (sin BYPASSRLS, no propietario) |
| Job de migraciones (efímero) | `DATABASE_MIGRATOR_URL` | `crm_migrator` (propietario, BYPASSRLS) |

El runtime **nunca** recibe `DATABASE_MIGRATOR_URL` ni `CRM_MIGRATOR_PASSWORD` y se niega a arrancar si las detecta. `CREATEDB` del migrador es exclusivo del bootstrap local. Ver ADR-002 §1.1.

El emulador S3 local es **Garage v2.4.1** (decisión D-ENG-2, ADR-012). Genera `GARAGE_RPC_SECRET` y las credenciales como indica `.env.example`. En la Fase 1 también se añaden los servicios `backend`, `worker`, `ws`, `frontend` y `proxy` (Caddy, topología same-origin de ADR-003).
