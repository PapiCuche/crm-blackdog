# CLAUDE.md

Read [AGENTS.md](AGENTS.md) before doing any work. It is the general source of rules; this file only adds the Claude Code workflow.

When the user gives an issue number (or asks for "the next READY issue"):

1. Load the issue with `gh issue view <N>`. To find the next one, run `gh issue list --label status:ready --label work-item --state open`. Pick the lowest phase item; if there is more than one candidate, ask.
2. Read the ADRs and docs linked from the issue, plus `docs/phases/`.
3. Verify the dependencies are merged in `main` and the working tree is clean. If not, stop and report.
4. Work only inside the issue scope ("Incluye" / "No incluye").
5. Create or use the branch declared by the issue, from an up-to-date `origin/main`.
6. Implement.
7. Run the validations required by the issue, plus gitleaks.
8. Commit using Conventional Commits.
9. Push the branch.
10. Open a PR with the repository template, referencing `Closes #N`.
11. Do NOT merge. Do NOT enable auto-merge.
12. Return the PR URL and the handoff summary from AGENTS.md §9.

Accepted ADRs cannot be silently overridden. If the issue contradicts them, stop the affected part and document it in the PR.
