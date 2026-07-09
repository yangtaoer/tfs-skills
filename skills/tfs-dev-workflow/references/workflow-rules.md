# Workflow Rules

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

## TFS Updates

- After the user confirms the requirement is complete, update only the user story state to `已解决`.
- Do not create child tasks unless the user explicitly asks.
- Do not close tasks, update work logs, add comments, or change iteration by default.

## Validation

- Do not run build/test/lint by default.
- In the final response, state that checks were not run and ask the user to self-test.
