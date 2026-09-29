"""Gate estable del CI del backend (A-03, OBS-F1-02-3; docs/architecture/ci-pipeline.md §6).

Dos modos (solo stdlib):
  detect  — decide si el evento toca el backend y escribe `backend_changed=true|false`
            en GITHUB_OUTPUT. En PRs lista los archivos por API (incluido el nombre
            anterior de los renombrados); en push a main el trigger ya filtra por rutas.
  gate    — evalúa los resultados exactos de los jobs y sale con 0 (PASS) o 1 (FAIL).
"""

from __future__ import annotations

import json
import os
import sys

from pr_governance import fetch_files

BACKEND_WORKFLOW = ".github/workflows/backend.yml"
API_FILES_LIMIT = 3000  # la API de archivos de un PR no devuelve más


def is_backend_path(path: str) -> bool:
    return path.startswith("backend/") or path == BACKEND_WORKFLOW


def backend_changed(files: list[dict]) -> bool:
    if len(files) >= API_FILES_LIMIT:
        return True  # lista posiblemente truncada: se ejecuta el CI (fail-safe)
    return any(
        is_backend_path(f.get("filename", "")) or is_backend_path(f.get("previous_filename") or "")
        for f in files
    )


def evaluate(changed: str, detector: str, checks: str, tests: str, docker: str) -> tuple[bool, str]:
    """Estados exactos: nada de "no es failure". `cancelled` o un `skipped` indebido fallan."""
    if detector != "success":
        return False, f"detector en estado {detector!r}"
    jobs = {"backend checks": checks, "backend tests": tests, "backend docker build": docker}
    if changed == "true":
        bad = {name: state for name, state in jobs.items() if state != "success"}
        if bad:
            return False, f"el backend cambió y estos jobs no terminaron en success: {bad}"
        return True, "backend cambió y los tres jobs terminaron en success"
    if changed == "false":
        bad = {name: state for name, state in jobs.items() if state != "skipped"}
        if bad:
            return False, f"sin cambios de backend pero hay jobs no omitidos: {bad}"
        return True, "sin cambios de backend: no-op"
    return False, f"backend_changed inválido: {changed!r}"


def detect() -> int:
    event_name = os.environ["GITHUB_EVENT_NAME"]
    if event_name == "pull_request":
        with open(os.environ["GITHUB_EVENT_PATH"], encoding="utf-8") as fh:
            number = json.load(fh)["pull_request"]["number"]
        files = fetch_files(os.environ["GITHUB_REPOSITORY"], number, os.environ["GITHUB_TOKEN"])
        changed = backend_changed(files)
        detail = f"{len(files)} archivos en el PR"
    else:
        changed, detail = True, f"evento {event_name}: el trigger ya filtra rutas del backend"
    print(f"backend_changed={str(changed).lower()} ({detail})")
    with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as fh:
        fh.write(f"backend_changed={str(changed).lower()}\n")
    return 0


def gate() -> int:
    env = os.environ
    ok, reason = evaluate(
        env.get("BACKEND_CHANGED", ""),
        env.get("DETECTOR_RESULT", ""),
        env.get("CHECKS_RESULT", ""),
        env.get("TESTS_RESULT", ""),
        env.get("DOCKER_RESULT", ""),
    )
    print(f"backend gate: {'PASS' if ok else 'FAIL'} — {reason}")
    summary = env.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as fh:
            fh.write(f"## backend gate\n\n{'✅ PASS' if ok else '❌ FAIL'} — {reason}\n")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit({"detect": detect, "gate": gate}[sys.argv[1]]())
