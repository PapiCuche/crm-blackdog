"""Trust boundary de los workflows `pull_request_target` (A-02, delivery-automation.md §5).

Análisis estático con la stdlib: ningún workflow trusted hace checkout del head del PR,
ejecuta código del PR, interpola `${{ }}` dentro de `run` ni pide permisos de escritura
más allá de los permitidos.
"""

import pathlib
import re
import unittest

WORKFLOWS = pathlib.Path(__file__).resolve().parents[1] / "workflows"
ALLOWED_WRITES = {"work-item-state.yml": {"issues"}}
TRUSTED_REFS = ("github.event.repository.default_branch", "github.event.pull_request.base.sha")
FORBIDDEN_IN_RUN = re.compile(r"\b(pip3? install|npm (ci|install)|pnpm install|uv sync|eval)\b")


def trusted_workflows():
    return [p for p in sorted(WORKFLOWS.glob("*.yml")) if re.search(r"^\s*pull_request_target\s*:", p.read_text(), re.M)]


def run_blocks(text):
    lines = text.splitlines()
    blocks = []
    for i, line in enumerate(lines):
        m = re.match(r"^(\s*)(?:- )?run:\s*(.*)$", line)
        if not m:
            continue
        indent, inline = len(m.group(1)), m.group(2)
        if inline not in ("|", ">", "|-", ">-"):
            blocks.append(inline)
            continue
        body = []
        for nxt in lines[i + 1:]:
            if nxt.strip() and len(nxt) - len(nxt.lstrip()) <= indent:
                break
            body.append(nxt)
        blocks.append("\n".join(body))
    return blocks


def permissions(text):
    m = re.search(r"^permissions:\n((?:[ \t]+.*\n?)+)", text, re.M)
    return dict(re.findall(r"^\s+([\w-]+):\s*(\w+)", m.group(1), re.M)) if m else {}


class TrustBoundaryTest(unittest.TestCase):
    def test_trusted_workflows_exist(self):
        names = {p.name for p in trusted_workflows()}
        self.assertTrue({"pr-governance-trusted.yml", "work-item-state.yml"} <= names, names)

    def test_trusted_governance_job_name(self):
        text = (WORKFLOWS / "pr-governance-trusted.yml").read_text()
        self.assertRegex(text, r"(?m)^\s+name: PR governance \(trusted\)\s*$")

    def test_no_head_references(self):
        for p in trusted_workflows():
            self.assertNotRegex(p.read_text(), r"pull_request\.head\.(sha|ref)\b", p.name)

    def test_checkout_only_trusted_refs(self):
        for p in trusted_workflows():
            text = p.read_text()
            for m in re.finditer(r"uses:\s*actions/checkout@\S+[^\n]*\n((?:\s+.*\n)*?)(?=\s*- |\Z)", text):
                refs = re.findall(r"ref:\s*(.+)", m.group(1))
                self.assertTrue(refs, f"{p.name}: checkout sin ref explícito")
                for ref in refs:
                    self.assertTrue(any(t in ref for t in TRUSTED_REFS), f"{p.name}: ref no trusted {ref}")

    def test_no_expressions_or_installs_in_run(self):
        for p in trusted_workflows():
            for block in run_blocks(p.read_text()):
                self.assertNotIn("${{", block, f"{p.name}: interpolación en run")
                self.assertIsNone(FORBIDDEN_IN_RUN.search(block), f"{p.name}: comando prohibido")

    def test_no_local_actions(self):
        for p in trusted_workflows():
            self.assertNotRegex(p.read_text(), r"uses:\s*\./", p.name)

    def test_minimal_permissions(self):
        for p in trusted_workflows():
            perms = permissions(p.read_text())
            self.assertTrue(perms, f"{p.name}: sin bloque permissions")
            writes = {k for k, v in perms.items() if v != "read"}
            self.assertLessEqual(writes, ALLOWED_WRITES.get(p.name, set()), f"{p.name}: {perms}")


if __name__ == "__main__":
    unittest.main()
