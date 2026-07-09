# Development-Ready User Story Guide

Use this guide before creating a TFS `用户情景` that should support automated development later.

## Goal

Produce a story that a future Codex thread can use to resolve repositories, prepare branches, inspect code, implement changes, and submit PRs with minimal extra clarification.

## Intake Quality Levels

| Level | Meaning | Action |
|---|---|---|
| `ready-for-development` | Project, scope, behavior, and testable acceptance criteria are clear. | Create the story. It can later flow into `tfs-requirement-workspace`. |
| `draft-needs-confirmation` | Story is useful, but at least one implementation blocker remains. | Create only after the user confirms it is a draft. Record unresolved questions. |
| `blocked` | Standard project or business goal is missing. | Do not create. Ask for the missing core information. |

## Required Information

Ask only for missing items that matter for implementation:

| Area | Required information | Why it matters |
|---|---|---|
| Project | Standard project name or alias resolvable by `tfs-project-catalog`. | Title and repository resolution depend on it. |
| Business goal | What problem is being solved and for whom. | Prevents vague implementation. |
| Current behavior | What happens today, or what is missing. | Helps locate code and tests. |
| Desired behavior | What should happen after completion. | Defines implementation target. |
| Scope | Included work and explicit non-goals. | Prevents accidental overbuild. |
| Affected surface | Page, module, API, job, report, export, workflow, or data object. | Guides code search. |
| Acceptance criteria | Observable checks with expected results. | Enables verification and PR review. |
| Constraints | Permissions, data range, compatibility, timing, integration, migration, or performance constraints. | Avoids hidden blockers. |

## Follow-Up Question Rules

- Ask focused questions, not a long interview.
- Prefer one compact batch when several missing fields are tightly related.
- Do not ask for fields already covered by defaults in `story-fields.md`.
- If the user says they do not know, record `待确认` and keep the story as `draft-needs-confirmation`.
- If a project is unknown to the catalog, ask for standard project name plus repository/base branch information or mark repository context as follow-up.

## Better Prompting Pattern

When the user provides a vague demand:

```text
用户: 省调网络发令加个审核提醒
Codex should ask:
我可以先整理成用户情景。为了后续能自动开发，还缺三点：
1. 提醒触发时机：提交后、审核超时、还是状态变化时？
2. 提醒接收人：审核人、发令人、还是角色组？
3. 验收方式：页面待办、消息中心、短信/钉钉，还是只需要系统内提醒？
```

Then draft:

```text
标题: 【四川省调网络发令】新增发令审核提醒
背景: 当前发令审核缺少及时提醒，审核人需要主动进入系统查看待办。
需求内容: 当发令单进入待审核状态时，系统向审核人生成站内待办提醒，并支持从提醒跳转到发令审核页面。
验收标准:
1. 当发令单提交并进入待审核状态时，审核人可以在待办/消息入口看到提醒。
2. 点击提醒后可以跳转到对应发令单审核页面。
3. 已审核或已撤回的发令单不再显示待审核提醒。
未确认事项:
- 提醒是否需要短信/钉钉等外部渠道。
```

## Acceptance Criteria Rules

Good acceptance criteria are specific and observable:

- "当发令单进入待审核状态时，审核人能在待办入口看到一条包含单号和发令人信息的提醒。"
- "点击提醒后跳转到对应发令单详情，且页面处于可审核状态。"
- "已审核、已撤回、已作废的发令单不产生待审核提醒。"

Weak criteria must be rewritten:

- "功能正常"
- "页面好用"
- "提醒及时"
- "数据正确"

Use this rewrite pattern:

```text
当<前置条件>，执行<操作/事件>，系统应<可观察结果>。
```

## Repository Context

After resolving the project:

1. List likely repositories from `tfs-project-catalog`.
2. If the demand points to a subset, mark likely modules, such as frontend/backend/interface.
3. If the catalog has no repo data, record:

   ```text
   仓库信息: 待补充，创建后需通过 project catalog update 补齐。
   ```

Do not invent repository names.

## Description Template

Use this shape in `System.Description` or the equivalent rich-text field:

```text
背景：
<当前问题、使用人、影响>

需求内容：
<需要新增/修改的行为，包含主要页面/接口/流程>

范围说明：
- 包含：<本次明确要做的内容>
- 不包含：<明确不做的内容或待二期事项>

涉及项目与仓库：
- 项目：<标准项目名>
- 可能涉及仓库/模块：<来自 catalog 或待确认>

验收标准：
1. 当<条件>时，<角色>可以<看到/操作/得到结果>。
2. ...

未确认事项：
- <没有则写 无>
```

## Readiness Checklist

Before marking `ready-for-development`, check:

- [ ] Title uses only catalog standard names inside `【】`.
- [ ] Description explains current behavior and desired behavior.
- [ ] Acceptance criteria have concrete conditions and expected results.
- [ ] Affected module/page/interface/data object is named or intentionally marked unknown.
- [ ] Repository/project context is sufficient for `tfs-requirement-workspace`.
- [ ] Defaults from `story-fields.md` are applied.
- [ ] Unresolved questions are listed instead of hidden.
