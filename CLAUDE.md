# CLAUDE.md

Read [AGENTS.md](AGENTS.md) before doing any work. It is the general source of rules; this file only adds the Claude Code workflow.

## "continuar" (no issue number given)

If the user only says `continuar` (or `sigamos`, `siguiente`, `continúa con el proyecto`…) and gives no issue number, ask GitHub. Do not ask the user to paste the issue.

```bash
gh issue list --state open --label work-item --label status:ready --json number,title
# or, with the reasons that block the next item:
python3 .github/scripts/work_item_dependencies.py next   # needs GITHUB_REPOSITORY and GITHUB_TOKEN
```

- **Exactly 1** → execute that issue following AGENTS.md.
- **0** → do not invent work. Reply briefly `No hay work item status:ready.` and show what blocks the next one: open dependencies and missing gates.
- **More than 1** → do not choose. List the numbers and titles and ask the user to pick one.

## Executing an issue

1. Load the issue with `gh issue view <N>`.
2. Read the ADRs and docs it links, plus `docs/phases/`.
3. Verify its dependencies are closed, the working tree is clean and `main` is up to date. If not, stop and report.
4. Work only inside the issue scope ("Incluye" / "No incluye").
5. Create or use the branch declared by the issue, from an up-to-date `origin/main`.
6. Implement.
7. Run the validations required by the issue, plus gitleaks.
8. Commit using Conventional Commits.
9. Push the branch.
10. Open a PR with the repository template, referencing `Closes #N`.
11. Wait for the real checks, then fill `## Handoff para Reviewer` in the PR body with the current HEAD and the real results (AGENTS.md §9).
12. Do NOT merge. Do NOT enable auto-merge.
13. Reply briefly, e.g. `PR #N listo para revisión. El handoff está actualizado en el PR.`

Accepted ADRs cannot be silently overridden. If the issue contradicts them, stop the affected part and document it in the PR.
