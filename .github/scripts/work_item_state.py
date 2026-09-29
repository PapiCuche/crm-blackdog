"""Transiciones de estado del work item (A-02, docs/architecture/delivery-automation.md §2).

Se ejecuta SOLO desde un checkout trusted de la rama por defecto (`work-item-state.yml`,
`pull_request_target`). Reutiliza la identificación del work item de `pr_governance` para
que las dos implementaciones no diverjan.

Invariante: ningún workflow con permisos de escritura muta un work item que no corresponda
exactamente al PR (un solo issue de cierre, issue real con `work-item`, rama declarada ==
rama del PR) ni cuyo estado de origen no permita la transición.
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

from pr_governance import declared_branch, fetch_issue, linked_issues

READY, IN_PROGRESS, BLOCKED, DONE = "status:ready", "status:in-progress", "status:blocked", "status:done"
STATUSES = (READY, IN_PROGRESS, BLOCKED, DONE)


@dataclass
class Plan:
    issue: int | None = None
    add: str | None = None
    remove: list[str] = field(default_factory=list)
    reason: str = ""

    @property
    def mutates(self) -> bool:
        return self.add is not None or bool(self.remove)


def target_issue(body: str) -> int | None:
    numbers = linked_issues(body)
    return numbers[0] if len(numbers) == 1 else None


def plan_transition(action: str, merged: bool, head_ref: str, body: str, issue: dict | None) -> Plan:
    n = target_issue(body)
    if n is None:
        return Plan(reason="se requiere exactamente un work item de cierre (Closes/Fixes/Resolves)")
    if issue is None:
        return Plan(n, reason=f"#{n} no existe")
    if "pull_request" in issue:
        return Plan(n, reason=f"#{n} es un PR, no un work item")
    labels = {lbl.get("name") for lbl in issue.get("labels") or []}
    if "work-item" not in labels:
        return Plan(n, reason=f"#{n} no es un work item")
    if declared_branch(issue.get("body") or "") != head_ref:
        return Plan(n, reason=f"la rama del PR no coincide con la declarada en #{n}")

    if action == "closed" and merged:
        stale = [s for s in (READY, IN_PROGRESS, BLOCKED) if s in labels]
        if DONE in labels and not stale:
            return Plan(n, reason=f"#{n} ya está en {DONE}")
        return Plan(n, add=None if DONE in labels else DONE, remove=stale, reason="PR mergeado")
    if BLOCKED in labels or DONE in labels:
        return Plan(n, reason=f"#{n} está blocked/done: no se muta")
    if action in ("opened", "ready_for_review"):
        if IN_PROGRESS in labels:
            return Plan(n, reason=f"#{n} ya está en {IN_PROGRESS} (idempotente)")
        if READY in labels:
            return Plan(n, add=IN_PROGRESS, remove=[READY], reason="PR abierto")
        return Plan(n, reason=f"#{n} no está en {READY}")
    if action == "closed":
        if IN_PROGRESS in labels:
            return Plan(n, add=READY, remove=[IN_PROGRESS], reason="PR cerrado sin merge")
        return Plan(n, reason=f"#{n} no estaba en {IN_PROGRESS}")
    return Plan(n, reason=f"acción {action!r} ignorada")


def _call(method: str, url: str, token: str, payload: dict | None = None) -> None:
    req = urllib.request.Request(
        url,
        method=method,
        data=None if payload is None else json.dumps(payload).encode(),
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=30):
        pass


def apply(repo: str, token: str, plan: Plan) -> None:
    # Primero se añade y después se quita: el issue nunca queda sin estado. Si no, la
    # governance trusted, concurrente, puede leerlo sin status (A-04, OBS-A-04-1).
    base = f"https://api.github.com/repos/{repo}/issues/{plan.issue}/labels"
    if plan.add:
        _call("POST", base, token, {"labels": [plan.add]})
    for label in plan.remove:
        try:
            _call("DELETE", f"{base}/{urllib.parse.quote(label, safe='')}", token)
        except urllib.error.HTTPError as exc:
            if exc.code != 404:
                raise


def main() -> int:
    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as fh:
        event = json.load(fh)
    pr = event["pull_request"]
    repo, token = os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_TOKEN"]
    body = pr.get("body") or ""
    n = target_issue(body)
    issue = fetch_issue(repo, n, token) if n is not None else None
    plan = plan_transition(event.get("action", ""), bool(pr.get("merged")), os.environ["PR_HEAD_REF"], body, issue)
    if plan.mutates:
        apply(repo, token, plan)
        print(f"#{plan.issue}: -{plan.remove} +{plan.add} ({plan.reason})")
    else:
        print(f"Sin cambios: {plan.reason}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
