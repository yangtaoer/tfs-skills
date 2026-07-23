---
name: tfs-git-pr
description: "Commit finished code changes to Azure DevOps Server/TFS Git repositories, create pull requests into the confirmed target branch, and prepare the user's main IDE workspace for local testing. Use when the user asks to submit code to TFS, push to a TFS remote repository such as dev.tellhowsoft.com, create a merge/pull request, or finish development by committing and handing off code. Enforces safe feature branching, standardized work-item commits, PR auto-complete with source deletion, work-item linking, and post-PR cleanup of temporary worktrees before switching clean main repositories to the PR source branch."
---

# TFS Git PR

## Overview

Use this skill to turn finished local code changes into a TFS Git pull request targeting the confirmed target branch.
The workflow protects the base branch, standardizes commit messages, and makes TFS work item linking reliable.

## Core Rules

- Before staging or publishing, classify each changed repository and path as project-specific or shared. Do not commit, push, or create a PR for unconfirmed shared-code changes made for a regional requirement. If the scope is uncertain, stop and ask the user to confirm the exact shared repository and accepted impact.
- Treat configured TFS remotes as Azure DevOps Server repositories. Default host is `dev.tellhowsoft.com`; override with `TFS_REPO_HOST` when needed.
- Never commit directly on the target/base branch or push directly to it.
- Confirm the target/base branch on first use. Use `TFS_TARGET_BRANCH` if set; otherwise use `dev` only as a fallback.
- Before committing, fetch `origin/<targetBranch>` and create or switch to a feature branch based on it.
- Prefer `feature/<workItemId>-<tfsAlias>` as the default source branch unless the user named another branch, for example `feature/1551572-yangtao`.
- Get `<tfsAlias>` from the user or `TFS_USER_ALIAS`.
- If the default feature branch already exists and is unsuitable for the current work, create a unique branch such as `feature/<workItemId>-<tfsAlias>-YYYYMMDD-HHmm`.
- The PR target branch is the confirmed target branch.
- The PR title must exactly match the commit subject.
- Set PR auto-complete to enabled after creating or reusing the PR, and configure source branch deletion on completion.
- The commit subject must include the TFS work item id in the format `type(#workItemId):area-summary`.
- If the user does not provide a work item id, first search the configured saved TFS query (`TFS_USER_STORY_QUERY_URL`) for a related user story, then ask the user only if no relevant item is found.
- Choose the Conventional Commit type from the change:
  - `feat` for new features or feature improvements.
  - `fix` for bug fixes.
  - `perf` for performance-only changes.
  - `refactor` for behavior-preserving restructuring.
  - `docs`, `test`, `chore`, `build`, or `ci` when they fit better.
- Use a specific area prefix before the summary, for example `成都-配网拟票自动联想功能优化`.
- After every successful PR submission, prepare the user's main IDE workspace for immediate local testing; do not wait for the PR to merge.
- Remove a temporary feature worktree and switch the corresponding clean main repository to the PR source branch only after verifying that the temporary worktree is clean and its HEAD is pushed to `origin/<sourceBranch>`.
- If the main repository is dirty, the temporary worktree has unpushed changes, or the main workspace is ambiguous, do not remove or switch anything. Report the exact blocker to the user.

Example:

```text
feat(#1551572):成都-配网拟票自动联想功能优化：命令模式交互升级、动词剔除匹配、性能优化(防抖+索引+DocumentFragment)
```

## Workflow

