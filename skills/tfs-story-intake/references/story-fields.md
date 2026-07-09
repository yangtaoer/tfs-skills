# Story Field Mapping

Use this reference when converting natural language into a TFS `用户情景`.

## Minimum Story Fields

| TFS field | Source |
|---|---|
| `System.Title` | Normalized as `【标准项目名】需求标题`. |
| `System.Description` | Demand background and content. |
| `System.AreaPath` | Default `XiNanArea-New\四川省区团队`. |
| `System.IterationPath` | Match the current UTC+8 local date to the TFS iteration classification nodes. |

## Default Intake Values

Use these defaults unless the user explicitly overrides them:

| Display field | Default value |
|---|---|
| 状态 | `新建` by omission; do not send `System.State` in the create request. |
| 区域 | `XiNanArea-New\四川省区团队` |
| 所属地区部 | `西南地区部` |
| 所属省份 | `四川` |
| 是否需要产品部支持 | `否` |
| 是否需要上会讨论 | `否` |
| 负责开发部门 | `地区部` |
| 需求交付负责人 | `杨涛(四川)` |
| 所属产品线 | `调度产品线` |
| 产品名称 | Prefer the matched project catalog `productName`; if absent choose a fitting product from context; if uncertain use `临时项目交付`. |

For custom fields whose reference names are unknown, query TFS fields and match by display name:

```text
GET /{project}/_apis/wit/fields?api-version=2.0
```

If a required display field cannot be mapped to a reference name, stop and report the missing mapping instead of silently omitting it.

## Iteration Default

For new user stories, set `System.IterationPath` to the iteration containing the current local date:

1. Get current UTC time and add 8 hours.
2. Query classification nodes:

   ```text
   GET /DefaultCollection/XiNanArea-New/_apis/wit/classificationnodes/iterations?$depth=3&api-version=2.0
   ```

3. Match the node whose `startDate` / `finishDate` contains the local date.
4. Convert the classification `path` to the field value:

   ```text
   \XiNanArea-New\迭代\迭代2026-6-3 -> XiNanArea-New\迭代2026-6-3
   ```

## Acceptance Criteria

Prefer explicit, testable statements:

```text
1. 在<页面/模块>可以<操作>。
2. 当<条件>时，系统<结果>。
3. 数据保存/导出/接口返回符合<规则>。
```

If TFS has a custom acceptance criteria field, use that field. If not, include the section in `System.Description`.

## Development-Friendly Description

When the user wants the story to feed later automated development, keep the description structured and stable:

```text
背景：
<当前问题、影响角色、为什么要做>

当前行为：
<系统现在怎么表现；如果是新增能力，写“当前无此能力”>

目标行为：
<需求完成后系统应该怎么表现>

范围说明：
- 包含：<本次要做>
- 不包含：<本次不做或待后续确认>

涉及对象：
- 页面/模块：<名称或待确认>
- 接口/任务/报表/数据：<名称或待确认>
- 项目：<标准项目名>
- 仓库：<catalog 推断结果或待确认>

验收标准：
1. 当<条件>时，<角色/系统>应<可观察结果>。
2. ...

未确认事项：
- <没有则写 无>
```

Avoid prose-only descriptions. Future automation depends on stable headings.

## Readiness Examples

One-line user input:

```text
省调网络发令加个审核提醒
```

Weak story:

```text
【四川省调网络发令】审核提醒优化
需求：增加审核提醒功能。
验收：功能正常。
```

Development-ready story:

```text
【四川省调网络发令】新增发令审核待办提醒

背景：
当前发令审核依赖审核人主动进入系统查看，容易遗漏待审核发令单。

当前行为：
发令单进入待审核状态后，审核人没有明确待办提醒入口。

目标行为：
发令单进入待审核状态后，系统为审核人生成站内待办提醒，并支持跳转到对应发令单审核页面。

范围说明：
- 包含：待审核提醒生成、提醒列表展示、提醒跳转。
- 不包含：短信、钉钉等外部通知渠道，除非用户另行确认。

涉及对象：
- 页面/模块：待办提醒、发令审核页面
- 项目：四川省调网络发令
- 仓库：由项目目录解析，可能涉及 notice/direct 相关仓库

验收标准：
1. 当发令单提交并进入待审核状态时，审核人可以在待办入口看到包含单号的提醒。
2. 点击提醒后可以跳转到对应发令单审核页面。
3. 已审核、已撤回、已作废的发令单不显示待审核提醒。

未确认事项：
- 是否需要外部通知渠道。
```

## Title Examples

Good:

```text
【四川省调网络发令】新增发令审核提醒
【项目A】【项目B】同步用户权限校验规则
```

Bad:

```text
【四川省调】新增发令审核提醒
省调网络发令新增发令审核提醒
```

The bad examples use an alias or omit brackets.
