---
name: tfs-daily-task
description: TFS每日任务管理 - 创建子任务、关闭用户情景等操作
---

# TFS 每日任务管理

## 用户信息
- **用户**: 杨涛(四川) `TELLHOW\yangtao`
- **项目**: XiNanArea-New
- **区域**: XiNanArea-New\四川省区团队
- **角色**: 需求交付负责人

## PAT Token
- 优先从环境变量 `TFS_PAT` 读取。
- 如果未配置 `TFS_PAT`，向用户索要或让用户在当前终端会话中设置。
- 不要打印、持久化或提交 PAT。

## TFS API 配置
- **地址**: http://dev.tellhowsoft.com/DefaultCollection/
- **Content-Type**: `application/json-patch+json`

## 关键字段
| 用途 | 字段名 | referenceName |
|------|--------|---------------|
| 需求交付负责人 | Custom.3d3cdcf5... | Custom.3d3cdcf5-de35-4448-afbb-bdfd963d2564 |
| 实际交付版本 | Custom.adf4ae15... | Custom.adf4ae15-611e-4565-9f47-a9f24561efa9 |
| 初始估计 | 初始估计 | Microsoft.VSTS.Scheduling.OriginalEstimate |
| 剩余工作 | 剩余工作 | Microsoft.VSTS.Scheduling.RemainingWork |
| 完成工作 | 完成工作 | Microsoft.VSTS.Scheduling.CompletedWork |
| 活动 | 活动 | Microsoft.VSTS.Common.Activity |

## 用户情景状态流转
```
新建 -> 已评审 -> 已解决 -> 已关闭
```

关闭用户情景时需要填写3个必填评价字段（质量评价、服务态度、用户体验），都是picklist字段，可选值示例：
- 质量评价: `5-功能完备可正常运行，满足使用`
- 服务态度: `5-服务亲切热情且耐心好`
- 用户体验: `5-界面美观、布局合理、呈现清晰、操作极简`

```json
[
  {"op": "replace", "path": "/fields/System.State", "value": "已关闭"},
  {"op": "add", "path": "/fields/Custom.a6fb40d4-5f26-4167-b47c-b056ab423f49", "value": "5-功能完备可正常运行，满足使用"},
  {"op": "add", "path": "/fields/Custom.2286db83-008a-4bbc-bdd2-98a779a142d6", "value": "5-服务亲切热情且耐心好"},
  {"op": "add", "path": "/fields/Custom.b7a089cf-99c0-4d5c-ab03-8bd3f068194f", "value": "5-界面美观、布局合理、呈现清晰、操作极简"}
]
```

## 完整工作流程

### 1. 接需求（一次性）
用户情景由需求提出人（如孙杰）创建，指派给自己。需要：
- 把 **需求交付负责人** 改为 `杨涛(四川) <TELLHOW\yangtao>`
- 把用户情景状态从 **新建** 改为 **已评审**

API:
```
PATCH /DefaultCollection/_apis/wit/workitems/{id}?api-version=2.0
[
  {"op": "replace", "path": "/fields/Custom.3d3cdcf5-de35-4448-afbb-bdfd963d2564", "value": "杨涛(四川) <TELLHOW\\yangtao>"},
  {"op": "replace", "path": "/fields/System.State", "value": "已评审"}
]
```

### 2. 每日创建任务（每天）
在已评审的用户情景下创建子任务：

必填字段：
- Title: 任务标题
- Description: 工作内容描述
- RemainingWork: 剩余工时（关闭时必须为空）
- OriginalEstimate: 初始估计工时
- CompletedWork: 完成工时
- Activity: "开发"（默认）
- IterationPath: 由任务开始日期确定的迭代（格式：`XiNanArea-New\迭代2026-5-1`，注意迭代名可能没有空格）
- AreaPath: `XiNanArea-New\四川省区团队`
- 关联父级: System.LinkTypes.Hierarchy-Reverse -> 用户情景ID

创建后直接关闭：
- State -> "已关闭"
- 关闭时 RemainingWork 必须不传（不能为0）

**重要**: JSON body 写文件用 `write_file` 确保反斜杠正确，再用 curl -d @file 发送。

### 2b. 创建并关闭任务（一步到位，推荐流程）

