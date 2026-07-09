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
