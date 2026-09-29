import unittest

from backend_gate import backend_changed, evaluate, is_backend_path

S, F, C, K = "success", "failure", "cancelled", "skipped"


class GateTest(unittest.TestCase):
    def assertPass(self, *args):
        ok, reason = evaluate(*args)
        self.assertTrue(ok, reason)

    def assertFail(self, *args):
        ok, reason = evaluate(*args)
        self.assertFalse(ok, reason)

    def test_docs_only_is_noop_pass(self):
        self.assertPass("false", S, K, K, K)

    def test_backend_change_all_success_passes(self):
        self.assertPass("true", S, S, S, S)

    def test_checks_failure_fails(self):
        self.assertFail("true", S, F, S, S)

    def test_tests_failure_fails(self):
        self.assertFail("true", S, S, F, S)

    def test_docker_failure_fails(self):
        self.assertFail("true", S, S, S, F)

    def test_checks_cancelled_fails(self):
        self.assertFail("true", S, C, S, S)

    def test_tests_cancelled_fails(self):
        self.assertFail("true", S, S, C, S)

    def test_docker_cancelled_fails(self):
        self.assertFail("true", S, S, S, C)

    def test_detector_failure_or_cancel_fails(self):
        for state in (F, C, K, ""):
            self.assertFail("", state, K, K, K)
            self.assertFail("false", state, K, K, K)

    def test_changed_with_any_skipped_job_fails(self):
        for jobs in ((K, S, S), (S, K, S), (S, S, K), (K, K, K)):
            self.assertFail("true", S, *jobs)

    def test_unchanged_with_skipped_jobs_passes(self):
        self.assertPass("false", S, K, K, K)

    def test_unchanged_but_jobs_ran_or_failed_fails(self):
        self.assertFail("false", S, F, K, K)
        self.assertFail("false", S, S, K, K)

    def test_invalid_changed_value_fails(self):
        for value in ("", "True", "yes", "maybe"):
            self.assertFail(value, S, S, S, S)


class DetectorTest(unittest.TestCase):
    def test_backend_paths(self):
        for p in ("backend/pyproject.toml", "backend/core/health.py", ".github/workflows/backend.yml"):
            self.assertTrue(is_backend_path(p), p)
        for p in ("docs/phases/phase-1.md", "backend-docs/x.md", "frontend/app.tsx",
                  ".github/workflows/backend.yml.bak", "AGENTS.md", "backend"):
            self.assertFalse(is_backend_path(p), p)

    def test_docs_only_pr_is_unchanged(self):
        self.assertFalse(backend_changed([{"filename": "docs/a.md"}, {"filename": "README.md"}]))

    def test_backend_file_or_workflow_is_changed(self):
        self.assertTrue(backend_changed([{"filename": "docs/a.md"}, {"filename": "backend/manage.py"}]))
        self.assertTrue(backend_changed([{"filename": ".github/workflows/backend.yml"}]))

    def test_rename_out_of_backend_is_changed(self):
        self.assertTrue(backend_changed([{"filename": "docs/x.py", "previous_filename": "backend/x.py"}]))

    def test_truncated_file_list_is_fail_safe(self):
        self.assertTrue(backend_changed([{"filename": f"docs/{i}.md"} for i in range(3000)]))


if __name__ == "__main__":
    unittest.main()
