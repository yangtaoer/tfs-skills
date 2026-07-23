# Workflow Rules

## First Principle: Protect Shared Regional Code

- Classify every candidate repository, module, class, API, and configuration path as project-specific or shared before editing.
- Prefer regional/project-specific extension points over changes to code used by multiple regions or provinces.
- Do not change existing shared behavior for a regional requirement unless the user explicitly approves after being told the exact shared repository/path, the reason, and the likely cross-region impact.
- Do not infer that approval from a generic request to complete a requirement.
- Allow new code in a shared repository only when it is isolated, region-scoped, and cannot affect existing consumers; ask the user when any of those conditions is uncertain.
- Re-check the changed repository list before commit and PR creation. If it contains an unconfirmed shared repository, stop and request confirmation.
- If an unapproved shared-code PR already exists and the user has explicitly disallowed that scope, prevent accidental merge and replace it with a regional implementation.

## Requirement Selection

- Use a configured saved query to find reviewed user stories.
- Query results may be flat or one-hop link results. Inspect both `workItems` and `workItemRelations`, but default candidate selection should filter to `用户情景` with state `已评审`.
- If multiple candidates are plausible, present a short list and ask the user to pick.
- Treat `已评审` as the normal start state.

## Branching

- Before any requirement code exploration or edits, confirm the target/base branch for each involved repository.
- Use `TFS_TARGET_BRANCH` if set; otherwise default to `dev` only after confirming the repo does not use another base branch.
- Always fetch `origin/<targetBranch>`.
- Create temporary branches from `origin/<targetBranch>`.
- Branch format:

```text
feature/<workItemId>-<tfsAlias>
```

Example:

```text
feature/1551572-yangtao
```

- Do not commit on the target/base branch.
- Do not overwrite existing local changes.

## PR and Completion

- Use `tfs-git-pr` for commit and PR creation.
- PR target is the confirmed target branch.
- PR title equals commit subject.
- Enable auto-complete.
- Configure source branch deletion through PR completion options.
- Do not merge PR manually.

## Local Testing Handoff

- After successful PR creation, prepare the user's main IDE workspace immediately; do not wait for PR merge.
- For each changed repository, verify the temporary worktree is clean and fully pushed, verify the main repository is clean, then remove the temporary worktree with `git worktree remove` and prune stale metadata.
- Switch the main repository to the PR source branch and verify its upstream and clean status.
- For multi-repository changes, place every involved main-workspace repository on the intended feature branch before telling the user local testing is ready.
- If any safety check fails, preserve both worktrees and report the exact path and reason. Never force removal or overwrite local changes.

## TFS Updates

- After the user confirms the requirement is complete, update only the user story state to `已解决`.
- Do not create child tasks unless the user explicitly asks.
- Do not close tasks, update work logs, add comments, or change iteration by default.

## Validation

- Do not run build/test/lint by default.
- In the final response, state that checks were not run and ask the user to self-test.
