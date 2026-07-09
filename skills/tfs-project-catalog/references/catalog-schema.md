# Project Catalog Schema

Use JSON as the canonical tracked format. JSON is readable by Python standard library and easy to generate from Excel later.

## Shape

```json
{
  "version": 1,
  "projects": [
    {
      "standardName": "四川省调网络发令",
      "aliases": ["省调网络发令", "四川省调", "四川省调网络发令系统"],
      "keywords": ["省调", "网络发令", "调度"],
      "areaPath": "XiNanArea-New\\四川省区团队",
      "defaultTargetBranch": "dev",
      "repos": [
        {
          "name": "repo-name",
          "remote": "http://dev.tellhowsoft.com/DefaultCollection/XiNanArea-New/_git/repo-name",
          "targetBranch": "dev",
          "role": "backend",
          "module": "主程序",
          "codeArea": "XiNanArea-New",
          "description": "主程序所在仓库",
          "keywords": ["api", "service"]
        }
      ]
    }
  ]
}
```

## Fields

| Field | Required | Notes |
|---|---:|---|
| `version` | yes | Start with `1`. |
| `projects[].standardName` | yes | Only value allowed inside `【】`. Must be unique. |
| `projects[].aliases` | no | Input-only names. Never write these into TFS titles. |
| `projects[].keywords` | no | Extra matching hints for descriptions and titles. |
| `projects[].areaPath` | no | Default TFS area path for new stories. |
| `projects[].defaultTargetBranch` | no | Fallback for repos without explicit branch. |
| `projects[].repos[].name` | yes | Human/repo name. Prefer actual TFS Git repo name. |
| `projects[].repos[].remote` | yes | TFS Git remote URL. Used for local repo matching. |
| `projects[].repos[].targetBranch` | no | Base branch for this repo. Defaults to project branch. |
| `projects[].repos[].role` | no | Examples: `frontend`, `backend`, `service`, `startup`, `shared`. |
| `projects[].repos[].module` | no | Business/function module from the source catalog, such as `主程序` or `三区接口程序`. |
| `projects[].repos[].codeArea` | no | TFS Git project/area used to infer remote URL when Excel gives only a repo name. |
| `projects[].repos[].description` | no | Human explanation of what this repo entry covers. |
| `projects[].repos[].keywords` | no | Repo-specific matching hints. |

## Validation Rules

- `standardName` values must be unique.
- Aliases should not equal another project's `standardName`.
- Repository remotes may repeat when the same repo has different target branches for different modules. Treat `remote + targetBranch + module` as the unique development target.
- Branch names must not include `origin/`; store `dev`, not `origin/dev`.
- Do not include `TFS_PAT`, passwords, or personal tokens.

## Remote Inference

When Excel only provides a repository name and a code area/project, infer the remote as:

```text
http://dev.tellhowsoft.com/DefaultCollection/<codeArea>/_git/<repoName>
```

If Excel provides a full remote URL later, use the explicit URL instead of inference.
