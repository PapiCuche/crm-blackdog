# ADR-008: Almacenamiento de objetos S3-compatible

- **Status:** Accepted
- **Date:** 2026-09-28
- **Deciders:** Product Owner, Tech Lead
- **Related:** ADR-001, decisión D10

## Context

- El sistema almacenará adjuntos, imágenes, audio, documentos, PDFs de cotización, archivos Excel importados y documentos de la base de conocimiento.
- Los blobs pesados no deben guardarse en PostgreSQL.
- El proveedor de hosting no está decidido y **no debe bloquear** el avance: debe poder usarse AWS S3, Cloudflare R2, MinIO local u otro proveedor S3-compatible.
- Las URLs de media de WhatsApp caducan: hay que descargar y conservar.

## Decision

### 1. `ObjectStorageService` (interfaz en `core.storage`)

```text
class ObjectStorageService(Protocol):
    def put(key, stream, *, content_type, content_length, metadata) -> StoredObject
    def open(key) -> BinaryIO                                   # lectura en streaming (workers)
    def head(key) -> ObjectInfo | None
    def delete(key) -> None
    def presign_get(key, *, expires_in, filename, disposition="attachment") -> str
    def presign_put(key, *, expires_in, content_type, max_bytes) -> PresignedUpload   # opcional
```

- **Una única implementación** inicial, `S3CompatibleStorage` (boto3), configurada con `endpoint_url`, `region`, `bucket`, credenciales y `addressing_style`. Cubre S3, R2 y MinIO. `InMemoryStorage` para tests.
- La selección se hace por configuración (`STORAGE_BACKEND`, `STORAGE_ENDPOINT_URL`, …), sin cambios de código.

### 2. Metadatos en BD, bytes en storage

Hay dos tablas de metadatos, según el propietario del objeto:

- **`files` (tenant-owned, RLS):** objetos de una organización (adjuntos, media, PDFs, imports, KB, avatar por organización de una membresía).
- **`platform_files` (platform-owned):** objetos que no pertenecen a ninguna organización. Hoy, solo el **avatar global del usuario** (`users.avatar_platform_file_id`). Una tabla global como `users` **nunca** referencia `files`, que es tenant-owned.

Ambas guardan `storage_key`, `original_name`, `mime_type` (detectado por magic bytes, no confiado del cliente), `size_bytes`, `sha256`, `purpose`, `scan_status` y el autor. **Nunca** los bytes.

### 3. Esquema de claves

```text
org/{organization_id}/{purpose}/{yyyy}/{mm}/{file_uuid}
  purpose ∈ message-media | quote-pdf | import | avatar | kb | attachment
platform/{purpose}/{yyyy}/{mm}/{file_uuid}
  purpose ∈ user-avatar
```

- Las claves no contienen nombres originales (evita path traversal y fugas en logs).
- El prefijo del tenant permite borrados y exportaciones por organización y políticas de ciclo de vida por propósito.

### 4. Acceso

- Bucket **privado**, sin ACL pública ni listado.
- Descarga: el backend verifica tenant y permisos sobre la entidad propietaria (mensaje, cotización…) → emite `presign_get` con una expiración corta (≤ 5 min) y `Content-Disposition` controlado.
- Subida:
  - Archivos pequeños (< 10 MB): a través de la API (validación inmediata).
  - Grandes: `presign_put` con `Content-Type` y un tamaño máximo firmados → el cliente sube → el endpoint `finalize` verifica `head` (tamaño y tipo real) antes de crear el registro `files`. Los objetos sin finalizar se purgan con una regla de ciclo de vida (24 h).
- Media de canales: el worker descarga desde el proveedor (solo hosts permitidos, anti-SSRF) y la sube en streaming.

### 5. Local

Un emulador S3-compatible en docker-compose, con el bucket creado por un contenedor de init y las mismas variables de entorno que en producción.

> **Actualización 2026-09-28 (Fase 0.5):** al fijar las imágenes, se verificó que Docker Hub ya no devuelve etiquetas de `minio/minio` (MinIO dejó de distribuir imágenes de su edición comunitaria). No se adopta MinIO como dependencia local. El emulador se elige en la Fase 1 (decisión **D-ENG-2**) entre **Garage** (`dxflrs/garage`, v2.x mantenida) y **SeaweedFS** (modo S3). Como la interfaz es S3 estándar, la elección no afecta al código. Los tests unitarios usan `InMemoryStorage`; los de integración, el emulador elegido.

## Alternatives considered

| Alternativa | Por qué se descarta |
|---|---|
| Blobs en PostgreSQL (`bytea` / large objects) | Infla backups y réplicas, perjudica el rendimiento; prohibido por requisito |
| Sistema de archivos local del servidor | No escala horizontalmente, backups frágiles |
| django-storages directamente en los modelos (`FileField`) | Útil como adaptador interno, pero acopla el dominio al ORM de archivos; nuestra interfaz propia permite streaming, presign con restricciones y tests en memoria. Puede usarse **dentro** de la implementación si simplifica |
| SDK específico de un proveedor | Dependencia del hosting |

## Consequences

- Un servicio adicional en local y en producción.
- Toda funcionalidad con archivos usa `ObjectStorageService` + `files`. Import-linter prohíbe usar boto3 fuera de `core.storage`.
- La Fase 1 implementa la interfaz, la implementación S3-compatible, InMemory y los tests contra el emulador local elegido (D-ENG-2). Los propósitos concretos llegan con sus fases.

## Security implications

- URLs firmadas de corta duración y emitidas solo tras autorizar. Servir contenido activo (HTML, SVG) siempre como `attachment`.
- Validación del tipo real y del tamaño; antivirus (ClamAV) planificado antes de aceptar archivos de clientes en producción (`scan_status`).
- Cifrado en reposo del proveedor (SSE) activado; TLS en tránsito.
- Las credenciales de storage viven en el entorno o en el gestor de secretos, nunca en BD ni en el frontend.

## Operational implications

- Reglas de ciclo de vida por prefijo: subidas sin finalizar (24 h), imports (90 días), media (configurable por organización, D-CH-4).
- Backups o versionado del bucket según el proveedor elegido; está incluido en el runbook de restauración junto con la BD (la coherencia entre `files` y los objetos se verifica con un job de reconciliación).
- Costes de egress: R2 no los cobra; se tendrá en cuenta al elegir el hosting.