每个任务固定8小时，建好直接关闭。两步操作：

**Step 1 — 创建任务**（注意URL编码 `$%E4%BB%BB%E5%8A%A1`）：
```bash
# 写JSON body到文件
py -3 -c "
import json
patch_data = [
    {'op': 'add', 'path': '/fields/System.Title', 'value': '任务标题'},
    {'op': 'add', 'path': '/fields/System.AssignedTo', 'value': 'TELLHOW\x5cyangtao'},
    {'op': 'add', 'path': '/fields/System.AreaPath', 'value': 'XiNanArea-New\x5c四川省区团队'},
    {'op': 'add', 'path': '/fields/System.IterationPath', 'value': 'XiNanArea-New\x5c迭代2026-5-1'},
    {'op': 'add', 'path': '/fields/Microsoft.VSTS.Scheduling.OriginalEstimate', 'value': 8},
    {'op': 'add', 'path': '/fields/Microsoft.VSTS.Scheduling.RemainingWork', 'value': 8},
    {'op': 'add', 'path': '/fields/Microsoft.VSTS.Scheduling.StartDate', 'value': '{日期}T00:30:00Z'},
    {'op': 'add', 'path': '/fields/Microsoft.VSTS.Scheduling.FinishDate', 'value': '{日期}T09:30:00Z'},
    {'op': 'add', 'path': '/fields/Microsoft.VSTS.Common.Activity', 'value': '开发'},
    {'op': 'add', 'path': '/fields/System.Description', 'value': '<div>1、今日完成开发情况（具体内容）<br>2、BUG修复情况（无）<br>3、需求沟通情况（无）<br>4、其他（无）</div>'},
    {'op': 'add', 'path': '/relations/-', 'value': {
        'rel': 'System.LinkTypes.Hierarchy-Reverse',
        'url': 'http://dev.tellhowsoft.com/DefaultCollection/_apis/wit/workItems/父级ID'
    }}
]
with open('tfs_create.json', 'w', encoding='utf-8') as f:
    json.dump(patch_data, f, ensure_ascii=False)
"

# 用curl发送（必须用curl，Python urllib不支持中文URL路径）
curl -u ":PAT_TOKEN" -X POST -H "Content-Type: application/json-patch+json" \
  -d @tfs_create.json \
  "http://dev.tellhowsoft.com/DefaultCollection/XiNanArea-New/_apis/wit/workitems/\$%E4%BB%BB%E5%8A%A1?api-version=2.0"
```

**Step 2 — 立即关闭任务**：
```bash
# 写关闭JSON
py -3 -c "
import json
patch_data = [
    {'op': 'replace', 'path': '/fields/System.State', 'value': '已关闭'},
    {'op': 'replace', 'path': '/fields/Microsoft.VSTS.Scheduling.OriginalEstimate', 'value': 8},
    {'op': 'replace', 'path': '/fields/Microsoft.VSTS.Scheduling.CompletedWork', 'value': 8},
    {'op': 'replace', 'path': '/fields/Microsoft.VSTS.Scheduling.TargetDate', 'value': '{日期}T09:30:00Z'}
]
with open('tfs_close.json', 'w', encoding='utf-8') as f:
    json.dump(patch_data, f, ensure_ascii=False)
"

curl -u ":PAT_TOKEN" -X PATCH -H "Content-Type: application/json-patch+json" \
  -d @tfs_close.json \
  "http://dev.tellhowsoft.com/DefaultCollection/_apis/wit/workitems/任务ID?api-version=2.0"
```

**注意**: 关闭时不要设置RemainingWork字段（留空即可），设置CompletedWork=8。

### 3. 完成用户情景（需求做完时）
- State -> "已解决"
- 实际交付版本 -> "1.0"

API:
```
PATCH /DefaultCollection/_apis/wit/workitems/{id}?api-version=2.0
[
  {"op": "replace", "path": "/fields/System.State", "value": "已解决"},
  {"op": "replace", "path": "/fields/Custom.adf4ae15-611e-4565-9f47-a9f24561efa9", "value": "1.0"}
]
```

## 任务描述模板（必用）

每个任务的 Description 必须使用以下标准模板格式：

