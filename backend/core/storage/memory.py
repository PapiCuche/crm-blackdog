"""`InMemoryStorage` para tests unitarios (ADR-008 §1). Nunca en producción."""

import io
from typing import IO

from core.storage import ObjectInfo, PresignedUpload, check_expiry, check_key, disposition_header


class InMemoryStorage:
    def __init__(self) -> None:
        self.objects: dict[str, tuple[bytes, ObjectInfo]] = {}

    def put(
        self, key: str, stream: IO[bytes], *, content_type: str, content_length: int,
        metadata: dict[str, str] | None = None,
    ) -> ObjectInfo:  # fmt: skip
        check_key(key)
        data = stream.read()
        if len(data) != content_length:
            raise ValueError("content_length no coincide con los bytes recibidos")
        info = ObjectInfo(key, len(data), content_type, dict(metadata or {}))
        self.objects[key] = (data, info)
        return info

    def open(self, key: str) -> IO[bytes]:
        return io.BytesIO(self.objects[check_key(key)][0])

    def head(self, key: str) -> ObjectInfo | None:
        entry = self.objects.get(check_key(key))
        return entry[1] if entry else None

    def delete(self, key: str) -> None:
        self.objects.pop(check_key(key), None)

    def presign_get(
        self, key: str, *, expires_in: int, filename: str, content_type: str,
        disposition: str = "attachment",
    ) -> str:  # fmt: skip
        check_expiry(expires_in)
        header = disposition_header(filename, disposition, content_type)
        return f"memory://{check_key(key)}?disposition={header}"

    def presign_put(
        self, key: str, *, expires_in: int, content_type: str, max_bytes: int
    ) -> PresignedUpload:
        check_expiry(expires_in)
        return PresignedUpload(
            f"memory://{check_key(key)}", {"Content-Type": content_type}, max_bytes
        )
