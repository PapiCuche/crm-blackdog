"""Tareas Celery con contexto explícito (tenancy-context §3).

- `@tenant_task`: exige `organization_id` (kwarg) al encolar y ejecuta el cuerpo en `tenant_scope`.
- `@platform_task`: sin tenant (TenantManager falla dentro).
- `TenancyCheck`: bootstep del worker; si hay una tarea registrada sin decorar, no arranca.
"""

import functools
from collections.abc import Callable
from typing import Any
from uuid import UUID

from celery import Task, bootsteps, shared_task

from core.tenancy.context import ActorType, TenantContext, TenantContextError
from core.tenancy.scope import assert_clean_connection, tenant_scope


class TenantTask(Task):  # type: ignore[misc]
    tenancy = "tenant"

    def apply_async(self, args: Any = None, kwargs: Any = None, **options: Any) -> Any:
        try:
            UUID(str((kwargs or {})["organization_id"]))
        except KeyError, ValueError:
            msg = f"{self.name}: organization_id (kwarg UUID) es obligatorio"
            raise TenantContextError(msg) from None
        return super().apply_async(args, kwargs, **options)


class PlatformTask(Task):  # type: ignore[misc]
    tenancy = "platform"


def tenant_task(**options: Any) -> Callable[[Callable[..., Any]], Any]:
    def decorate(fn: Callable[..., Any]) -> Any:
        @functools.wraps(fn)
        def run(
            *args: Any,
            organization_id: str,
            actor_type: str = ActorType.SYSTEM,
            actor_id: str | None = None,
            correlation_id: str | None = None,
            **kwargs: Any,
        ) -> Any:
            actor = UUID(actor_id) if actor_id else None
            ctx = TenantContext(
                UUID(organization_id), "celery", None, ActorType(actor_type), actor, correlation_id
            )
            assert_clean_connection()
            with tenant_scope(ctx):  # los argumentos son IDs: se re-lee el estado aquí
                return fn(*args, **kwargs)

        return shared_task(base=TenantTask, **options)(run)

    return decorate


def platform_task(**options: Any) -> Callable[[Callable[..., Any]], Any]:
    def decorate(fn: Callable[..., Any]) -> Any:
        @functools.wraps(fn)
        def run(*args: Any, **kwargs: Any) -> Any:
            assert_clean_connection()
            return fn(*args, **kwargs)

        return shared_task(base=PlatformTask, **options)(run)

    return decorate


def undecorated_tasks(tasks: dict[str, Any]) -> list[str]:
    return sorted(
        name
        for name, task in tasks.items()
        if not name.startswith("celery.")
        and getattr(task, "tenancy", None) not in ("tenant", "platform")
    )


class TenancyCheck(bootsteps.Step):  # type: ignore[misc]
    """Se instancia al construir el WorkController: una excepción aquí impide el arranque."""

    def __init__(self, worker: Any, **kwargs: Any) -> None:
        worker.app.loader.import_default_modules()
        if missing := undecorated_tasks(dict(worker.app.tasks)):
            raise TenantContextError(
                "Tareas sin @tenant_task/@platform_task: " + ", ".join(missing)
            )
        super().__init__(worker, **kwargs)
