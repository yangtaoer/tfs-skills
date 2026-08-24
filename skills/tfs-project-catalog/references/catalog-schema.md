# Project Catalog Schema

Use JSON as the canonical tracked format. JSON is readable by Python standard library and easy to generate from Excel later.

## Shape

```json
{
  "version": 1,
  "projects": [
    {
      "standardName": "自贡检修计划智能编排系统",
      "aliases": ["自贡检修智能编排", "自贡检修计划智能编排"],
      "keywords": ["自贡", "检修计划", "智能编排"],
      "areaPath": "XiNanArea-New\\四川省区团队",
      "defaultTargetBranch": "dev-sczg",
      "pipelines": [
        {
          "purpose": "dependency",
          "stage": 1,
          "definitionId": 9479,
          "name": "th-oms-dp-repairplan-dev-sczg-自贡",
          "definitionUrl": "http://dev.tellhowsoft.com/DefaultCollection/DCOMS/_build?definitionId=9479",
          "folderPath": "\\RELEASE\\四川\\检修计划智能编排系统",
          "tfsProject": "DCOMS",
          "repository": "th-oms-dp-repairplan",
          "sourceBranch": "refs/heads/dev-sczg"
        },
        {
          "purpose": "delivery",
          "stage": 2,
          "deliverable": "backend",
          "definitionId": 9180,
          "name": "th-oms-repairplan-layout-starter-四川自贡后端应用-测试",
          "definitionUrl": "http://dev.tellhowsoft.com/DefaultCollection/DCOMS/_build?definitionId=9180",
          "folderPath": "\\RELEASE\\四川\\检修计划智能编排系统",
          "tfsProject": "DCOMS",
          "repository": "th-oms-repairplan-layout-starter",
          "sourceBranch": "refs/heads/dev-sczg",
          "buildProfile": "sc-zg",
          "artifactName": "drop"
        }
      ],
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
| `projects[].pipelines[].purpose` | yes | `dependency` prepares a later stage; `delivery` must produce the requested package. |
| `projects[].pipelines[].stage` | for workflows | Positive execution stage. Pipelines in one stage are queued together; the next stage waits for all of them to succeed. Omit for a legacy single-pipeline delivery. |
| `projects[].pipelines[].deliverable` | no | Delivery label such as `backend` or `frontend`, used to identify final artifact links. |
| `projects[].pipelines[].definitionId` | yes | Positive TFS Build definition ID. |
| `projects[].pipelines[].name` | yes | Current TFS Build definition name. |
| `projects[].pipelines[].definitionUrl` | yes | Human-facing TFS pipeline URL containing `definitionId`. |
| `projects[].pipelines[].folderPath` | no | TFS Build folder path used for discovery and auditing. |
| `projects[].pipelines[].tfsProject` | yes | TFS team project that owns the definition, such as `DCS`. |
| `projects[].pipelines[].repository` | no | Primary repository used by the definition. |
| `projects[].pipelines[].sourceBranch` | yes | Full Build API branch ref, such as `refs/heads/dev`. |
| `projects[].pipelines[].buildProfile` | no | Build profile or variant used by the pipeline. |
| `projects[].pipelines[].artifactName` | no | Expected published artifact, such as `drop`. |
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
- Pipeline `sourceBranch` values must use full refs such as `refs/heads/dev`.
- Pipeline definition IDs must be unique within a TFS project.
- Pipeline definition URLs must contain the matching `definitionId` query value.
- If any pipeline in a project has `stage`, every runnable pipeline in that project must have a positive stage; stages must be contiguous from `1`.
- A staged workflow must contain at least one pipeline with `purpose: delivery`.
- Pipelines in the same stage may run concurrently. Every pipeline in an earlier stage must succeed before the next stage is queued.
- Do not include `TFS_PAT`, passwords, or personal tokens.

## Remote Inference

When Excel only provides a repository name and a code area/project, infer the remote as:

```text
http://dev.tellhowsoft.com/DefaultCollection/<codeArea>/_git/<repoName>
```

If Excel provides a full remote URL later, use the explicit URL instead of inference.
