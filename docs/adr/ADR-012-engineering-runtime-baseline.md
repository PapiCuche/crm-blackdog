# ADR-012: Baseline de runtimes, herramientas e imágenes (y emulador S3 local)

- **Status:** Accepted *(pendiente de aprobación del PR F1-01)*
- **Date:** 2026-09-28 (verificación de versiones realizada ese día entre las 18:38 y las 18:47 UTC; segunda verificación de Next.js a las 18:46 UTC)
- **Deciders:** Product Owner, Tech Lead
- **Related:** ADR-002 (PostgreSQL 18), ADR-004 (UUIDv7), ADR-008 (object storage), decisiones **D-ENG-1** y **D-ENG-2**
- **Review date:** 2026-12-15 (o antes si se publica una security release que afecte a la baseline)

## Context

La Fase 1 empieza a crear código (Django, Next.js, CI). Antes hay que fijar versiones **exactas** y verificadas en fuentes oficiales, para que:

- los lockfiles, las imágenes y el CI sean reproducibles;
- no se adopten versiones prerelease ni vulnerables conocidas;
- las decisiones de soporte (LTS frente a última versión) queden explícitas y con fecha de revisión.

También hay que elegir el emulador S3 local (D-ENG-2): MinIO dejó de publicar imágenes (ADR-008).

## Decision

### 1. Tabla de versiones exactas (baseline)

| Componente | Versión | Publicada | Soporte / estado | Fuente oficial |
|---|---|---|---|---|
| Python | **3.14.7** | 2026-08-05 | Rama 3.14 en *bugfix*; EOL 2030-10 | peps.python.org/api/release-cycle.json · python.org/api/v2/downloads/release |
| Django | **5.2.17** (LTS) | 2026-08-04 | Extended support hasta **abril de 2028** | djangoproject.com/download · pypi.org/project/Django |
| PostgreSQL | **18.6** (imagen `postgres:18.6`) | minor vigente | Soportada hasta 2030-11-14 | postgresql.org/support/versioning · Docker Hub `library/postgres` |
| Redis | **8.8.3** (imagen `redis:8.8.3-alpine`) | 2026-09-17 | Línea 8.8 recibiendo parches (8.8.3 publicada junto con 8.10.2) | github.com/redis/redis/releases · Docker Hub `library/redis` |
| Node.js | **24.21.0** LTS (*Krypton*) | 2026-09-07 | Active LTS hasta 2026-10-20; Maintenance hasta **2028-04-30** | nodejs.org/dist/index.json · github.com/nodejs/Release (schedule.json) |
| Next.js | **16.3.6** (Active LTS) | 2026-09-22 | Última publicada; security release **16.3.7 anunciada para 2026-09-30** (ver §4) | npm `next` · nextjs.org/blog · nextjs.org/support-policy · GitHub advisories vercel/next.js |
| React | **19.2.8** | 2026-07-21 | Versión que empareja `create-next-app` 16.3.6; incluye el fix de GHSA-wx67-qw84-cm4g | npm `react` · `packages/create-next-app/templates/index.ts@v16.3.6` · GitHub advisories facebook/react |
| React DOM | **19.2.8** | 2026-07-21 | Igual que React | npm `react-dom` |
| @types/react | **19.2.18** | 2026-07-30 | Versión usada por el propio monorepo de Next.js v16.3.6 | npm `@types/react` · `package.json@v16.3.6` |
| @types/react-dom | **19.2.7** | 2026-09-03 | Último patch 19.2.x | npm `@types/react-dom` |
| TypeScript | **6.0.3** | 2026-04-16 | Next.js 16.3.6 instala `typescript@^6.0.0` y su monorepo usa 6.0.2 | npm `typescript` · `packages/next/src/lib/verify-typescript-setup.ts@v16.3.6` |
| pnpm | **12.6.0** | 2026-09-22 | dist-tag `latest` / release "Latest" en GitHub | npm `pnpm` (dist-tags) · github.com/pnpm/pnpm/releases |
| uv | **0.12.19** | 2026-09-25 | Última release estable | github.com/astral-sh/uv/releases · pypi.org/project/uv |
| Mailpit | **v1.31.3** (imagen `axllent/mailpit:v1.31.3`) | 2026-09-27 | Última release | github.com/axllent/mailpit/releases · Docker Hub |
| Emulador S3 local | **Garage v2.4.1** (imagen `dxflrs/garage:v2.4.1`) | 2026-09-08 | Última release estable | git.deuxfleurs.fr/Deuxfleurs/garage (releases) · garagehq.deuxfleurs.fr · Docker Hub |

