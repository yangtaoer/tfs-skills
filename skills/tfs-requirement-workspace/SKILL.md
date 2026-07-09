---
name: tfs-requirement-workspace
description: Use when a TFS user story or requirement must be turned into a local multi-repository development workspace, including project bracket parsing, repository resolution, local clone detection, target branch confirmation, and feature branch preparation.
---

# TFS Requirement Workspace

## Overview

Turn a TFS requirement into a confirmed local development workspace. A workspace is a requirement-level record that lists all involved repositories, local paths, remotes, target branches, feature branches, and preparation status.

## Required Sub-Skills

- Use `tfs-project-catalog` to resolve project names and repositories.
- Use `tfs-dev-workflow` after the workspace exists and development should begin.
- Use `tfs-git-pr` later for committing and PR submission.

## Workspace Workflow

1. Get the work item id and title. If only an id is provided, fetch the TFS story first.
2. Parse bracketed standard project names from the title.
3. If the title has no brackets, resolve project aliases from title/description through `tfs-project-catalog` and require confirmation.
4. Load the project catalog and collect all repositories for the matched projects.
5. Scan configured local repo roots or a local repo index.
6. Match each catalog repository to a local git repo by remote URL first, then repository name.
7. For missing repositories, ask the user for a local path or permission to clone; do not guess.
8. Confirm target/base branch for every repository. Use catalog `targetBranch` as default.
9. Create a workspace JSON under a user-level workspace root, preferably:

   ```text
   %USERPROFILE%\.codex\tfs-workspaces\<workItemId>\workspace.json
   ```

10. Prepare feature branches only after repo paths and target branches are confirmed. Branch format:

   ```text
   feature/<workItemId>-<tfsAlias>
   ```

11. Hand off the workspace to `tfs-dev-workflow` for code exploration and implementation.

## Matching Rules

- Remote URL match beats repository name match.
- If one project maps to frontend and backend repos, keep both.
- If several projects are bracketed, union all repositories and de-duplicate by remote URL.
- If a local repo path exists but the remote differs from the catalog, mark it as `remote-mismatch` and ask the user.
- If a repo has uncommitted changes before branch preparation, inspect and preserve them; do not overwrite.

## Helper Script

Use the shared resolver:

```powershell
py -3 skills\tfs-project-catalog\scripts\resolve_tfs_workspace.py --help
```

Typical dry run:

```powershell
py -3 skills\tfs-project-catalog\scripts\resolve_tfs_workspace.py `
  --catalog .\project-catalog.json `
  --work-item-id 1551572 `
  --title "【四川省调网络发令系统】新增发令审核提醒" `
  --repo-root C:\work\workSpaceTellHow
```

The script does not create git branches. Use it to resolve and write workspace metadata, then run branch preparation with `tfs-dev-workflow`.

## Workspace Contract

A workspace must include:

- Work item id and title.
- Matched standard project names.
- Repository list with name, role, remote, targetBranch, localPath, match status.
- Feature branch name.
- Creation timestamp.

Read `references/workspace-schema.md` for the JSON shape.

## Safety Rules

- Do not prepare branches until the repo list is confirmed.
- Do not clone repositories without user approval.
- Do not store PATs in workspace files.
- Do not write workspace files into business repositories unless the user explicitly asks.
