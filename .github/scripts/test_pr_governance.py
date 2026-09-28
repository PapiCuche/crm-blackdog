import unittest

from pr_governance import REQUIRED_SECTIONS, evaluate, is_excluded

BODY = "Closes #4\n\n" + "\n".join(f"## {s}\n\ntexto\n" for s in REQUIRED_SECTIONS)


def pr(title="feat(backend): create Django skeleton", branch="feature/f1-backend-skeleton",
       body=BODY, labels=()):
    return {"title": title, "head": {"ref": branch}, "body": body,
            "labels": [{"name": n} for n in labels]}


def files(n, name="backend/app.py"):
    return [{"filename": name, "additions": n, "deletions": 0}]


class GovernanceTest(unittest.TestCase):
    def test_valid_pr_passes(self):
        res = evaluate(pr(), files(120))
        self.assertEqual(res.errors, [])
        self.assertEqual(res.warnings, [])

    def test_valid_titles(self):
        for t in ("security(tenancy): enforce RLS context", "docs(adr): update runtime baseline",
                  "chore(project): automate delivery workflow", "fix: handle empty body"):
            self.assertEqual(evaluate(pr(title=t), []).errors, [], t)

    def test_invalid_title_fails(self):
        for t in ("Add backend", "feature(backend): x", "feat(backend):missing space", "feat(Backend): x"):
            self.assertTrue(any("Título" in e for e in evaluate(pr(title=t), []).errors), t)

    def test_invalid_branch_fails(self):
        for b in ("main", "feature/backend-skeleton", "feature/phase-0.5-architecture",
                  "chore/Project_Automation", "feat/f1-x"):
            self.assertTrue(any("Rama" in e for e in evaluate(pr(branch=b), []).errors), b)

    def test_valid_branches(self):
        for b in ("feature/f1-backend-skeleton", "fix/login-loop", "hotfix/csrf", "docs/adr-013",
                  "chore/project-automation"):
            self.assertEqual(evaluate(pr(branch=b), []).errors, [], b)

    def test_missing_issue_fails(self):
        res = evaluate(pr(body=BODY.replace("Closes #4", "")), [])
        self.assertTrue(any("issue" in e for e in res.errors))

    def test_other_issue_keywords(self):
        for kw in ("Fixes #4", "Resolves #4", "Refs #4", "closes #4"):
            self.assertEqual(evaluate(pr(body=BODY.replace("Closes #4", kw)), []).errors, [], kw)

    def test_missing_section_fails(self):
        res = evaluate(pr(body=BODY.replace("## No incluye", "## Otra")), [])
        self.assertIn("Falta la sección obligatoria '## No incluye'", res.errors)

    def test_size_thresholds(self):
        self.assertEqual(evaluate(pr(), files(400)).warnings, [])
        res = evaluate(pr(), files(401))
        self.assertEqual((len(res.errors), len(res.warnings)), (0, 1))
        res = evaluate(pr(), files(801))
        self.assertEqual((len(res.errors), len(res.warnings)), (1, 0))

    def test_override_label_turns_fail_into_warning(self):
        res = evaluate(pr(labels=("large-pr-approved",)), files(900))
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
        res = evaluate(pr(), files(5000, "docs/fase-0/02-modelo-de-datos.md") + files(10))
        self.assertEqual((res.relevant_lines, res.excluded_lines, res.errors), (10, 5000, []))


if __name__ == "__main__":
    unittest.main()
