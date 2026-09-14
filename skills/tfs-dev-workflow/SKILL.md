---
name: tfs-dev-workflow
description: End-to-end TFS development workflow for pulling reviewed user stories from a saved query, developing from a confirmed target branch in temporary feature worktrees, submitting linked pull requests, and preparing the user's main IDE workspace for local testing on the PR source branches. Use when the user asks to pull requirements from TFS, start development from a TFS user story, find a local workspace, finish development and submit PRs, or perform the full TFS-to-code-to-PR workflow including safe post-PR worktree cleanup and workspace switching.
---

# TFS Dev Workflow

## Overview

Use this skill for the full path from TFS requirement selection to local development and PR submission.
It composes `tfs-rest-api` for TFS work items and `tfs-git-pr` for commit, push, PR, auto-complete, and work item linking.

## First Principle: Protect Shared Regional Code

- Treat repositories, modules, classes, APIs, and configuration used by multiple regions or provinces as protected shared code by default.
- Prefer region-specific or project-specific repositories, extension points, controllers, configuration, and frontend routing for a regional requirement.
- Determine the impact scope before editing: inspect repository/module naming, dependencies, call sites, deployment composition, and existing regional overrides.
- If the scope is uncertain, or a regional requirement appears to require changing shared code, stop before editing and tell the user which shared repository or path would change, why it seems necessary, and which other regions may be affected. Proceed only after explicit user confirmation.
- Do not treat a generic request such as "complete this work item" as permission to modify shared code.
- Add isolated code in a shared repository only when it cannot change existing behavior for other regions and its activation is explicitly region-scoped. When that guarantee is unclear, ask the user first.

## Configuration

On first use, collect these values if they are not already known:

- TFS saved query URL for reviewed user stories. It can also be supplied through `TFS_USER_STORY_QUERY_URL`.
- TFS user alias for branch naming, such as `yangtao`. It can also be supplied through `TFS_USER_ALIAS`.
- Target/base branch for the repository. It can also be supplied through `TFS_TARGET_BRANCH`; use `dev` only as a fallback after confirming no repo-specific branch was provided.
- TFS base URL and repository host if they differ from `http://dev.tellhowsoft.com/DefaultCollection` and `dev.tellhowsoft.com`. They can be supplied through `TFS_BASE_URL` and `TFS_REPO_HOST`.
- One or more local repository paths involved in the change. Do not infer a repo mapping unless the user provides it.
- Requirement workspace JSON path, if `tfs-requirement-workspace` already resolved the requirement.

Current user's query example:

```text
http://dev.tellhowsoft.com/DefaultCollection/XiNanArea-New/_queries/query/2fd5f73e-f5bc-4423-b289-7bcb1fb58977
```

That query is expected to return reviewed requirements. The requirement state to start from is `已评审`; after the user confirms development is complete, set only the user story state to `已解决`.

## Required Behavior

- Apply the shared-code protection principle before selecting repositories or exploring implementation paths.
- Only production-required files may be submitted. Documentation and tests remain local unless explicitly requested, and SQL remains local unless the user confirms the exact SQL files for submission.
- Before delegating submission to `tfs-git-pr`, classify every changed path and provide an exact production-file allowlist. Never treat “提交全部修改” as permission to include documentation, tests, SQL, or other non-production files.
- Always use the saved query or an explicit work item id to select the requirement.
- If a requirement workspace JSON exists, use its confirmed repository paths and target branches instead of asking again.
- If no workspace exists, ask the user for local repository path(s). Many features span multiple repos and one startup repo, so do not rely on static module-to-repo mapping unless `tfs-requirement-workspace` has produced a confirmed workspace.
- Before any requirement code exploration or edits, confirm the target/base branch for each involved repository, then update from the latest `origin/<targetBranch>`.
- For each repo that needs changes, start from `origin/<targetBranch>` and create a temporary branch named `feature/<workItemId>-<tfsAlias>`, for example `feature/1551572-yangtao`.
- Never commit directly to the target/base branch and never push directly to it.
- Do not run automated checks by default. After PR creation, summarize changes and tell the user to self-test.
- Do not create tasks, close tasks, update work logs, or write extra TFS comments unless the user explicitly asks.
- Do not merge PRs. Set auto-complete on the PR and configure source branch deletion after completion.
- Do not delete local or remote branches directly. Source branch deletion should be handled by PR completion options.
- Do not overwrite unrelated local changes. If a repo is dirty before the workflow starts, inspect and preserve user changes.
- After all PRs are submitted successfully, clean up temporary worktrees and switch the corresponding clean repositories in the user's main IDE workspace to the PR source branch for local testing. Do not wait for PR merge.
- Never perform this handoff when the main repository or temporary worktree is dirty, the feature commit is not pushed, or the main-workspace mapping is uncertain.