Sin rangos: estas son las versiones que se escriben en `pyproject.toml`, `.python-version`, `package.json` (`engines`, `packageManager`), `.nvmrc`, Dockerfiles y `compose.yaml` en los PRs de la Fase 1.

### 2. Python 3.14.7

- **3.15 no se adopta en F1-01:** a la fecha es *prerelease* (3.15.0rc2; estreno previsto el 2026-10-01). Aunque se publique durante la Fase 1, **no se cambia automáticamente**: primero hay que verificar Django, psycopg, Celery, Channels, cryptography, boto3, django-stubs y el resto de dependencias.
- **Compatibilidad verificada (PyPI y repositorios oficiales, 2026-09-28):**

| Dependencia | Última versión | Python 3.14 |
|---|---|---|
| Django 5.2.17 | — | ✅ oficial desde 5.2.8 (FAQ de instalación de Django) |
| psycopg / psycopg-binary 3.3.6 | 2026-09-18 | ✅ classifier + wheel `cp314` |
| celery 5.6.3 / kombu 5.6.2 | 2026-03 / 2025-12 | ✅ Celery 5.6.0 anuncia "initial support for Python 3.14"; kombu y celery prueban 3.14 en CI (el classifier de la release 5.6.3 aún no lo lista) |
| channels 4.3.2 / channels-redis 4.3.0 | 2025-11 / 2025-07 | ✅ channels con classifier; channels_redis prueba 3.14 en CI |
| cryptography 50.0.1 | 2026-08-25 | ✅ wheel `cp314` |
| boto3 / botocore 1.43.103 | 2026-09-25 | ✅ classifier |
| mypy (2.3.1 / 1.19.1) | — | ✅ wheel `cp314` |
| pytest 9.1.1 / pytest-django 4.14.0 | — | ✅ classifier |
| djangorestframework 3.18.1, drf-spectacular 0.30.0, uvicorn 0.54.0, redis 8.1.0, structlog 26.1.0, argon2-cffi 25.1.0 | — | ✅ classifier |
| **structlog 26.1.0** (fijada en F1-07) | 2026-06-06 | ✅ classifier 3.14, `py.typed`. Validada el **2026-09-30** (PyPI). Uso: logs JSON estructurados (ADR-011) |
| **boto3 / botocore 1.43.105** (fijadas en F1-08) | 2026-09-29 | ✅ classifier 3.14 (sin `py.typed`: mypy las trata como `Any`). Validadas el **2026-09-30** (PyPI) y con la suite de contrato contra Garage v2.4.1. Uso: storage S3-compatible, solo en `core.storage` |
| **urllib3 2.8.0** (fijada en F1-08) | 2026-09-15 | ✅ classifier 3.14, `py.typed`. Validada el **2026-09-30** (PyPI; compatible con botocore `<3`). Uso: cliente HTTP saliente anti-SSRF, solo en `core.http` |
| **sentry-sdk 2.69.1** (fijada en F1-07) | 2026-09-08 | ✅ classifier 3.14, `py.typed`. Validada el **2026-09-30** (PyPI; la última publicada ese día era 2.71.0, pero se fija 2.69.1 por decisión del PR de F1-07, sin vulnerabilidades en `pip-audit`). Uso: reporte de errores opcional (`SENTRY_DSN`), solo dentro de `core.observability` |

