# Configuration

## Required Values

Collect these values on first use:

```text
TFS_USER_STORY_QUERY_URL=<saved query URL>
TFS_USER_ALIAS=<personal branch alias, e.g. yangtao>
TFS_TARGET_BRANCH=<repo target/base branch, e.g. dev>
TFS_BASE_URL=<TFS collection URL>
TFS_REPO_HOST=<TFS git host>
```

The values may be provided by the user in conversation or set as environment variables.

User-specific example:

```text
TFS_USER_STORY_QUERY_URL=http://dev.tellhowsoft.com/DefaultCollection/XiNanArea-New/_queries/query/2fd5f73e-f5bc-4423-b289-7bcb1fb58977
TFS_USER_ALIAS=your-alias
TFS_TARGET_BRANCH=dev
TFS_BASE_URL=http://dev.tellhowsoft.com/DefaultCollection
TFS_REPO_HOST=dev.tellhowsoft.com
```

Do not store `TFS_PAT` in this skill. Read it from the environment only.

Confirm `TFS_TARGET_BRANCH` per repository. Some repositories may use `main`, `master`, `develop`, a release branch, or another team-specific branch instead of `dev`.

## Repository Paths

Always ask the user for local repository path(s) for the current requirement.

Reasons:

- A feature may span multiple repos.
- One repo may be only a startup/composition repo.
- Static area-to-repo mapping is unreliable for this environment.

If several repos are provided, prepare a branch for each repo but only commit and create PRs for repos with actual changes.

## Platform

- Windows: PowerShell scripts are available.
- macOS/Linux: prefer the Python scripts with `python3`.
- PowerShell scripts can also run on macOS/Linux when PowerShell Core (`pwsh`) is installed.
