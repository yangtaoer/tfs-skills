# Requirement Workspace Schema

Workspace files are local execution records. They should normally live outside business repositories:

```text
%USERPROFILE%\.codex\tfs-workspaces\<workItemId>\workspace.json
```

## Shape

```json
{
  "version": 1,
  "createdAt": "2026-07-09T10:00:00+08:00",
  "workItemId": 1551572,
  "title": "【四川省调网络发令】新增发令审核提醒",
  "projects": ["四川省调网络发令"],
  "featureBranch": "feature/1551572-yangtao",
  "repos": [
    {
      "project": "四川省调网络发令",
      "name": "repo-name",
      "role": "backend",
      "module": "主程序",
      "codeArea": "XiNanArea-New",
      "description": "主程序所在仓库",
      "remote": "http://dev.tellhowsoft.com/DefaultCollection/XiNanArea-New/_git/repo-name",
      "targetBranch": "dev",
      "localPath": "C:\\work\\repo-name",
      "matchStatus": "found",
      "matchReason": "remote"
    }
  ]
}
```

## Match Status

| Status | Meaning |
|---|---|
| `found` | Local repo path exists and remote/name matches. |
| `missing` | Repo is in catalog but no local path was found. |
| `remote-mismatch` | A local path was found, but origin differs from catalog. |
| `needs-confirmation` | Match is plausible but ambiguous. |

The same remote may appear more than once when different modules use different target branches. Treat `remote + targetBranch + module` as the unique workspace target.

## Git Branch Preparation

Branch creation is intentionally not part of the workspace JSON writer. After confirming the workspace:

```powershell
git -C <localPath> fetch origin <targetBranch>
git -C <localPath> switch -c feature/<workItemId>-<tfsAlias> origin/<targetBranch>
```

Use `tfs-dev-workflow` or its bundled scripts for this step.