1. Locate the repository, confirm its `origin` remote points to the configured TFS host, and verify that any shared-code scope was explicitly approved.
2. Inspect `git status --short --branch`, current branch, remotes, and recent commits.
3. Identify the work item id. If the user has not provided it, first execute the configured saved TFS query and pick the most relevant user story by title/area/state. Saved queries may be one-hop link queries, so inspect `workItemRelations` as well as `workItems`. If no relevant user story is found, ask the user for the id before committing.
4. Build the commit subject using `type(#workItemId):area-summary`. If the user gives an exact commit message, use it as-is after checking the format.
5. Fetch `origin/<targetBranch>`.
6. Ensure the current branch is not the target/base branch. If needed, create a feature branch from `origin/<targetBranch>` before committing.
7. Stage only the intended files. Do not stage unrelated local changes.
8. Commit with the standardized subject.
9. Push the source branch to origin.
10. Create a PR from the source branch to the confirmed target branch with the commit subject as the title.
11. Set PR auto-complete to enabled and configure source branch deletion.
12. Verify that the PR links to the work item. If the title or commit association does not link it automatically, add a TFS ArtifactLink explicitly.
13. For each submitted repository, hand the PR source branch back to the user's main IDE workspace:
    - Confirm the temporary worktree and main repository are clean.
    - Confirm the temporary worktree HEAD equals `origin/<sourceBranch>`.
    - Remove the temporary worktree through `git worktree remove`, then run `git worktree prune`.
    - Switch the main repository to the source branch, creating a local tracking branch if needed.
    - Verify the selected branch, upstream, and clean status.
    - Do not wait for PR merge. If the source branch was already deleted after merge, update and use the confirmed target branch instead.
14. Report the PR id, source branch, target branch, title, auto-complete/source deletion status, web URL, and main-workspace handoff result.

## Branch Commands

Use these patterns with judgment after inspecting the worktree:

```powershell
git fetch origin <targetBranch>
git switch -c feature/<workItemId>-<tfsAlias> origin/<targetBranch>
git status --short
git add <intended-files>
git commit -m "<type(#workItemId):area-summary>"
git push -u origin feature/<workItemId>-<tfsAlias>
```

If the source branch already exists locally:

```powershell
git fetch origin <targetBranch>
git switch feature/<workItemId>-<tfsAlias>
```

Do not run destructive branch reset commands unless the user explicitly asks.

## PR Creation

Use `scripts/New-TfsGitPullRequest.ps1` after the branch has been pushed. On macOS/Linux, prefer `scripts/new_tfs_git_pull_request.py` unless PowerShell Core (`pwsh`) is available.

Required inputs:

- `-RepoPath`: local repository path.
- `-Title`: exact commit subject.
- `-SourceBranch`: feature branch name, without `refs/heads/`.
- `-TargetBranch`: confirmed PR target branch; defaults from `TFS_TARGET_BRANCH` or falls back to `dev`.
- `-WorkItemId`: TFS user story/work item id.

Example:

```powershell
& "$env:USERPROFILE\.codex\skills\tfs-git-pr\scripts\New-TfsGitPullRequest.ps1" `
  -RepoPath "C:\path\to\repo" `
  -SourceBranch "feature/1551572-yangtao" `
  -TargetBranch "dev" `
  -Title "feat(#1551572):成都-配网拟票自动联想功能优化：命令模式交互升级、动词剔除匹配、性能优化(防抖+索引+DocumentFragment)" `
  -WorkItemId 1551572
```

The script reads `TFS_PAT` from the environment, discovers the TFS project and repository from `origin`, creates or reuses the active PR, enables auto-complete with source branch deletion, and ensures the work item is linked.

## Main Workspace Handoff

On Windows, use `scripts/Switch-TfsMainWorkspace.ps1` after the PR has been created successfully. Run it once per changed repository:

```powershell
& "$env:USERPROFILE\.codex\skills\tfs-git-pr\scripts\Switch-TfsMainWorkspace.ps1" `
  -MainRepoPath "C:\path\to\idea-workspace\repository" `
  -SourceBranch "feature/1551572-yangtao" `
  -TemporaryWorktreePath "C:\path\to\temporary-worktree"
```

The script refuses to proceed when either worktree is dirty, the temporary worktree is registered to another repository, or its commit is not on the remote source branch. Never replace these checks with `--force`.

Python example:

```bash
python3 ~/.codex/skills/tfs-git-pr/scripts/new_tfs_git_pull_request.py \
  --repo-path /path/to/repo \
  --source-branch feature/1551572-yangtao \
  --target-branch "${TFS_TARGET_BRANCH:-dev}" \
  --title "feat(#1551572):成都-配网拟票自动联想功能优化：命令模式交互升级、动词剔除匹配、性能优化(防抖+索引+DocumentFragment)" \
  --work-item-id 1551572
```

## References

- Read `references/commit-and-pr-rules.md` when composing a commit message or deciding the branch/PR behavior.
- Read `references/tfs-api-notes.md` when debugging TFS REST failures or adjusting the PR/work item link script.
