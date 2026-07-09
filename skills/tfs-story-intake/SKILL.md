---
name: tfs-story-intake
description: Use when creating, normalizing, refining, or quality-gating a TFS 用户情景 from natural language, especially when the story must be development-ready for automated code work, include bracketed standard project names such as 【四川省调网络发令】, and contain clear acceptance criteria.
---

# TFS Story Intake

## Overview

Create or normalize TFS `用户情景` records from natural language. Every story must resolve its project through `tfs-project-catalog`, use the canonical title format `【标准项目名】需求标题`, and pass a development-readiness check before creation unless the user explicitly chooses to create a draft.

## Required Sub-Skills

- Use `tfs-project-catalog` before creating or renaming a story.
- Use `tfs-rest-api` for actual TFS work item API calls.

## Intake Workflow

1. Extract the user's raw demand, affected system/project terms, expected behavior, and any acceptance criteria.
2. Resolve project terms through `tfs-project-catalog`.
3. Build a normalized title:

   ```text
   【标准项目名】简洁需求标题
   ```

   For multiple projects, use one bracket per project:

   ```text
   【项目A】【项目B】简洁需求标题
   ```

4. Run the development-ready intake guide:
   - Read `references/development-ready-story.md`.
   - Ask focused follow-up questions only for missing information that blocks implementation.
   - Capture unknowns explicitly instead of hiding them in vague wording.
5. Draft the story fields:
   - `System.Title`
   - `System.Description`
   - acceptance criteria field if the TFS process exposes one
   - `System.AreaPath`
   - `System.IterationPath` matched to the current local date
   - default custom fields from `references/story-fields.md`
6. Assign a readiness level:
   - `ready-for-development`: enough information for repository resolution and implementation planning.
   - `draft-needs-confirmation`: useful story draft, but one or more implementation blockers remain.
   - `blocked`: missing standard project or core business goal.
7. Search for possible duplicate active stories before creating a new one.
8. Show the normalized title, project(s), readiness level, unresolved questions, and fields for confirmation before creating the story.
9. Create the `用户情景` through TFS REST API only after confirmation.
10. Leave the new story in the default `新建` state. Do not set `System.State` during creation.
11. If the user explicitly asks to move it to `已评审`, PATCH the state after creation as a separate operation only when readiness is `ready-for-development`.
12. Return the new work item id, resolved standard project(s), readiness level, and recommended next step.

## Development-Ready Gate

Before creating a non-draft story, verify these are known:

- Standard project name for each affected system.
- Business goal and current pain point.
- User-facing behavior change.
- Scope boundaries: included and not included.
- Affected module/page/interface/job/data object when known.
- Repository hints from the catalog, or explicit note that repo details must be completed later.
- Testable acceptance criteria.
- Any data migration, permission, integration, timing, or compatibility constraints.

If only one or two fields are missing, ask concise follow-up questions. If the user does not know, record the unknown and create only a draft when the user confirms.

## Title Rules

- Always use full-width Chinese brackets `【】`.
- Inside brackets, use only catalog `standardName` values.
- Do not use aliases inside brackets.
- Keep the text after brackets action-oriented and short.
- If the title lacks a project bracket, add one before creation.
- If the title contains an unknown bracket value, stop and resolve it instead of preserving it.

## Description Shape

Use concise sections unless the user's team has a stricter TFS template:

```text
背景：
<为什么需要这个需求>

需求内容：
<要实现什么能力>

验收标准：
1. <可验证结果>
2. <可验证结果>
```

If the user only gives a one-line request, infer a draft but mark uncertain details for confirmation.

## Confirmation Format

Before creation, present a compact confirmation:

```text
标题: 【标准项目名】需求标题
就绪度: ready-for-development / draft-needs-confirmation / blocked
项目: ...
涉及仓库: ... / 待确认
需求内容: ...
验收标准:
1. ...
未确认事项:
- ...
默认字段: 区域、迭代、地区部、省份、产品线、负责人...
```

Do not create the story if the user has not confirmed this summary.

## Duplicate Check

Before creation, run a WIQL query for active `用户情景` items whose title contains the normalized project bracket and key nouns from the demand. If a likely duplicate exists, show the id/title/state and ask whether to reuse or create a new story.

## Iteration Selection

Use the user's local date in UTC+8. Query TFS classification nodes and choose the iteration whose start/finish date contains the current local date. Convert classification API paths to `System.IterationPath` using the same rules as `tfs-daily-task`: remove the leading backslash and remove the middle `\迭代\` layer when present.

## Safety Rules

- Do not create a story until the standard project name is known.
- Do not create a story until the user has confirmed the normalized title and key fields.
- Do not label a story `ready-for-development` unless acceptance criteria are testable and repository/project context is sufficient for `tfs-requirement-workspace`.
- Do not set `System.State` during story creation; default state must remain `新建`.
- Do not close, resolve, or add work logs from this skill unless explicitly requested.
- Do not store or print `TFS_PAT`.

## References

- Read `references/development-ready-story.md` when guiding the user from vague demand to a development-ready story.
- Read `references/story-fields.md` when mapping natural-language demand into TFS fields.