```
1、今日完成开发情况（具体内容）
2、BUG修复情况（无）
3、需求沟通情况（无）
4、其他（无）
```

第1条括号内填实际工作内容，2/3/4一般填"无"。

**重要：描述必须适当扩充，不能只写一句话**。用户提供的简要描述需要扩展为饱满、专业的工作描述，具体要求：
- 将用户的简短描述拆解为多个具体工作步骤
- 补充技术细节（如涉及的技术栈、工具、方法等）
- 增加工作目的和意义的说明
- 适当补充沟通协调、问题排查等关联工作
- 如果第1条内容较丰富，可根据实际情况适当填充第3条（需求沟通情况）
- 目标：让任务描述看起来专业、详实，体现工作量和专业性

扩充示例：
- 用户输入："拉取代码及协调缺包" → 扩充为："从远程仓库拉取最新代码到本地工作空间，检查代码分支及版本一致性；在编译构建过程中发现仓库中存在多个依赖包缺失的问题，逐一排查缺失的包及版本依赖关系，及时与团队成员及仓库管理员沟通协调，推动缺包问题尽快解决，确保项目代码能够正常编译运行"
- 用户输入："搭建本地环境" → 扩充为："配置前端及后端运行环境，安装必要的开发工具及插件，调整本地配置文件以适配项目要求，确保本地环境能够顺利编译和启动项目"

HTML示例：
```html
<div>1、今日完成开发情况（从远程仓库拉取最新代码到本地工作空间，检查代码分支及版本一致性；在编译构建过程中发现仓库中存在多个依赖包缺失的问题，逐一排查缺失的包及版本依赖关系，及时与团队成员及仓库管理员沟通协调，推动缺包问题尽快解决）<br>2、BUG修复情况（无）<br>3、需求沟通情况（与仓库管理员确认缺包补齐进度）<br>4、其他（无）</div>
```

## 每日用户输入格式

用户只需提供简单信息：
```
今天的工作：
1. 做了什么
2. 做了什么
工时：8
父级：1523040（如果不变可不写）
```

甚至一句话也行：
```
今天梳理了APP的登录接口逻辑，8小时
```

## 自动处理的固定项
- 区域: XiNanArea-New\四川省区团队
- 迭代: 必须按任务开始日期所属迭代确定（需要查API确认名称，不能直接沿用父级用户情景的迭代）
- 活动: 开发
- 状态: 创建后直接关闭（必须分两步：先创建再PATCH关闭）
- 初始估计 = 完成工作 = 8（每个任务固定8小时）
- 开始日期/目标日期：见下方时区处理规则

## 时区处理规则（重要）

用户时区 **UTC+8**。TFS存储UTC时间。每次建任务必须先获取当前UTC时间，加8小时算出用户本地日期。

- 未指定补录日期时，先执行 `py -3 -c "from datetime import datetime, timezone, timedelta; now=datetime.now(timezone.utc)+timedelta(hours=8); print(now.strftime('%Y-%m-%d'))"` 获取本地日期
- 指定补录日期时，以用户指定的任务日期作为本地日期；不要用当前日期覆盖补录日期
- **StartDate** = `{本地日期}T00:30:00Z`（用户看到 08:30）
- **TargetDate/FinishDate** = `{本地日期}T09:30:00Z`（用户看到 17:30）
- 不要硬编码日期，每次都动态获取

## 迭代名称注意事项

迭代名称格式不统一，有的是 `迭代 2026-5-1`（有空格），有的是 `迭代2026-5-1`（无空格）。
**必须通过API按任务开始日期查询确认**：GET /DefaultCollection/XiNanArea-New/_apis/wit/classificationnodes/iterations?$depth=3&api-version=2.0

### 迭代必须按 StartDate 确定

创建任务前必须先确定任务的本地日期，再用该日期匹配迭代节点的 `startDate` / `finishDate`：

1. 今日任务：用 UTC 当前时间 + 8 小时得到本地日期。
2. 补录任务：用用户指定的补录日期。
3. 批量补录：每个日期分别匹配自己的迭代，不能整批共用一个迭代。
4. 父级用户情景的 `System.IterationPath` 只能作为兜底参考或排错线索，不能作为子任务迭代来源。

### 分类API路径 ≠ IterationPath字段值（重要）

