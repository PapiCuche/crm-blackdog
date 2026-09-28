import unittest

from work_item_state import BLOCKED, DONE, IN_PROGRESS, READY, plan_transition

BRANCH = "feature/f1-backend-skeleton"


def issue(*status, branch=BRANCH, work_item=True):
    labels = (["work-item"] if work_item else []) + list(status)
    body = f"### ID / Fase\n\nF1-02\n\n### Rama\n\n`{branch}`\n\n### Objetivo\n\nx\n"
    return {"number": 4, "body": body, "labels": [{"name": n} for n in labels]}


def plan(issue_obj, action="opened", merged=False, head=BRANCH, body="Closes #4\nRefs #13"):
    return plan_transition(action, merged, head, body, issue_obj)


class WorkItemStateTest(unittest.TestCase):
    def assertNoMutation(self, p):
        self.assertFalse(p.mutates, p)

    def test_ready_to_in_progress(self):
        p = plan(issue(READY))
        self.assertEqual((p.issue, p.add, p.remove), (4, IN_PROGRESS, [READY]))

    def test_ready_for_review_also_moves(self):
        self.assertEqual(plan(issue(READY), action="ready_for_review").add, IN_PROGRESS)

    def test_branch_mismatch_no_mutation(self):
        self.assertNoMutation(plan(issue(READY), head="fix/incorrecta"))
        self.assertNoMutation(plan(issue(IN_PROGRESS), action="closed", merged=True, head="fix/incorrecta"))

    def test_pull_request_number_no_mutation(self):
        self.assertNoMutation(plan({**issue(READY), "pull_request": {}}))

    def test_nonexistent_issue_no_mutation(self):
        self.assertNoMutation(plan(None))

    def test_without_work_item_no_mutation(self):
        self.assertNoMutation(plan(issue(READY, work_item=False)))

    def test_blocked_no_mutation(self):
        self.assertNoMutation(plan(issue(BLOCKED)))

    def test_blocked_and_in_progress_no_mutation(self):
        self.assertNoMutation(plan(issue(BLOCKED, IN_PROGRESS)))
        self.assertNoMutation(plan(issue(BLOCKED, IN_PROGRESS), action="closed"))

    def test_done_no_mutation(self):
        self.assertNoMutation(plan(issue(DONE)))
        self.assertNoMutation(plan(issue(DONE, READY)))

    def test_without_status_no_mutation(self):
        self.assertNoMutation(plan(issue()))

    def test_in_progress_on_open_is_idempotent(self):
        self.assertNoMutation(plan(issue(IN_PROGRESS)))

    def test_closed_unmerged_in_progress_to_ready(self):
        p = plan(issue(IN_PROGRESS), action="closed")
        self.assertEqual((p.add, p.remove), (READY, [IN_PROGRESS]))

    def test_closed_unmerged_ready_no_mutation(self):
        self.assertNoMutation(plan(issue(READY), action="closed"))

    def test_merged_to_done(self):
        p = plan(issue(IN_PROGRESS), action="closed", merged=True)
        self.assertEqual((p.add, p.remove), (DONE, [IN_PROGRESS]))

    def test_merged_cleans_inconsistent_states(self):
        p = plan(issue(READY, IN_PROGRESS, BLOCKED), action="closed", merged=True)
        self.assertEqual((p.add, sorted(p.remove)), (DONE, sorted([READY, IN_PROGRESS, BLOCKED])))
        p = plan(issue(DONE, IN_PROGRESS), action="closed", merged=True)
        self.assertEqual((p.add, p.remove), (None, [IN_PROGRESS]))

    def test_merged_already_done_no_mutation(self):
        self.assertNoMutation(plan(issue(DONE), action="closed", merged=True))

    def test_multiple_closing_issues_no_mutation(self):
        self.assertNoMutation(plan(issue(READY), body="Closes #4\nFixes #5"))

    def test_refs_only_no_mutation(self):
        self.assertNoMutation(plan(issue(READY), body="Refs #4"))


if __name__ == "__main__":
    unittest.main()
