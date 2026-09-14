# Commit and PR Rules

## Production Commit Scope Gate

- Only commit files required by the production application, runtime configuration, build, or deployment.
- Default-exclude documentation (`docs/`, `doc/`, `README*`, `CHANGELOG*`, `*.md`, `*.adoc`, `*.rst`) and tests/test support (`src/test/`, `test/`, `tests/`, `__tests__/`, fixtures, mocks, snapshots, coverage, `*Test.*`, `*Tests.*`, `*.test.*`, `*.spec.*`). Include these only after an explicit user instruction covering the category or exact path.
- Default-exclude local/editor/agent metadata, logs, screenshots, reports, scratch/temporary files, caches, and generated build output unless a specific file is required in the production source tree.
- SQL is never implicitly included. List each `*.sql` path and obtain explicit confirmation before staging it. Without confirmation, leave it local. If production correctness depends on it, stop before commit and request confirmation.
- A generic instruction to submit all changes does not approve documentation, tests, or SQL.
- Never use `git add .`, `git add -A`, or broad staging globs. Stage the reviewed production allowlist by exact path and inspect the complete staged diff before commit.
- Unstage prohibited or unconfirmed paths without deleting their working-tree content. Report all excluded paths after submission.
- If the allowlist is empty, do not create a commit or PR.

## Shared Code Gate

- Treat code used by multiple regions or provinces as protected shared code.
- For a regional requirement, prefer a regional/project-specific repository or extension point.
- Before staging, verify that every shared repository or shared path in the diff was explicitly approved by the user after its cross-region impact was explained.
- If approval is missing or impact is uncertain, do not commit, push, create a PR, or enable auto-complete; stop and ask the user.
- Do not treat a general instruction to finish or submit the work item as shared-code approval.

## Trigger Phrases

Use this skill when the user says any of the following:

- "提交到 TFS"
- "提交到远程仓库"
- "创建合并请求"
- "创建 PR"
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

If the user does not provide a work item id, first check the configured saved TFS query (`TFS_USER_STORY_QUERY_URL`) and choose the related user story before asking the user.

```text
http://dev.tellhowsoft.com/DefaultCollection/XiNanArea-New/_queries/query/2fd5f73e-f5bc-4423-b289-7bcb1fb58977
```

The URL above is an example. Some saved queries are `oneHop` WorkItemLinks queries. When using the REST API, do not rely only on `workItems`; parse `workItemRelations` and fetch the unique `source.id` and `target.id` work items. Prefer matching open or reviewed `用户情景` items by title, area, and the current code change. If none matches, ask the user for the work item id.

## Type Selection

- `feat`: new feature, feature enhancement, user-facing behavior improvement.
- `fix`: bug fix or production defect correction.
- `perf`: performance improvement without behavior change.
- `refactor`: internal restructuring without behavior change.
- `docs`: documentation explicitly approved for submission.
- `test`: test-only changes explicitly approved for submission.
- `chore`: maintenance, configuration, dependency, or tooling work.
- `build`: build system changes.
- `ci`: CI/CD pipeline changes.

## Branching

- Confirm the target/base branch before branch creation. Use `TFS_TARGET_BRANCH` if set; otherwise use `dev` only as a fallback.
- Start from `origin/<targetBranch>`.
- Do not commit on the target/base branch.
- Default branch: `feature/<workItemId>-<tfsAlias>`, for example `feature/1551572-yangtao`.
- Get `<tfsAlias>` from the user or `TFS_USER_ALIAS`.
- If a branch already exists and belongs to another unfinished task, create `feature/<workItemId>-<tfsAlias>-YYYYMMDD-HHmm`.
- Push with upstream: `git push -u origin <branch>`.

## PR

- Source branch: the feature branch.
- Target branch: confirmed target branch.
- Title: exact commit subject.
- Description: include source branch, target branch, and a concise change summary.
- Auto-complete: set to enabled after creating or reusing the PR.
- Source branch deletion: enable through PR completion options.
- Verify work item linking from the PR side. If no work item is listed, explicitly add a `Pull Request` ArtifactLink to the work item.

## Post-PR Main Workspace Handoff

- Perform the handoff immediately after successful PR creation; PR merge is not required.
- Preserve the user's primary IDE workspace path for every repository when creating temporary worktrees.
- Before removing a temporary worktree, verify both it and the main repository are clean and verify its HEAD equals `origin/<sourceBranch>`.
- Remove worktrees with `git worktree remove`, never by deleting their directories directly; follow with `git worktree prune`.
- Switch each clean main repository to the PR source branch and verify its upstream and status so the user can test the complete multi-repository change in the IDE.
- If any repository is dirty, has unpushed commits, is locked, or cannot be mapped unambiguously to the main workspace, leave it unchanged and report the blocker.
- Do not delete local or remote feature branches during handoff. Remote deletion remains a PR completion option.