- **Restricción conocida (tipado, no runtime):** la serie `django-stubs 5.2.x` (última 5.2.9, 2026-01-20; mypy 1.13–1.19) declara probado Python 3.10–3.13, aunque se instala en 3.14 (`requires_python >=3.10`). La serie 6.x (6.1.1) sí declara Python 3.14 pero solo tiene **soporte parcial** de Django 5.2. **Decisión para F1-02:** usar `django-stubs 5.2.9` + `mypy 1.19.1` (stubs exactos de la API de 5.2) y verificar en CI que `mypy` corre sobre 3.14. Si falla, pasar a `django-stubs 6.0.x` (parcial 5.2) y documentarlo. **No es motivo para bajar a Python 3.13.**
- **UUIDv7:** `uuid.uuid7()` está disponible y es estable en la stdlib de Python 3.14 (verificado en ejecución local con 3.14.6). **Se usa la stdlib, sin dependencia externa.** Se encapsulará en `core.ids.new_id()` en F1-05 (ADR-004).

### 3. Django 5.2 LTS frente a 6.1

| Criterio | Django 5.2.17 LTS | Django 6.1.1 |
|---|---|---|
| Fin de soporte extendido (seguridad) | **Abril de 2028** | Diciembre de 2027 |
| Madurez | 17 patch releases; en producción desde abril de 2025 | Publicado el 2026-08-05; 1 patch release |
| Python 3.14 | ✅ (desde 5.2.8) | ✅ |
| Ecosistema (Channels, Celery, DRF, stubs) | Soporte completo y maduro | Soporte reciente; django-stubs 6.1.x completo |
| Riesgo durante el MVP | Bajo: solo parches | Upgrade obligatorio en ~15 meses |
| Camino siguiente | Saltar directamente a **6.2 LTS** (abril de 2027, soporte hasta abril de 2030) | 6.2 LTS igualmente |

**Why Django 5.2 LTS instead of Django 6.1:** en un SaaS con multi-tenancy, RLS, Channels, Celery y muchas integraciones, la prioridad es **seguridad y estabilidad**. 5.2 LTS da **4 meses más** de soporte que 6.1, un ecosistema más maduro y cero upgrades de framework durante el MVP. El coste es no disponer de las novedades de 6.0 y 6.1, ninguna de ellas necesaria para el MVP. El salto 5.2 → 6.2 LTS pasará por las deprecaciones de 6.0 y 6.1, algo acotado si el proyecto mantiene los *deprecation warnings* como errores en CI desde el inicio.

**Revisión prevista:** evaluar **Django 6.2 LTS** después de su lanzamiento (abril de 2027) y de su maduración inicial (≈ 2–3 patch releases). No es un upgrade automático. Nota: la política de Django cambia a partir de 2028 (versiones `YYYY` anuales con 3 años de soporte cada una); se tendrá en cuenta en esa revisión.

### 4. Node.js y Next.js

- **Node 24.21.0 LTS** y no 22 ni 26:
  - Node 22 pasa a EOL el 2027-04-30, dentro de la vida del MVP.
  - Node 26 todavía es *Current*: entra en LTS el 2026-10-28, y no se usa *Current* en producción.
  - Node 24 tiene soporte hasta 2028-04-30 y cumple `engines.node >=20.9.0` de Next.js 16.3.6.
  - **Revisión:** evaluar Node 26 cuando lleve ≥ 2 meses en LTS (≈ enero de 2027).
- **Next.js 16.3.x Active LTS.** Sin canary, beta, rc ni preview.
- **Estado de seguridad a la fecha de cierre (2026-09-28):**
  - **16.3.6** es la última versión publicada y corrige el advisory crítico GHSA-vcvr-r3jv-pc5j (RCE en `next/og`, 2026-09-22).
  - Vercel anunció el 2026-09-23 una **security release programada para el 2026-09-30** (16.3.7 y 15.5.27) que corregirá **nueve vulnerabilidades** (una crítica, dos altas, cinco medias y una baja). **16.3.7 no está publicada**, así que no se fija.
  - **Consecuencia obligatoria:** 16.3.6 tiene vulnerabilidades conocidas aún no divulgadas. **El frontend (F1-09) no se crea con 16.3.6 si 16.3.7 ya existe**: F1-09 debe fijar la última patch 16.3.x publicada a esa fecha (actualizando esta tabla en el mismo PR). Hoy no hay código de frontend, así que no hay exposición.