分类API返回的 `path` 和实际 `System.IterationPath` 字段**格式不同**：

| 来源 | 示例 |
|------|------|
| 分类API path | `\XiNanArea-New\迭代\迭代2026-6-3` |
| IterationPath 字段 | `XiNanArea-New\迭代2026-6-3` |

差异：
1. API path 有**前导反斜杠** `\`，IterationPath 没有
2. API path 包含中间层 `迭代` 节点（`\迭代\迭代2026-6-3`），IterationPath 没有（`\迭代2026-6-3`）

**可靠转换方法**：分类 API 匹配到日期所在节点后，把 path 转成字段值：

1. 去掉前导 `\`
2. 去掉中间层 `\迭代\`
3. 保留真实叶子节点名称，包括其中可能存在的空格

示例：

```text
\XiNanArea-New\迭代\迭代2026-6-3 -> XiNanArea-New\迭代2026-6-3
\XiNanArea-New\迭代\迭代 2026-5-1 -> XiNanArea-New\迭代 2026-5-1
```

## 父级用户情景自动查找规则（重要）

当用户没有指定任务的父级用户情景时，**必须**按以下顺序查找：

1. 查询用户前一天（或最近一个有任务的工日）的任务，获取其关联的父级用户情景ID
2. 查询方法：`GET /_apis/wit/workItems/{前一天任务ID}?api-version=2.0`，从 `relations` 中找 `System.LinkTypes.Hierarchy-Reverse` 对应的URL提取父级ID
3. 如果前一天也没有任务，再往前找，直到找到为止
4. **如果完全找不到任何历史任务的父级，则不要新建任务，向用户报告并要求提供用户情景ID**

```python
# 查找最近任务的父级用户情景示例
# 1. 先用已知任务ID获取详情，从relations找父级
req = urllib.request.Request(
    f'http://dev.tellhowsoft.com/DefaultCollection/_apis/wit/workItems/{task_id}?api-version=2.0',
    headers={'Authorization': 'Basic ' + cred}
)
resp = urllib.request.urlopen(req)
result = json.loads(resp.read())
parent_id = None
for rel in result.get('relations', []):
    if rel.get('rel') == 'System.LinkTypes.Hierarchy-Reverse':
        parent_id = rel['url'].split('/')[-1]
```

## 批量补工日（Backfill）

当用户要求补某个月或多天任务时，**必须**先询问用户哪些天不需要补（法定节假日、请假等），然后再执行。

流程：
1. **询问排除日期**：用 clarify 工具询问用户"以下哪些日期不需要补录？（如法定假日、请假等）"，列出所有待补的工日供用户选择或补充
2. 确认日期范围，排除周末（六日）和用户指定的排除日期
3. 按每个补录日期的 StartDate 分别确定所属迭代（查API），注意迭代名空格问题
4. 用一个父级用户情景（用户指定或从邻近任务取，遵循"父级用户情景自动查找规则"）
5. 批量创建：Python写JSON文件 → subprocess调curl创建 → 记录返回的ID
6. 批量关闭：用返回的ID逐个PATCH关闭
7. 创建完成后，输出汇总表格让用户确认

示例代码见 `scripts/batch_create_tasks.py`。该脚本支持参数化调用：

```bash
py -3 scripts/batch_create_tasks.py \
  --parent 1476929 --from 2026-05-25 --to 2026-05-29 \
  --exclude 2026-05-27 --detail "巴中自巡航代码独立化" --pat YOUR_PAT
```

自动跳过周末，`--exclude` 跳过指定日期（请假/假日）。

## 查询我的需求与任务

### WIQL 查询注意事项

`@Me` 和显式 `AssignedTo` 各有适用场景，建议两种都准备好，一种失败就换另一种：

```sql
-- 方式1：用 @Me（2026-06实测可靠，返回458条任务）
SELECT [System.Id], [System.Title], [System.State]
FROM WorkItems
WHERE [System.TeamProject] = @Project
  AND [System.AssignedTo] = @Me
  AND [System.WorkItemType] = '任务'
ORDER BY [System.Id] DESC

