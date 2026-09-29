"""Identificadores técnicos (ADR-004 §1, ADR-012 §2): UUIDv7 de la stdlib de Python 3.14.

Todo el código genera IDs con `new_id()`, nunca con `uuid` directamente, para no depender
de la implementación. Se generan en la aplicación (el ID existe antes del INSERT); la BD
tiene `DEFAULT uuidv7()` de respaldo para inserts SQL directos.
"""

import uuid


def new_id() -> uuid.UUID:
    return uuid.uuid7()
