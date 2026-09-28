"""PR governance checks (ADR-009, docs/architecture/delivery-automation.md).

Validates structure only: title, branch, linked issue, required sections and size.
Reads the pull_request event from GITHUB_EVENT_PATH and the changed files from the
GitHub REST API. Standard library only, so it runs on any runner without installs.
"""

from __future__ import annotations

import json
import os
import re
import sys
import urllib.request
from dataclasses import dataclass, field

TITLE_RE = re.compile(
    r"^(feat|fix|docs|test|refactor|perf|chore|ci|build|security)(\([a-z0-9._/-]+\))?!?: \S.*$"
)
SLUG = r"[a-z0-9]+(?:-[a-z0-9]+)*"
BRANCH_RE = re.compile(rf"^(?:feature/f\d+-{SLUG}|(?:fix|hotfix|docs|chore)/{SLUG})$")
ISSUE_RE = re.compile(r"\b(?:closes|fixes|resolves|refs)\s+#\d+\b", re.IGNORECASE)
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


def missing_sections(body: str) -> list[str]:
    headings = {m.group(1).strip() for m in re.finditer(r"^##\s+(.+?)\s*$", body, re.MULTILINE)}
    return [s for s in REQUIRED_SECTIONS if s not in headings]


def evaluate(pr: dict, files: list[dict]) -> Result:
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
    if not ISSUE_RE.search(body):
        res.errors.append("El cuerpo no referencia un issue (Closes #N / Fixes #N / Resolves #N / Refs #N)")
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


def fetch_files(repo: str, number: int, token: str) -> list[dict]:
    files: list[dict] = []
    for page in range(1, 31):  # la API devuelve como máximo 3000 archivos
        req = urllib.request.Request(
            f"https://api.github.com/repos/{repo}/pulls/{number}/files?per_page=100&page={page}",
            headers={
                "Authorization": f"Bearer {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            },
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            batch = json.load(resp)
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
    files = fetch_files(os.environ["GITHUB_REPOSITORY"], pr["number"], os.environ["GITHUB_TOKEN"])
    res = evaluate(pr, files)
    exempt = (pr.get("user") or {}).get("login") in EXEMPT_AUTHORS
    write_summary(res, exempt)
    for w in res.warnings:
        print(f"::warning title=PR governance::{w}")
    for e in res.errors:
        print(f"::{'warning' if exempt else 'error'} title=PR governance::{e}")
    return 0 if exempt or not res.errors else 1


if __name__ == "__main__":
    sys.exit(main())