- **React 19.2.8 y no 19.3.0:** 19.3.0 (2026-09-09) es una minor más nueva, pero `create-next-app` 16.3.6 empareja `react@19.2.8`, que es la combinación probada por Next.js. 19.2.8 incluye el fix del último advisory de React Server Components (GHSA-wx67-qw84-cm4g). Se adopta 19.3 cuando Next.js la empareje.
- **TypeScript 6.0.3 y no 7.0.2:** Next.js 16.3.6 hace el type-check con la **API JS** de TypeScript (`typescript/lib/typescript.js`) y, si falta, instala `typescript@^6.0.0`. TypeScript 7 (el compilador nativo) no ofrece esa API y provoca un error salvo en el modo CLI. Se usa `strict: true` y `noUncheckedIndexedAccess: true` (se configura en F1-09).

### 5. Gestores de paquetes y herramientas

- **pnpm 12.6.0:** es el dist-tag `latest` y la release "Latest" en GitHub. Las versiones 12.7.0, 12.8.0 y 12.8.1 están publicadas bajo el canal `next-12`, aún no promovidas a `latest`; se adoptarán cuando pnpm las promueva. Se fija con `"packageManager": "pnpm@12.6.0"` en `package.json`. En CI, la acción oficial de pnpm lee ese campo. En local, se instala con el método oficial vigente (standalone o `npm`). **No se depende de Corepack:** la documentación oficial de pnpm ya no lo presenta como método de instalación.
- **uv 0.12.19:** única estrategia de dependencias Python (entorno, `uv.lock`, instalación reproducible, CI). **No** se usan Poetry, Pipenv ni pip-tools. Se fija con `required-version` en `pyproject.toml` (y la versión del instalador en CI).

### 6. Emulador S3 local (D-ENG-2): **Garage v2.4.1**

**Matriz de evaluación** (fuentes oficiales, 2026-09-28):

| Criterio | Garage v2.4.1 | SeaweedFS 4.47 (4.48 publicada hoy en GitHub, sin imagen Docker aún) |
|---|---|---|
| S3 API necesaria (Create/HeadBucket, Put/Get/Head/DeleteObject, ListObjectsV2, multipart completo) | ✅ todas "Implemented" (tabla oficial de compatibilidad) | ✅ todas "Yes" (wiki oficial Amazon-S3-API) |
| SigV4 | ✅ (SigV2 no, irrelevante) | ✅ |
| Presigned URLs (GET/PUT) | ✅ | ✅ |
| Path-style | ✅ (también vhost) | ✅ |
| Compatibilidad boto3 | Por estándar SigV4; la documentación oficial aún no tiene ejemplo boto3 ("Coming soon") → **se valida con los tests de contrato** | Documentado con AWS CLI y SDKs |
| ARM64 (Apple Silicon) | ✅ `linux/arm64` (+amd64, arm, 386) | ✅ `linux/arm64` (+amd64, arm, 386) |
| Imagen oficial | `dxflrs/garage` (la que indica la documentación oficial) | `chrislusf/seaweedfs` (del autor, indicada en el repositorio oficial) |
| Simplicidad single-node | **Alta**: desde v2.3.0, `garage server --single-node --default-bucket` crea el clúster de un nodo, la clave y el bucket desde variables de entorno (`GARAGE_DEFAULT_ACCESS_KEY/SECRET_KEY/BUCKET`) | Alta: `weed server -s3` levanta master + volume + filer + gateway S3; credenciales por variables AWS_* (modo *fallback*) o `s3.json` |
| Complejidad de arranque | Requiere un `garage.toml` mínimo (rutas, `rpc_secret`, puertos, `replication_factor = 1`) | Sin archivo de configuración obligatorio; el bucket se crea por API |
| Consumo de recursos | Un binario Rust, un proceso | 4 componentes en un proceso Go (master, volume, filer, S3): más pesado. *No medido* (Docker no disponible); se mide en F1-08 |
| Health check | `GET /health` en la API de administración (:3903). La imagen es `FROM scratch` (sin shell ni curl) → healthcheck con el propio binario (`/garage status`) o desde otro contenedor | Imagen con shell → healthcheck HTTP directo |
| Alcance funcional | Subconjunto de S3; lo no implementado devuelve **501** | Muy amplio (versioning, SSE, lifecycle…) |
| Licencia | AGPL-3.0 | Apache-2.0 |
| Mantenimiento | Activo (v2.3.0 abril, v2.4.0 y v2.4.1 septiembre de 2026) | Muy activo (releases semanales) |
| Testabilidad | Arranque determinista con clave y bucket por entorno: ideal para CI | Buena; hay que crear el bucket en el setup del test |