-- 方式2：显式 AssignedTo（可能因转义问题返回0条）
SELECT [System.Id], [System.Title], [System.State]
FROM WorkItems
WHERE [System.TeamProject] = @Project
  AND [System.AssignedTo] = 'TELLHOW\\yangtao'
  AND [System.WorkItemType] = '任务'
ORDER BY [System.Id] DESC
```

**重要**：WIQL返回的JSON可能包含控制字符，直接用 `json.loads()` 会报错。
必须用 `json.loads(text, strict=False)` 或先 `curl -o file.json` 再读取文件。

### 补缺任务时查询策略

检查某段时间内哪些天没写任务：
1. 用WIQL查出所有任务，`-o` 写入文件
2. 用 `json.loads(file_content, strict=False)` 解析
3. 批量获取详情（GET workitems?ids=...&fields=System.Id,System.Title,Microsoft.VSTS.Scheduling.StartDate）
4. 按 StartDate 对照日历，找出缺失的工作日

### 无父级用户情景的任务

部分任务可能没有关联父级用户情景（relations为空数组）。这种情况下：
- 创建新任务时不需要添加 `/relations/-` 操作
- 直接创建独立任务即可
- 补缺时可参考最近一天的任务标题和描述来延续工作内容

## 常见陷阱
1. **JSON中的反斜杠**: Python字符串中的反斜杠会被吃掉。用 `write_file` 写JSON文件，再用 `curl -d @file` 发送。
2. **RemainingWork关闭时**: 不能传0，必须不传这个字段。
3. **API URL**: 创建工作项必须包含项目名 `/XiNanArea-New/_apis/wit/workitems/$%E4%BB%BB%E5%8A%A1`（URL编码），更新可以用全局路径。
4. **迭代名称**: 格式不统一，每次必须按任务 StartDate 查API确认。
5. **任务活动字段**: 是必填的，默认值为"开发"。
6. **Python urllib不能用中文URL**: 创建任务时URL包含中文类型名`任务`，Python urllib会报UnicodeEncodeError。**必须用curl**。
7. **创建URL的$符号**: curl中`$%E4%BB%BB%E5%8A%A1`的$需要转义为`\$`，或用单引号包裹URL。
8. **关闭用户情景的3个评价字段**: 质量评价、服务态度、用户体验都是必填picklist，不填会400错误。
9. **TargetDate格式**: 需要带时间部分和UTC时区后缀，如 `{日期}T09:30:00Z`，不能只传日期。用户时区UTC+8，所以 08:30本地=00:30UTC，17:30本地=09:30UTC。
10. **创建任务不能一步设为已关闭**: POST创建时不能在body里设State=已关闭，TFS会拒绝。必须先创建（State默认为新建），再单独PATCH关闭。
11. **每次必须动态获取日期**: 先查UTC时间+8小时算出用户本地日期，不要硬编码。
12. **WIQL `@Me` 宏**: 2026-06实测 `@Me` 查询**可靠**（返回458条任务），反而显式 `AssignedTo = 'TELLHOW\\yangtao'` 返回0条。两种方式都应准备好，互为备选。WIQL返回的JSON可能含控制字符，必须用 `json.loads(text, strict=False)` 或先curl写文件再读。
13. **WIQL JSON 控制字符**: API返回的JSON中可能包含控制字符（如tab、换行等），`json.loads()` 默认 strict=True 会报错 `Invalid control character`。解决方法：`json.loads(text, strict=False)` 或 `curl -o file.json` 后再读文件。
14. **无父级用户情景**: 部分任务可能没有关联父级用户情景（relations为空）。补缺任务时如果找不到父级，可以不关联父级直接创建独立任务。
15. **补缺任务参考内容**: 补缺时参考前一天的标题和描述来延续工作内容，保持工作线的自然连贯性。标题应体现工作的递进关系（如"搭建环境"→"功能验证"→"接口联调"）。
16. **分类API路径 ≠ IterationPath字段**: 分类API返回的path（如 `\XiNanArea-New\迭代\迭代2026-6-3`）与 IterationPath 字段值（如 `XiNanArea-New\迭代2026-6-3`）格式不同：API path有前导`\`和中间`迭代`层级，IterationPath没有。**不要直接用API path作为IterationPath**。必须先按任务 StartDate 匹配节点，再转换为字段值。
