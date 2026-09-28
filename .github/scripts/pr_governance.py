"""PR governance checks (ADR-009, docs/architecture/delivery-automation.md).

Validates structure (title, branch, linked issue, required sections, size) and that the
linked issue is a real work item in a workable state whose declared branch matches the PR.
Reads the pull_request event from GITHUB_EVENT_PATH; changed files and issues come from
the GitHub REST API. Standard library only, so it runs on any runner without installs.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass, field

TITLE_RE = re.compile(
    r"^(feat|fix|docs|test|refactor|perf|chore|ci|build|security)(\([a-z0-9._/-]+\))?!?: \S.*$"
)
SLUG = r"[a-z0-9]+(?:-[a-z0-9]+)*"
BRANCH_RE = re.compile(rf"^(?:feature/f\d+-{SLUG}|(?:fix|hotfix|docs|chore)/{SLUG})$")
# Solo palabras de cierre: "Refs #N" puede aparecer, pero nunca identifica al work item.
CLOSING_RE = re.compile(r"\b(?:closes|fixes|resolves)\s+#(\d+)\b", re.IGNORECASE)
BRANCH_SECTION_RE = re.compile(r"^###\s+Rama\s*$\s*^(.+?)\s*$", re.MULTILINE)
WORKABLE_STATUSES = {"status:ready", "status:in-progress"}
FORBIDDEN_STATUSES = {"status:blocked", "status:done"}
REQUIRED_SECTIONS = (
    "Issue / Fase",
    "Objetivo",
    "Cambios",
    "No incluye",
    "Cómo se verificó",
    "Definition of Done",
    "Riesgos y deuda técnica",
    "Autoría",
)
EXCLUDED_PATTERNS = (
    "docs/**",
    "*.lock",
    "uv.lock",
    "pnpm-lock.yaml",
    "package-lock.json",
    "**/migrations/**",
    "generated/**",
    "frontend/src/lib/api/**",
)
WARN_LINES = 400
FAIL_LINES = 800
OVERRIDE_LABEL = "large-pr-approved"
EXEMPT_AUTHORS = ("dependabot[bot]",)


def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    out = ""
    i = 0
    while i < len(pattern):
        if pattern.startswith("**/", i):
            out, i = out + "(?:.*/)?", i + 3
        elif pattern.startswith("**", i):
            out, i = out + ".*", i + 2
        elif pattern[i] == "*":
            out, i = out + "[^/]*", i + 1
        else:
            out, i = out + re.escape(pattern[i]), i + 1
    return re.compile(f"^{out}$")


_EXCLUDED = [(("/" in p), _glob_to_regex(p)) for p in EXCLUDED_PATTERNS]


def is_excluded(path: str) -> bool:
    """Patterns with '/' match the full path; others match the file name (gitignore-like)."""
    name = path.rsplit("/", 1)[-1]
    return any(rx.match(path if has_slash else name) for has_slash, rx in _EXCLUDED)


@dataclass
class Result:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    relevant_lines: int = 0
    excluded_lines: int = 0


def linked_issues(body: str) -> list[int]:
    """Work items cerrados por el PR (Closes/Fixes/Resolves). "Refs" se ignora."""
    return sorted({int(n) for n in CLOSING_RE.findall(body)})


def declared_branch(issue_body: str) -> str | None:
    m = BRANCH_SECTION_RE.search(issue_body or "")
    return m.group(1).strip().strip("`").strip() if m else None


def work_item_errors(number: int, issue: dict | None, branch: str) -> list[str]:
    if issue is None:
        return [f"El issue #{number} no existe"]
    if "pull_request" in issue:
        return [f"#{number} es un PR, no un issue"]
    labels = {lbl.get("name") for lbl in issue.get("labels") or []}
    errors = []
    if "work-item" not in labels:
        errors.append(f"El issue #{number} no tiene el label 'work-item'")
    forbidden = sorted(labels & FORBIDDEN_STATUSES)
    if forbidden:
        errors.append(f"El issue #{number} está en {', '.join(forbidden)}")
    elif not labels & WORKABLE_STATUSES:
        errors.append(f"El issue #{number} no está en status:ready ni status:in-progress")
    declared = declared_branch(issue.get("body") or "")
    if declared != branch:
        errors.append(f"La rama del PR {branch!r} no coincide con la declarada en #{number} ({declared!r})")
    return errors


def missing_sections(body: str) -> list[str]:
    headings = {m.group(1).strip() for m in re.finditer(r"^##\s+(.+?)\s*$", body, re.MULTILINE)}
    return [s for s in REQUIRED_SECTIONS if s not in headings]


def evaluate(pr: dict, files: list[dict], issues: dict[int, dict | None]) -> Result:
    res = Result()
    title = pr.get("title") or ""
    branch = (pr.get("head") or {}).get("ref") or ""
    body = pr.get("body") or ""
    labels = {lbl.get("name") for lbl in pr.get("labels") or []}

    if not TITLE_RE.match(title):
        res.errors.append(f"Título no sigue Conventional Commits: {title!r}")
    if not BRANCH_RE.match(branch):
        res.errors.append(
            f"Rama inválida {branch!r}: usar feature/f<N>-<slug>, fix/, hotfix/, docs/ o chore/<slug>"
        )
    numbers = linked_issues(body)
    if not numbers:
        res.errors.append(
            "El PR no cierra un work item: usar Closes/Fixes/Resolves #N (Refs solo para referencias adicionales)"
        )
    elif len(numbers) > 1:
        res.errors.append(
            f"El PR cierra {len(numbers)} work items ({', '.join(f'#{n}' for n in numbers)}): "
            "1 issue = 1 rama = 1 PR"
        )
    else:
        res.errors.extend(work_item_errors(numbers[0], issues.get(numbers[0]), branch))
    for section in missing_sections(body):
        res.errors.append(f"Falta la sección obligatoria '## {section}'")

    for f in files:
        lines = int(f.get("additions", 0)) + int(f.get("deletions", 0))
        if is_excluded(f.get("filename", "")):
            res.excluded_lines += lines
        else:
            res.relevant_lines += lines

    n = res.relevant_lines
    if n > FAIL_LINES:
        msg = f"PR de {n} líneas relevantes (> {FAIL_LINES}): dividirlo (ADR-009)"
        if OVERRIDE_LABEL in labels:
            res.warnings.append(msg + f" — permitido por el label '{OVERRIDE_LABEL}'")
        else:
            res.errors.append(msg)
    elif n > WARN_LINES:
        res.warnings.append(f"PR de {n} líneas relevantes (> {WARN_LINES}): objetivo de ADR-009 superado")
    return res


def _get(url: str, token: str):
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def fetch_issue(repo: str, number: int, token: str) -> dict | None:
    try:
        return _get(f"https://api.github.com/repos/{repo}/issues/{number}", token)
    except urllib.error.HTTPError as exc:
        if exc.code in (404, 410):
            return None
        raise


def fetch_files(repo: str, number: int, token: str) -> list[dict]:
    files: list[dict] = []
    for page in range(1, 31):  # la API devuelve como máximo 3000 archivos
        batch = _get(f"https://api.github.com/repos/{repo}/pulls/{number}/files?per_page=100&page={page}", token)
        files.extend(batch)
        if len(batch) < 100:
            break
    return files


def write_summary(res: Result, exempt: bool) -> None:
    path = os.environ.get("GITHUB_STEP_SUMMARY")
    lines = ["## PR governance", ""]
    if exempt:
        lines.append("PR de autor exento (bot de dependencias): solo se informa.")
    lines += [
        f"- Líneas relevantes: **{res.relevant_lines}** (excluidas: {res.excluded_lines})",
        f"- Errores: {len(res.errors)} · Avisos: {len(res.warnings)}",
        "",
    ]
    lines += [f"- ❌ {e}" for e in res.errors] + [f"- ⚠️ {w}" for w in res.warnings]
    if path:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write("\n".join(lines) + "\n")


def main() -> int:
    with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as fh:
        pr = json.load(fh)["pull_request"]
    repo, token = os.environ["GITHUB_REPOSITORY"], os.environ["GITHUB_TOKEN"]
    files = fetch_files(repo, pr["number"], token)
    issues = {n: fetch_issue(repo, n, token) for n in linked_issues(pr.get("body") or "")}
    res = evaluate(pr, files, issues)
    exempt = (pr.get("user") or {}).get("login") in EXEMPT_AUTHORS
    write_summary(res, exempt)
    for w in res.warnings:
        print(f"::warning title=PR governance::{w}")
    for e in res.errors:
        print(f"::{'warning' if exempt else 'error'} title=PR governance::{e}")
    return 0 if exempt or not res.errors else 1


if __name__ == "__main__":
    sys.exit(main())