## Workflow

1. **Select requirement**
   - If the user gives a work item id, fetch it directly.
   - Otherwise execute the configured saved query with `scripts/Get-TfsSavedQueryWorkItems.ps1` or `scripts/tfs_workflow.py query`, which defaults to `WorkItemType=用户情景` and `State=已评审`.
   - Show concise candidates and let the user pick if there is ambiguity.

2. **Understand the requirement**
   - Read title, state, area, iteration, description, acceptance criteria, and relations.
   - Confirm the state is `已评审` unless the user intentionally wants another item.
   - Extract the region/module phrase for commit messages, such as `成都-...`.
   - Classify candidate repositories and code paths as project-specific or shared before choosing where to implement.

3. **Collect workspace**
   - If the user provides a workspace JSON, read it and use the listed repositories whose `matchStatus` is `found`.
   - If a repo is `missing`, `remote-mismatch`, or `needs-confirmation`, resolve that before branch preparation.
   - Ask for local repository path(s) that need changes.
   - For multi-repo work, repeat branch preparation and later PR submission per changed repo.
   - Require explicit user confirmation before adding a protected shared repository to the change set for a regional requirement.
   - If a path is not a git repo or does not point to the configured TFS repository host, stop and ask for the correct path.

4. **Update from target branch**
   - Before reading code for implementation, run the branch preparation against the latest `origin/<targetBranch>`.
   - If the repo is already dirty, inspect the changes first and preserve them; do not overwrite unrelated local work.

5. **Prepare branch**
   - Run `scripts/Start-TfsFeatureBranch.ps1` or `scripts/tfs_workflow.py start-branch` for each repo.
   - Branch format must be `feature/<workItemId>-<tfsAlias>`.
   - Base branch must be `origin/<targetBranch>`.

6. **Develop**
   - Make the required code changes in the provided repo(s).
   - Follow the repo's local coding style and existing patterns.
   - Do not run checks unless the user asks or the repo clearly requires a very cheap validation.
   - Do not delete locally useful documentation, tests, SQL, reports, or scratch files merely because they are excluded from submission.

7. **Submit PR**
   - Use `tfs-git-pr` to apply its Production Commit Scope Gate, stage only the exact approved production allowlist, commit, push, create PR to the confirmed target branch, set auto-complete, delete source branch on completion, and link the work item.
   - For each SQL file, obtain explicit user confirmation before staging. If confirmation is absent, omit it; if the feature cannot work correctly without it, stop before commit.
   - Include documentation or test files only when the user explicitly requests that category or exact path.
   - After each PR is created, use the `tfs-git-pr` main-workspace handoff procedure to remove the clean temporary worktree and switch the corresponding clean repository in the user's IDEA/main workspace to the PR source branch.
   - Complete the handoff immediately; do not wait for PR merge. For multi-repository work, verify every involved repository is on the same intended feature branch before reporting readiness for local testing.
   - Commit/PR title format:

     ```text
     type(#workItemId):区域-特性更新内容
     ```

8. **Resolve requirement**
   - Only after the user confirms the requirement is complete, update the user story state to `已解决` with `scripts/Set-TfsWorkItemState.ps1` or `scripts/tfs_workflow.py set-state`.
   - Do not update other fields unless explicitly requested.

9. **Final response**
   - Report requirement id/title.
   - Report repo path(s), branch(es), commit title(s), PR URL(s), and auto-complete/source deletion status.
   - Explain that checks were not run by default and the user should self-test.
   - List documentation, tests, SQL, and other non-production changes that were intentionally left local and unsubmitted.
   - Report which temporary worktrees were removed and the branch now selected in each main-workspace repository. If handoff was skipped, report the dirty or ambiguous path that blocked it.

## References

- Read `references/configuration.md` when setting up saved query URL, user alias, or repo paths.
- Read `references/workflow-rules.md` before executing the workflow.
- Use `tfs-requirement-workspace` when a work item title contains `【标准项目名】` and the repository list should be resolved from the project catalog.
- Use existing `tfs-git-pr` for the commit and PR phase.
- On macOS/Linux, prefer `scripts/tfs_workflow.py`; use PowerShell scripts only when `pwsh` is available.
