---
name: tfs-story-intake
description: Use when creating, normalizing, or updating a TFS 用户情景 from natural language, especially when the title must include bracketed standard project names such as 【四川省调网络发令】 and acceptance criteria must be written before development starts.
---

# TFS Story Intake

## Overview

Create or normalize TFS `用户情景` records from natural language. Every story must resolve its project through `tfs-project-catalog` and use the canonical title format `【标准项目名】需求标题`.

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

4. Draft the story fields:
   - `System.Title`
   - `System.Description`
   - acceptance criteria field if the TFS process exposes one
   - `System.AreaPath`
   - `System.IterationPath` matched to the current local date
   - default custom fields from `references/story-fields.md`
5. Search for possible duplicate active stories before creating a new one.
6. Show the normalized title, project(s), and fields for confirmation before creating the story.
7. Create the `用户情景` through TFS REST API only after confirmation.
8. Leave the new story in the default `新建` state. Do not set `System.State` during creation.
9. If the user explicitly asks to move it to `已评审`, PATCH the state after creation as a separate operation.
10. Return the new work item id and the resolved standard project(s).

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

## Duplicate Check

Before creation, run a WIQL query for active `用户情景` items whose title contains the normalized project bracket and key nouns from the demand. If a likely duplicate exists, show the id/title/state and ask whether to reuse or create a new story.

## Iteration Selection

Use the user's local date in UTC+8. Query TFS classification nodes and choose the iteration whose start/finish date contains the current local date. Convert classification API paths to `System.IterationPath` using the same rules as `tfs-daily-task`: remove the leading backslash and remove the middle `\迭代\` layer when present.

## Safety Rules

- Do not create a story until the standard project name is known.
- Do not create a story until the user has confirmed the normalized title and key fields.
- Do not set `System.State` during story creation; default state must remain `新建`.
- Do not close, resolve, or add work logs from this skill unless explicitly requested.
- Do not store or print `TFS_PAT`.

## References

Read `references/story-fields.md` when mapping natural-language demand into TFS fields.
