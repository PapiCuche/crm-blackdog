import unittest

from pr_governance import REQUIRED_SECTIONS, declared_branch, evaluate, is_excluded, linked_issues

BRANCH = "feature/f1-backend-skeleton"
BODY = "Closes #4\n\n" + "\n".join(f"## {s}\n\ntexto\n" for s in REQUIRED_SECTIONS)


def issue(labels=("work-item", "status:ready"), branch=BRANCH):
    body = f"### ID / Fase\n\nF1-02\n\n### Rama\n\n`{branch}`\n\n### Objetivo\n\nx\n"
    return {"number": 4, "body": body, "labels": [{"name": n} for n in labels]}


def pr(title="feat(backend): create Django skeleton", branch=BRANCH, body=BODY, labels=()):
    return {"title": title, "head": {"ref": branch}, "body": body,
            "labels": [{"name": n} for n in labels]}


def files(n, name="backend/app.py"):
    return [{"filename": name, "additions": n, "deletions": 0}]


def run(p=None, f=(), issues=None):
    return evaluate(p or pr(), list(f), {4: issue()} if issues is None else issues)


def branch_ok(b):
    return {4: issue(branch=b)}


class GovernanceTest(unittest.TestCase):
    def test_valid_pr_passes(self):
        res = run(f=files(120))
        self.assertEqual(res.errors, [])
        self.assertEqual(res.warnings, [])

    def test_valid_titles(self):
        for t in ("security(tenancy): enforce RLS context", "docs(adr): update runtime baseline",
                  "chore(project): automate delivery workflow", "fix: handle empty body"):
            self.assertEqual(run(pr(title=t)).errors, [], t)

    def test_invalid_title_fails(self):
        for t in ("Add backend", "feature(backend): x", "feat(backend):missing space", "feat(Backend): x"):
            self.assertTrue(any("Título" in e for e in run(pr(title=t)).errors), t)

    def test_invalid_branch_fails(self):
        for b in ("main", "feature/backend-skeleton", "feature/phase-0.5-architecture",
                  "chore/Project_Automation", "feat/f1-x"):
            self.assertTrue(any("Rama" in e for e in run(pr(branch=b), issues=branch_ok(b)).errors), b)

    def test_valid_branches(self):
        for b in ("feature/f1-backend-skeleton", "fix/login-loop", "hotfix/csrf", "docs/adr-013",
                  "chore/project-automation"):
            self.assertEqual(run(pr(branch=b), issues=branch_ok(b)).errors, [], b)

    def test_missing_issue_fails(self):
        res = run(pr(body=BODY.replace("Closes #4", "")))
        self.assertTrue(any("no referencia un issue" in e for e in res.errors))

    def test_other_issue_keywords(self):
        for kw in ("Fixes #4", "Resolves #4", "Refs #4", "closes #4"):
            self.assertEqual(run(pr(body=BODY.replace("Closes #4", kw))).errors, [], kw)

    def test_missing_section_fails(self):
        res = run(pr(body=BODY.replace("## No incluye", "## Otra")))
        self.assertIn("Falta la sección obligatoria '## No incluye'", res.errors)

    def test_size_thresholds(self):
        self.assertEqual(run(f=files(400)).warnings, [])
        res = run(f=files(401))
        self.assertEqual((len(res.errors), len(res.warnings)), (0, 1))
        res = run(f=files(801))
        self.assertEqual((len(res.errors), len(res.warnings)), (1, 0))

    def test_override_label_turns_fail_into_warning(self):
        res = run(pr(labels=("large-pr-approved",)), files(900))
        self.assertEqual((len(res.errors), len(res.warnings)), (0, 1))

    def test_excluded_paths(self):
        for p in ("docs/adr/ADR-013.md", "backend/uv.lock", "frontend/pnpm-lock.yaml", "package-lock.json",
                  "backend/apps/contacts/migrations/0001_initial.py", "generated/schema.ts",
                  "frontend/src/lib/api/client.ts", "poetry.lock"):
            self.assertTrue(is_excluded(p), p)
        for p in ("backend/core/tenancy/scope.py", "AGENTS.md", "frontend/src/app/page.tsx",
                  "backend/docs.py", "infra/docker/compose.yaml"):
            self.assertFalse(is_excluded(p), p)

    def test_excluded_lines_do_not_count(self):
        res = run(f=files(5000, "docs/fase-0/02-modelo-de-datos.md") + files(10))
        self.assertEqual((res.relevant_lines, res.excluded_lines, res.errors), (10, 5000, []))


class WorkItemTest(unittest.TestCase):
    def assertFails(self, res, fragment):
        self.assertTrue(any(fragment in e for e in res.errors), res.errors)

    def test_nonexistent_issue_fails(self):
        self.assertFails(run(issues={4: None}), "no existe")

    def test_issue_without_work_item_label_fails(self):
        self.assertFails(run(issues={4: issue(labels=("status:ready",))}), "'work-item'")

    def test_blocked_fails(self):
        self.assertFails(run(issues={4: issue(labels=("work-item", "status:blocked"))}), "status:blocked")

    def test_done_fails(self):
        self.assertFails(run(issues={4: issue(labels=("work-item", "status:done"))}), "status:done")

    def test_ready_passes(self):
        self.assertEqual(run(issues={4: issue(labels=("work-item", "status:ready"))}).errors, [])

    def test_in_progress_passes(self):
        self.assertEqual(run(issues={4: issue(labels=("work-item", "status:in-progress"))}).errors, [])

    def test_blocked_and_in_progress_fails(self):
        labels = ("work-item", "status:in-progress", "status:blocked")
        self.assertFails(run(issues={4: issue(labels=labels)}), "status:blocked")

    def test_no_status_fails(self):
        self.assertFails(run(issues={4: issue(labels=("work-item",))}), "status:ready ni status:in-progress")

    def test_different_branch_fails(self):
        self.assertFails(run(issues={4: issue(branch="feature/f1-db-roles-rls-core")}), "no coincide")

    def test_matching_branch_passes(self):
        self.assertEqual(run(issues={4: issue(branch=BRANCH)}).errors, [])

    def test_pull_request_number_fails(self):
        self.assertFails(run(issues={4: {**issue(), "pull_request": {}}}), "es un PR")

    def test_linked_issues_prefers_closing_keywords(self):
        self.assertEqual(linked_issues("Closes #3\nRefs #13"), [3])
        self.assertEqual(linked_issues("Refs #13"), [13])
        self.assertEqual(linked_issues("Closes #3, fixes #5"), [3, 5])

    def test_declared_branch_parsing(self):
        self.assertEqual(declared_branch("### Rama\n\n`chore/project-automation`\n"), "chore/project-automation")
        self.assertEqual(declared_branch("### Rama\n\nfix/x\n\n### Objetivo"), "fix/x")
        self.assertIsNone(declared_branch("### Objetivo\n\nx"))


if __name__ == "__main__":
    unittest.main()
