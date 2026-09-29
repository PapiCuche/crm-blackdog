"""Orquestador de dependencias de work items (A-04, docs/architecture/delivery-automation.md).

Modos (solo stdlib):
  sync  — (workflow trusted) pasa `status:blocked` → `status:ready` SOLO si todas las
          dependencias explícitas están CLOSED y todos los `required-check:*` existen en
          el ruleset de la rama por defecto. Comenta en el issue y en su issue maestro.
          Nunca toca `status:in-progress` ni `status:done`. DRY_RUN=1 no muta nada.
  next  — (comando `continuar` del Builder) muestra el único work item `status:ready`,
          o qué bloquea al siguiente. Con varios, no escoge.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, field

READY, BLOCKED, IN_PROGRESS, DONE = "status:ready", "status:blocked", "status:in-progress", "status:done"
DEPENDENCY_LINE = re.compile(r"^\s*[-*]\s+#(\d+)\b")
GATE_LINE = re.compile(r"^\s*(?:[-*]\s+)?`?required-check:([^`]+?)`?\s*$")
MASTER_LINE = re.compile(r"^Issue maestro:\s*#(\d+)\s*$", re.M)


def section(body: str, title: str) -> str | None:
    """Contenido de `### <title>` hasta el siguiente `### ` (None si no existe)."""
    m = re.search(rf"^###\s+{re.escape(title)}\s*$(.*?)(?=^###\s|\Z)", body or "", re.M | re.S)
    return m.group(1) if m else None


def parse_dependencies(body: str) -> list[int] | None:
    """`- #N` por línea dentro de `### Dependencias`; None si falta la sección."""
    text = section(body, "Dependencias")
    if text is None:
        return None
    return sorted({int(m.group(1)) for line in text.splitlines() if (m := DEPENDENCY_LINE.match(line))})


def declares_no_dependencies(body: str) -> bool:
    text = (section(body, "Dependencias") or "").strip().lower()
    return text.startswith("ninguna")


def parse_gates(body: str) -> list[str]:
    text = section(body, "Gates") or ""
    return sorted({m.group(1).strip() for line in text.splitlines() if (m := GATE_LINE.match(line))})


def labels_of(issue: dict) -> set[str]:
    return {lbl.get("name") for lbl in issue.get("labels") or []}


@dataclass
class Decision:
    ready: bool
    reasons: list[str] = field(default_factory=list)


def evaluate(issue: dict, deps: dict[int, dict | None], required_checks: set[str]) -> Decision:
    labels = labels_of(issue)
    n = issue.get("number")
    if issue.get("state", "").lower() != "open":
        return Decision(False, [f"#{n} no está abierto"])
    if "work-item" not in labels:
        return Decision(False, [f"#{n} no es work-item"])
    if IN_PROGRESS in labels or DONE in labels:
        return Decision(False, [f"#{n} en in-progress/done: no se toca"])
    if BLOCKED not in labels:
        return Decision(False, [f"#{n} no está en {BLOCKED}"])
    body = issue.get("body") or ""
    numbers = parse_dependencies(body)
    reasons: list[str] = []
    if numbers is None:
        reasons.append("falta la sección ### Dependencias")
    elif not numbers and not declares_no_dependencies(body):
        reasons.append("### Dependencias sin `- #N` ni 'Ninguna'")
    for d in numbers or []:
        dep = deps.get(d)
        if dep is None:
            reasons.append(f"dependencia #{d} no existe")
        elif "pull_request" in dep:
            reasons.append(f"dependencia #{d} es un PR, no un work item")
        elif dep.get("state", "").lower() != "closed":
            reasons.append(f"dependencia #{d} abierta")
    for gate in parse_gates(body):
        if gate not in required_checks:
            reasons.append(f"gate ausente en el ruleset: required-check:{gate}")
    return Decision(not reasons, reasons)


def select_next(ready_issues: list[dict]) -> tuple[dict | None, str]:
    if len(ready_issues) == 1:
        i = ready_issues[0]
        return i, f"Siguiente: #{i['number']} — {i['title']}"
    if not ready_issues:
        return None, "No hay work item status:ready."
    listing = ", ".join(f"#{i['number']} {i['title']}" for i in sorted(ready_issues, key=lambda i: i["number"]))
    return None, f"Hay {len(ready_issues)} work items status:ready; elige uno: {listing}"


def declared_branch(body: str) -> str:
    text = (section(body, "Rama") or "").strip().splitlines()
    return text[0].strip().strip("`") if text else "(no declarada)"


def master_of(body: str) -> int | None:
    m = MASTER_LINE.search(body or "")
    return int(m.group(1)) if m else None


# --- API -----------------------------------------------------------------------------------


class Api:
    def __init__(self, repo: str, token: str, dry_run: bool) -> None:
        self.base, self.token, self.dry_run = f"https://api.github.com/repos/{repo}", token, dry_run

    def call(self, method: str, path: str, payload: dict | None = None):
        req = urllib.request.Request(
            self.base + path,
            method=method,
            data=None if payload is None else json.dumps(payload).encode(),
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read()
        return json.loads(raw) if raw else None

    def issues(self, labels: str) -> list[dict]:
        out: list[dict] = []
        for page in range(1, 11):
            batch = self.call("GET", f"/issues?state=open&labels={urllib.parse.quote(labels)}&per_page=100&page={page}")
            out += [i for i in batch if "pull_request" not in i]
            if len(batch) < 100:
                return out
        return out

    def issue(self, number: int) -> dict | None:
        try:
            return self.call("GET", f"/issues/{number}")
        except urllib.error.HTTPError as exc:
            if exc.code in (404, 410):
                return None
            raise

    def required_checks(self, branch: str) -> set[str]:
        rules = self.call("GET", f"/rules/branches/{urllib.parse.quote(branch, safe='')}")
        return {
            c["context"]
            for r in rules or []
            if r.get("type") == "required_status_checks"
            for c in (r.get("parameters") or {}).get("required_status_checks", [])
        }

    def write(self, method: str, path: str, payload: dict | None = None) -> None:
        if self.dry_run:
            print(f"[dry-run] {method} {path} {payload or ''}")
        else:
            self.call(method, path, payload)


def sync(api: Api, default_branch: str, completed: int | None) -> int:
    checks = api.required_checks(default_branch)
    cache: dict[int, dict | None] = {}
    promoted: dict[int | None, list[dict]] = {}
    for issue in api.issues(f"work-item,{BLOCKED}"):
        numbers = parse_dependencies(issue.get("body") or "") or []
        for d in numbers:
            if d not in cache:
                cache[d] = api.issue(d)
        decision = evaluate(issue, {d: cache[d] for d in numbers}, checks)
        n = issue["number"]
        if not decision.ready:
            print(f"#{n} sigue bloqueado: {'; '.join(decision.reasons)}")
            continue
        branch = declared_branch(issue.get("body") or "")
        api.write("DELETE", f"/issues/{n}/labels/{urllib.parse.quote(BLOCKED, safe='')}")
        api.write("POST", f"/issues/{n}/labels", {"labels": [READY]})
        api.write("POST", f"/issues/{n}/comments", {"body": (
            "✅ Dependencias satisfechas.\n\nEste work item está listo.\n\n"
            f"Rama: `{branch}`\n\nSiguiente comando para Builder:\n`continuar`")})
        print(f"#{n}: {BLOCKED} → {READY}")
        promoted.setdefault(master_of(issue.get("body") or ""), []).append({**issue, "branch": branch})
    for master, items in promoted.items():
        if master is None:
            continue
        lines = [f"Work item completado: #{completed}"] if completed else []
        lines += [f"Siguiente ready: #{i['number']} — {i['title']}\nRama: `{i['branch']}`" for i in items]
        api.write("POST", f"/issues/{master}/comments", {"body": "\n".join(lines) + "\n\nBuilder: `continuar`"})
    return 0


def next_item(api: Api, default_branch: str) -> int:
    chosen, message = select_next(api.issues(f"work-item,{READY}"))
    print(message)
    if chosen is not None:
        print(f"Rama: {declared_branch(chosen.get('body') or '')}")
        return 0
    if message.startswith("No hay"):
        checks = api.required_checks(default_branch)
        for issue in sorted(api.issues(f"work-item,{BLOCKED}"), key=lambda i: i["number"]):
            numbers = parse_dependencies(issue.get("body") or "") or []
            decision = evaluate(issue, {d: api.issue(d) for d in numbers}, checks)
            print(f"  #{issue['number']} {issue['title']}: {'; '.join(decision.reasons) or 'listo'}")
    return 0


def main() -> int:
    env = os.environ
    api = Api(env["GITHUB_REPOSITORY"], env["GITHUB_TOKEN"], env.get("DRY_RUN") == "1")
    default_branch = env.get("DEFAULT_BRANCH", "main")
    if sys.argv[1] == "next":
        return next_item(api, default_branch)
    completed = None
    if env.get("GITHUB_EVENT_NAME") == "issues" and env.get("GITHUB_EVENT_PATH"):
        with open(env["GITHUB_EVENT_PATH"], encoding="utf-8") as fh:
            event = json.load(fh)
        if event.get("action") == "closed":
            completed = event["issue"]["number"]
    return sync(api, default_branch, completed)


if __name__ == "__main__":
    sys.exit(main())