**Decisión: Garage v2.4.1.**

1. Cubre el 100 % de las operaciones requeridas, con SigV4, presigned URLs, path-style y ARM64.
2. Es el más simple de operar en Compose para nuestro caso (un proceso y bootstrap automático de clave y bucket).
3. Su alcance acotado es una **ventaja**: si el código usa por error una operación exótica, Garage responde 501 en local, igual que fallaría en proveedores con compatibilidad parcial como R2. SeaweedFS lo aceptaría en silencio.
4. **Licencia AGPL-3.0:** solo se usa como servicio local de desarrollo y CI; no se distribuye ni se enlaza con el producto, así que no impone obligaciones sobre nuestro código. Si en el futuro se quisiera usar Garage en producción, se re-evaluará.

**Fallback documentado:** SeaweedFS (última versión con imagen publicada) si los tests de contrato de F1-08 revelan una incompatibilidad bloqueante de Garage con boto3.

**Resultado F1-08 (2026-09-30):** Garage v2.4.1 **acepta** los checksums por defecto de boto3 1.43.105 (`put_object`, multipart y `get_object` verificados contra el contenedor). Aun así el cliente usa `when_required`, por portabilidad a R2 y a otros servicios S3-compatibles; la suite de contrato pasa completa con esa configuración. **Riesgo que se verificaba:** las versiones recientes de boto3/botocore envían por defecto *checksums* de integridad en `PutObject` y multipart (`x-amz-checksum-*`), y algunos servicios S3-compatibles los rechazan. Si Garage los rechaza, se configura el cliente con `request_checksum_calculation="when_required"` y `response_checksum_validation="when_required"`, que también es la configuración recomendada para proveedores compatibles como R2. Se documentará en el PR.

**Fuera de F1-01:** Garage **no** se añade a `compose.yaml` en este PR; se añade en **F1-08 (object storage)**.

### 7. Contrato de compatibilidad S3 (se implementa en F1-08)

Una única suite de tests de contrato con boto3, parametrizada por configuración (endpoint, región, credenciales, addressing style), que debe pasar contra el **emulador local** y, cuando haya credenciales, contra **AWS S3** y **Cloudflare R2**:

`test_create_bucket` · `test_put_get_object` · `test_head_object` · `test_delete_object` · `test_list_objects_v2` · `test_multipart_upload` · `test_abort_multipart` · `test_presigned_get` · `test_presigned_put` · `test_content_type` (+ deseable: `test_content_disposition`, `test_user_metadata`).

En CI se ejecuta contra Garage; contra S3 y R2 solo de forma manual o programada con secretos dedicados (nunca en PRs de forks).

## Compatibility matrix (resumen)

| | Python 3.14.7 | Django 5.2.17 | PostgreSQL 18.6 | Node 24.21.0 | Next 16.3.6 | React 19.2.8 | TS 6.0.3 |
|---|---|---|---|---|---|---|---|
| Django 5.2.17 | ✅ (≥ 5.2.8) | — | ✅ (psycopg 3.3.6) | — | — | — | — |
| Next 16.3.6 | — | — | — | ✅ (`>=20.9.0`) | — | ✅ (peer `^19.0.0`; pareja oficial) | ✅ (instala `^6.0.0`) |
| Celery 5.6 / Channels 4.3 | ✅ | ✅ | — | — | — | — | — |
| django-stubs 5.2.9 + mypy 1.19.1 | ⚠️ probado hasta 3.13, instalable; verificar en F1-02 | ✅ | — | — | — | — | — |
| Garage v2.4.1 | — | — | — | — | — | — | — |
| ↳ boto3 1.43.x | ⚠️ por estándar; tests de contrato en F1-08 | | | | | | |

## Upgrade policy

