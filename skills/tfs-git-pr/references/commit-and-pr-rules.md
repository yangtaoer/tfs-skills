# Commit and PR Rules

## Trigger Phrases

Use this skill when the user says any of the following:

- "提交到 TFS"
- "提交到远程仓库"
- "创建合并请求"
- "创建 PR 到 dev"
- "dev.tellhowsoft.com"
- "代码开发完成，帮我提交"

## Required Commit Subject

Format:

```text
type(#workItemId):area-summary
```

Examples:

```text
feat(#1551572):成都-配网拟票自动联想功能优化：命令模式交互升级、动词剔除匹配、性能优化(防抖+索引+DocumentFragment)
fix(#1590470):巴中-绩效考核统计修复人员维度汇总异常
perf(#1551572):成都-配网拟票自动联想优化索引构建性能
```

Rules:

- Keep the work item id immediately after the type: `feat(#1551572):...`
- Use the same string as the PR title.
- Prefer one commit per user-facing change unless the user asks for multiple commits.
- Use the business region or module before the hyphen, such as `成都-`, `巴中-`, `四川-`, or the specific module name.
- Make the summary concrete enough for reviewers to understand the change without opening the diff.

## Work Item Discovery

If the user does not provide a work item id, first check this saved TFS query and choose the related user story before asking the user:

```text
http://dev.tellhowsoft.com/DefaultCollection/XiNanArea-New/_queries/query/2fd5f73e-f5bc-4423-b289-7bcb1fb58977
```

This query is a `oneHop` WorkItemLinks query. When using the REST API, do not rely only on `workItems`; parse `workItemRelations` and fetch the unique `source.id` and `target.id` work items. Prefer matching open or reviewed `用户情景` items by title, area, and the current code change. If none matches, ask the user for the work item id.

## Type Selection

- `feat`: new feature, feature enhancement, user-facing behavior improvement.
- `fix`: bug fix or production defect correction.
- `perf`: performance improvement without behavior change.
- `refactor`: internal restructuring without behavior change.
- `docs`: documentation only.
- `test`: test-only changes.
- `chore`: maintenance, configuration, dependency, or tooling work.
- `build`: build system changes.
- `ci`: CI/CD pipeline changes.

## Branching

- Start from `origin/dev`.
- Do not commit on `dev`.
- Default branch: `feature/<workItemId>-<tfsAlias>`, for example `feature/1551572-yangtao`.
- Get `<tfsAlias>` from the user or `TFS_USER_ALIAS`.
- If a branch already exists and belongs to another unfinished task, create `feature/<workItemId>-<tfsAlias>-YYYYMMDD-HHmm`.
- Push with upstream: `git push -u origin <branch>`.

## PR

- Source branch: the feature branch.
- Target branch: `dev`.
- Title: exact commit subject.
- Description: include source branch, target branch, and a concise change summary.
- Auto-complete: set to enabled after creating or reusing the PR.
- Source branch deletion: enable through PR completion options.
- Verify work item linking from the PR side. If no work item is listed, explicitly add a `Pull Request` ArtifactLink to the work item.
