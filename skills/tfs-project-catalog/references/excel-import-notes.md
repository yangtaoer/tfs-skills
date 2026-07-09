# Excel Import Notes

When the user provides an Excel project list, convert it into the JSON catalog shape from `catalog-schema.md`.

## Recommended Columns

| Column | Meaning |
|---|---|
| `标准项目名` | Required. Canonical project name used in `【】`. |
| `别名` | Optional. Multiple aliases separated by comma, semicolon, Chinese comma, or newline. |
| `关键词` | Optional matching hints. |
| `区域路径` | Optional TFS `System.AreaPath`. |
| `代码所在区域` | Optional TFS Git project/area. Used for remote inference when `远程地址` is absent. |
| `默认基础分支` | Optional project-level target branch. |
| `仓库名` | Required for each repo row. |
| `远程地址` | Optional TFS Git remote URL. If missing, infer it from `代码所在区域` and `仓库名`. |
| `基础分支` | Optional repo-level target branch. |
| `仓库角色` | Optional: frontend/backend/service/startup/shared. |
| `仓库关键词` | Optional repo-specific hints. |
| `产品名称` | Optional product field default for story intake. |

## Import Behavior

- Multiple rows may share the same `标准项目名`; merge them into one project with multiple repos.
- Split aliases and keywords on `,` `，` `;` `；` and newlines.
- Split multi-line repository cells into one repo entry per line.
- Trim whitespace from all cells.
- Preserve Chinese characters literally.
- If both project default branch and repo branch are empty, leave branch blank and require confirmation during workspace creation.
- Do not infer a standard project name from aliases; ask the user to correct the Excel file.
- If a branch cell contains per-repo notes, such as `dcsd-springboot-starter使用chongqing\n其余是dev`, apply the named branch to that repo and the fallback branch to the remaining repos.

## After Import

Validate the resulting JSON:

```powershell
py -3 skills\tfs-project-catalog\scripts\resolve_tfs_workspace.py --catalog .\project-catalog.json --validate
```