| Categoría | Patch | Minor | Major |
|---|---|---|---|
| **Runtimes** (Python, Node) | PR normal con CI verde | Revisión de compatibilidad de dependencias + CI | ADR o revisión arquitectónica |
| **Frameworks** (Django, Next.js, React) | **Security patch: lo antes posible** (≤ 72 h si es crítica/alta); otros parches, PR normal | Feature release con CI completo y notas de upgrade leídas | ADR (p. ej., Django 6.2 LTS, Next 17) |
| **PostgreSQL** | Regular (PR que cambia el tag) | — | Plan de upgrade (pg_upgrade o dump/restore probado, ventana, rollback) + ADR |
| **Redis** | Regular | Revisado (cambio de comportamiento, persistencia) | Revisado + ADR |
| **Tooling** (uv, pnpm, mypy, ruff, eslint…) | Dependabot o revisión periódica; lockfiles siempre commiteados y `--frozen` en CI | Idem, con CI completo | Revisión explícita |
| **Imágenes Docker** | Tags **patch concretos**; **nunca `latest`** ni tags flotantes (`v1`, `8.8`) | — | — |

- Digests (`@sha256:`) para imágenes sensibles: se evaluará en fases posteriores (despliegue).
- Esta tabla de versiones se actualiza **en el mismo PR** que cambia una versión.
- Revisión trimestral de la baseline (próxima: 2026-12-15) o antes ante una security release.

## Alternatives considered

| Alternativa | Por qué se descarta |
|---|---|
| Python 3.15 | Prerelease a la fecha |
| Python 3.13 | Sin incompatibilidad de runtime que lo justifique; 3.14 tiene más soporte (EOL 2030-10) y `uuid.uuid7()` en stdlib |
| Django 6.1 | Menos soporte (dic-2027) y menos madurez; forzaría un upgrade durante el MVP |
| Node 22 / Node 26 | 22 termina en abril de 2027; 26 aún es Current |
| Next.js canary/preview o 15.5.x | Sin estabilidad garantizada / major anterior en Maintenance LTS |
| React 19.3.0 | No es la pareja oficial de Next 16.3.6 |
| TypeScript 7.0.2 | Sin la API JS que Next.js usa en el type-check por defecto |
| TypeScript 5.9.3 | Next 16.3.6 recomienda e instala `^6.0.0` |
| pnpm 12.8.1 | Canal `next-12`, aún no promovido a `latest` |
| Corepack | No recomendado ya por la documentación oficial de pnpm; se usa `packageManager` + instalación oficial |
| Poetry / Pipenv / pip-tools | Una sola estrategia (uv) |
| MinIO | Sin imágenes publicadas (ADR-008) |
| SeaweedFS | Viable (fallback), pero más pesado y con un alcance mayor del necesario, lo que puede ocultar dependencias de operaciones no portables |

## Consequences

- Los PRs F1-02 (backend) y F1-09 (frontend) crean los manifiestos con exactamente estas versiones.
- La baseline tiene fecha de caducidad implícita por las security releases: la de Next.js es inminente (2026-09-30).
- La validación real de Garage con boto3 queda como gate de F1-08.

## Security implications

- Ninguna versión prerelease ni sin soporte.
- La vulnerabilidad pendiente de Next.js está registrada y bloquea la creación del frontend con una versión afectada si ya existe el parche.
- React 19.2.8 incluye todos los fixes de RSC publicados hasta la fecha.
- Las imágenes Docker se fijan por patch (sin `latest`), lo que evita cambios silenciosos.
- La credencial por defecto de Garage (clave y bucket por entorno) es **solo local**; en CI se genera por ejecución. Nunca se reutiliza en producción.

## Operational implications

- Dependabot (Fase 1) cubrirá `uv`, `npm` y `github-actions`; los tags Docker se revisan en la revisión trimestral.
- `.python-version`, `.nvmrc`, `packageManager` y `required-version` (uv) documentan la baseline para personas y agentes de IA.
- Docker no estaba disponible en la máquina de verificación: la ejecución de los contenedores (PostgreSQL, Redis, Mailpit, Garage) sigue pendiente y es un gate de la Fase 1.
