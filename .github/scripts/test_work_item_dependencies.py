import unittest

from work_item_dependencies import (
    BLOCKED, DONE, IN_PROGRESS, READY, evaluate, parse_dependencies, parse_gates, select_next,
)

BODY = """### ID / Fase

F1-03 · referencia a #99 fuera de dependencias

### Rama

`feature/f1-db-roles-rls-core`

### Dependencias

- #4 — F1-02 (PR #17, ✅ cerrado)
- #18 — A-03
- #4 — duplicada

Texto con #77 que no es una dependencia.

### Gates

- `required-check:backend gate`

### Incluye

- ver #55
"""


def issue(*status, body=BODY, state="open", number=5, work_item=True):
    labels = (["work-item"] if work_item else []) + list(status)
    return {"number": number, "title": "F1-03", "state": state, "body": body,
            "labels": [{"name": n} for n in labels]}


def closed(n):
    return {"number": n, "state": "closed", "labels": []}


def opened(n):
    return {"number": n, "state": "open", "labels": []}


ALL_CLOSED = {4: closed(4), 18: closed(18)}
CHECKS = {"secret scanning (gitleaks)", "PR governance (trusted)", "backend gate"}


class ParserTest(unittest.TestCase):
    def test_single_dependency(self):
        self.assertEqual(parse_dependencies("### Dependencias\n\n- #4\n"), [4])

    def test_multiple_and_duplicates(self):
        self.assertEqual(parse_dependencies(BODY), [4, 18])

    def test_numbers_outside_section_or_not_leading_are_ignored(self):
        deps = parse_dependencies(BODY)
        for n in (99, 77, 55, 17):
            self.assertNotIn(n, deps)

    def test_missing_section_is_none(self):
        self.assertIsNone(parse_dependencies("### Rama\n\nx\n"))

    def test_gates(self):
        self.assertEqual(parse_gates(BODY), ["backend gate"])
        self.assertEqual(parse_gates("### Gates\n\n_No response_\n"), [])
        self.assertEqual(parse_gates("### Gates\n\nrequired-check:a\n- required-check:b\n"), ["a", "b"])


class EvaluateTest(unittest.TestCase):
    def test_open_dependency_blocks(self):
        d = evaluate(issue(BLOCKED), {4: closed(4), 18: opened(18)}, CHECKS)
        self.assertFalse(d.ready)
        self.assertIn("dependencia #18 abierta", d.reasons)

    def test_closed_dependency_is_satisfied(self):
        self.assertTrue(evaluate(issue(BLOCKED, body="### Dependencias\n\n- #4\n"), {4: closed(4)}, set()).ready)

    def test_all_closed_and_gate_present_is_ready(self):
        self.assertTrue(evaluate(issue(BLOCKED), ALL_CLOSED, CHECKS).ready)

    def test_required_check_missing_blocks(self):
        d = evaluate(issue(BLOCKED), ALL_CLOSED, CHECKS - {"backend gate"})
        self.assertFalse(d.ready)
        self.assertIn("gate ausente en el ruleset: required-check:backend gate", d.reasons)

    def test_missing_or_pr_dependency_blocks(self):
        self.assertFalse(evaluate(issue(BLOCKED), {4: closed(4), 18: None}, CHECKS).ready)
        self.assertFalse(evaluate(issue(BLOCKED), {4: closed(4), 18: {**closed(18), "pull_request": {}}}, CHECKS).ready)

    def test_in_progress_or_done_never_touched(self):
        self.assertFalse(evaluate(issue(IN_PROGRESS), ALL_CLOSED, CHECKS).ready)
        self.assertFalse(evaluate(issue(DONE), ALL_CLOSED, CHECKS).ready)
        self.assertFalse(evaluate(issue(BLOCKED, IN_PROGRESS), ALL_CLOSED, CHECKS).ready)

    def test_only_blocked_open_work_items(self):
        self.assertFalse(evaluate(issue(READY), ALL_CLOSED, CHECKS).ready)
        self.assertFalse(evaluate(issue(BLOCKED, state="closed"), ALL_CLOSED, CHECKS).ready)
        self.assertFalse(evaluate(issue(BLOCKED, work_item=False), ALL_CLOSED, CHECKS).ready)

    def test_no_explicit_dependencies_is_not_inferred(self):
        self.assertFalse(evaluate(issue(BLOCKED, body="### Rama\n\nx\n"), {}, CHECKS).ready)
        self.assertFalse(evaluate(issue(BLOCKED, body="### Dependencias\n\nF1-02 y F1-03\n"), {}, CHECKS).ready)
        self.assertTrue(evaluate(issue(BLOCKED, body="### Dependencias\n\nNinguna.\n"), {}, CHECKS).ready)


class ContinueTest(unittest.TestCase):
    def test_zero_ready(self):
        chosen, msg = select_next([])
        self.assertIsNone(chosen)
        self.assertIn("No hay work item status:ready", msg)

    def test_one_ready(self):
        chosen, _ = select_next([issue(READY, number=20)])
        self.assertEqual(chosen["number"], 20)

    def test_many_ready_does_not_choose(self):
        chosen, msg = select_next([issue(READY, number=21), issue(READY, number=20)])
        self.assertIsNone(chosen)
        self.assertIn("#20", msg)
        self.assertIn("#21", msg)


if __name__ == "__main__":
    unittest.main()
