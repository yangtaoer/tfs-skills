# Codex TFS Skills

This repository collects Codex skills for working with an on-premise TFS / Azure DevOps Server environment.

GitHub: https://github.com/yangtaoer/tfs-skills

The skills cover four common workflows:

- Querying and updating TFS work items through REST APIs.
- Creating and closing daily TFS tasks.
- Committing code to TFS Git and creating pull requests into `dev`.
- Running an end-to-end flow from reviewed user story to local development branch and PR submission.

## Contents

```text
skills/
├── tfs-rest-api/        # Low-level TFS REST API workflow and examples
├── tfs-daily-task/      # Daily task creation, backfill, and task closing workflow
├── tfs-git-pr/          # Git branch, commit, push, PR, auto-complete, work item link workflow
└── tfs-dev-workflow/    # End-to-end user story -> local repo -> branch -> PR workflow
```

## Skill Summary

### `tfs-rest-api`

Use this skill when Codex needs to query or update TFS work items directly.

It documents:

- PAT based Basic Auth.
- WIQL queries.
- Work item CRUD endpoints.
- Classification node / iteration lookup.
- Parent-child links.
- Common TFS pitfalls such as JSON Patch content type, Chinese work item type URL encoding, and WIQL response parsing.

### `tfs-daily-task`

Use this skill for daily report tasks.

It supports:

- Creating an 8-hour `任务`.
- Closing the task immediately after creation.
- Filling standard task descriptions.
- Matching `System.IterationPath` by task start date.
- Backfilling missing workdays.
- Reusing the nearest parent user story when appropriate.

### `tfs-git-pr`

Use this skill when finished code must be submitted to a TFS Git repository under `dev.tellhowsoft.com`.

It enforces:

- Never commit directly on `dev`.
- Create a feature branch from `origin/dev`.
- Use branch format `feature/<workItemId>-<tfsAlias>`, for example `feature/1551572-yangtao`.
- Use commit subject format `type(#workItemId):area-summary`.
- Use the exact commit subject as the PR title.
- Create a PR into `dev`.
- Enable auto-complete and source branch deletion.
- Ensure the PR is linked to the TFS work item.

Bundled script:

```powershell
skills/tfs-git-pr/scripts/New-TfsGitPullRequest.ps1
```

### `tfs-dev-workflow`

Use this skill for the full development workflow.

It guides Codex to:

- Pull reviewed user stories from a configured saved TFS query.
- Ask the user for local repository paths instead of guessing repo mappings.
- Create temporary feature branches from `origin/dev`.
- Develop against the selected local repositories.
- Delegate commit and PR submission to `tfs-git-pr`.
- Update only the user story state to `已解决` after the user confirms completion.

Bundled scripts:

```powershell
skills/tfs-dev-workflow/scripts/Get-TfsSavedQueryWorkItems.ps1
skills/tfs-dev-workflow/scripts/Start-TfsFeatureBranch.ps1
skills/tfs-dev-workflow/scripts/Set-TfsWorkItemState.ps1
```

## Installation

Copy the desired skill directories into your Codex skills directory.

PowerShell example:

```powershell
$repo = "C:\path\to\this\repo"
$skillsHome = "$env:USERPROFILE\.codex\skills"

Copy-Item -Recurse -Force "$repo\skills\tfs-rest-api" "$skillsHome\tfs-rest-api"
Copy-Item -Recurse -Force "$repo\skills\tfs-daily-task" "$skillsHome\tfs-daily-task"
Copy-Item -Recurse -Force "$repo\skills\tfs-git-pr" "$skillsHome\tfs-git-pr"
Copy-Item -Recurse -Force "$repo\skills\tfs-dev-workflow" "$skillsHome\tfs-dev-workflow"
```

Open a new Codex thread after installing or updating skills so the skill metadata is reloaded.

## Required Environment Variables

Set `TFS_PAT` before using scripts that call TFS APIs.

```powershell
$env:TFS_PAT = "<your-personal-access-token>"
```

Optional variables used by the higher-level workflow:

```powershell
$env:TFS_USER_ALIAS = "yangtao"
$env:TFS_USER_STORY_QUERY_URL = "http://dev.tellhowsoft.com/DefaultCollection/XiNanArea-New/_queries/query/<query-id>"
```

Do not commit PATs, passwords, generated request JSON files, logs, or local configuration files.

## Typical Workflows

### Create a daily TFS task

Ask Codex:

```text
帮我按今天的工作创建 TFS 任务，父级是 1580688，内容是完善巴中绩效考核系统交付闭环。
```

Codex should use `tfs-daily-task`, determine the iteration from the task date, create the task, and close it with 8 completed hours.

### Submit code to TFS Git and create PR

Ask Codex:

```text
开发完成了，提交到 TFS，用户情景 1551572，标题用 feat(#1551572):成都-配网拟票自动联想功能优化...
```

Codex should use `tfs-git-pr`, create a feature branch from `origin/dev`, commit, push, create a PR targeting `dev`, enable auto-complete, delete the source branch on completion, and verify the work item link.

### Pull a reviewed TFS story and start development

Ask Codex:

```text
从 TFS 已评审需求里选一个巴中绩效相关需求，仓库路径是 C:\work\workSpaceTellHow\th-dc-biz-bazhong，开始开发。
```

Codex should use `tfs-dev-workflow`, load candidates from the configured saved query, ask for confirmation when needed, create `feature/<workItemId>-<tfsAlias>` from `origin/dev`, then proceed with implementation.

## Safety Rules

These skills are intentionally conservative:

- Do not print or store `TFS_PAT`.
- Do not commit directly to `dev`.
- Do not push directly to `dev`.
- Do not merge PRs manually.
- Do not overwrite unrelated local changes.
- Do not create TFS tasks unless the user requests task creation.
- Do not close tasks, update work logs, or add TFS comments unless explicitly requested.
- Do not run destructive Git operations unless the user explicitly asks.

## Validation

Basic checks used for this repository:

```powershell
# Check PowerShell scripts parse
Get-ChildItem .\skills -Recurse -Filter *.ps1 | ForEach-Object {
  [scriptblock]::Create((Get-Content -LiteralPath $_.FullName -Raw)) | Out-Null
}

# Search for obvious TODO placeholders
Select-String -Path .\skills\*\*.md,.\README.md -Pattern "TODO","[TODO" -SimpleMatch
```

Some Codex skill validation scripts require `PyYAML`. If it is not installed, validate frontmatter manually or install the dependency in your local Python environment.
