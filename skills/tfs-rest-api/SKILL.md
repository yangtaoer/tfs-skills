---
name: tfs-rest-api
description: Query and manage TFS (Azure DevOps Server) work items via REST API — WIQL queries, CRUD, linking, state transitions.
tags: [tfs, azure-devops, rest-api, work-items, wiql]
---

# TFS (Azure DevOps Server) REST API

Manage work items on on-premise Azure DevOps Server (TFS) via REST API using PAT authentication.

## Authentication

Use Personal Access Token (PAT) with HTTP Basic auth:
```bash
curl -u ":<PAT>" "http://<tfs-host>/DefaultCollection/_apis/..."
```

Or in Python:
```python
import base64
credentials = base64.b64encode((':' + pat).encode()).decode()
headers = {'Authorization': 'Basic ' + credentials}
```

## Key API Endpoints

| Action | Method | URL |
|--------|--------|-----|
| List projects | GET | `/_apis/projects?api-version=2.0` |
| WIQL query | POST | `/{project}/_apis/wit/wiql?api-version=2.0` |
| Get work item | GET | `/_apis/wit/workitems/{id}?api-version=2.0` |
| Get multiple | GET | `/_apis/wit/workitems?ids=1,2,3&fields=...&api-version=2.0` |
| Create work item | POST | `/{project}/_apis/wit/workitems/${type}?api-version=2.0` |
| Update work item | PATCH | `/_apis/wit/workitems/{id}?api-version=2.0` |
| List iterations | GET | `/{project}/_apis/wit/classificationnodes/iterations?$depth=3&api-version=2.0` |
| List fields | GET | `/{project}/_apis/wit/fields?api-version=2.0` |
| Work item types | GET | `/{project}/_apis/wit/workitemtypes?api-version=2.0` |

## WIQL Queries

POST JSON body with `query` field to the WIQL endpoint. Use Unicode escapes for Chinese characters:

```json
{
  "query": "SELECT [System.Id], [System.Title], [System.State] FROM WorkItems WHERE [System.TeamProject] = @Project AND [System.AssignedTo] = @Me AND [System.WorkItemType] = '用户情景' ORDER BY [System.Id] DESC"
}
```

**Important**: Response only returns work item IDs and URLs. Must make a second call to get field details.

## Steps: Create Child Task Under User Story

1. Write JSON patch body to a file (avoids shell escaping issues)
2. Use `curl -d @file.json` to POST
3. Must include all required fields or creation fails

## Critical Pitfalls

### 1. Content-Type for Create/Update
```
Content-Type: application/json-patch+json
```
NOT `application/json`. The create/update endpoints use JSON Patch format (array of ops).

### 2. Create URL Must Include Project
```
/{project}/_apis/wit/workitems/${url_encoded_type}?api-version=2.0
```
NOT `/_apis/wit/workitems/...`. The project name MUST be in the URL path.

### 3. Required Fields for Task Creation
Tasks require these fields at minimum:
- `System.Title`
- `Microsoft.VSTS.Scheduling.RemainingWork` (number, e.g. 8)
- `Microsoft.VSTS.Scheduling.OriginalEstimate` (number, e.g. 8)
- `Microsoft.VSTS.Common.Activity` (e.g. "开发")
- `System.IterationPath`

### 4. Closing a Task — RemainingWork Must Be EMPTY
When setting state to "已关闭", `RemainingWork` must be removed/empty, NOT set to 0.
Setting it to 0 causes: `TF401320: 字段 剩余工作 发生规则错误。错误代码: InvalidNotEmpty。`

Solution: Don't include RemainingWork in the close operation. Just set state + CompletedWork.

### 11. Cannot Set State=已关闭 on Task Creation
When creating a task, you CANNOT set `System.State` to `已关闭` in the same POST request — TFS rejects it with "字段'状态'包含的值'已关闭'不在受支持值的列表中". The initial state must be the default (新建). You must create first, then make a separate PATCH call to change the state to 已关闭.

### 12. Closing 用户情景 Requires 3 Evaluation Fields
When transitioning a 用户情景 to 已关闭, three custom picklist fields become mandatory:
- **质量评价** (`Custom.a6fb40d4-5f26-4167-b47c-b056ab423f49`)
- **服务态度** (`Custom.2286db83-008a-4bbc-bdd2-98a779a142d6`)
- **用户体验** (`Custom.b7a089cf-99c0-4d5c-ab03-8bd3f068194f`)

Typical values (score 5):
- `5-功能完备可正常运行，满足使用`
- `5-服务亲切热情且耐心好`
- `5-界面美观、布局合理、呈现清晰、操作极简`

Without these, you get a 400 with `TF401320: 字段 质量评价 发生规则错误`. To discover valid values, query existing closed items that have these fields populated.

### 5. AreaPath/IterationPath Backslash Escaping
When writing JSON via Python string literals, backslashes get eaten. 
**Solution**: Write JSON to a file first, then use `curl -d @file.json`:

```python
with open('tfs_update.json', 'w', encoding='utf-8') as f:
    f.write('[{"op": "replace", "path": "/fields/System.AreaPath", "value": "XiNanArea-New\\\\\\\\四川省区团队"}]')
```

Or use `write_file` tool to write literal JSON, then curl it.

### 6. Finding Correct Iteration Names
Iteration names may have inconsistent spacing (e.g., "迭代 2026-4-4" vs "迭代2026-5-1").
Always query classification nodes to get exact names:
```
GET /{project}/_apis/wit/classificationnodes/iterations?$depth=3&api-version=2.0
```

### 7. Linking as Child (Parent-Child Relation)
Use `System.LinkTypes.Hierarchy-Reverse` relation to create a child:
```json
{
  "op": "add",
  "path": "/relations/-",
  "value": {
    "rel": "System.LinkTypes.Hierarchy-Reverse",
    "url": "http://<tfs>/DefaultCollection/_apis/wit/workItems/<parent_id>"
  }
}
```

### 8. Custom Fields
Custom fields use GUID reference names. Find them via:
```
GET /{project}/_apis/wit/fields?api-version=2.0
```
Then filter by name. Example: "需求交付负责人" = `Custom.3d3cdcf5-de35-4448-afbb-bdfd963d2564`

### 9. WIQL with Custom Fields
Custom fields can be used in WIQL queries by their reference name:
```
WHERE [Custom.3d3cdcf5-de35-4448-afbb-bdfd963d2564] = @Me
```

### 10. Batch Fetching Work Item Details
WIQL returns IDs only. Fetch details in batches of 200:
```
GET /_apis/wit/workitems?ids=1,2,...,200&fields=System.Id,System.Title,System.State&api-version=2.0
```

### 11. WIQL @Me vs Explicit AssignedTo
Both `@Me` and explicit `AssignedTo` should be tried as fallbacks:
- `@Me`: Worked reliably in 2026-06 testing (returned 458 tasks)
- `AssignedTo = 'TELLHOW\\yangtao'`: Returned 0 results (possible escaping issue)
- Try `@Me` first; if it fails, fall back to explicit assignment or known-ID queries

### 12. WIQL Response JSON Control Characters
WIQL API responses may contain control characters (tabs, newlines) in field values.
`json.loads()` with default `strict=True` raises `Invalid control character` error.
Fix: `json.loads(text, strict=False)` or `curl -o file.json` then read the file.

### 11. Creating Work Items with Chinese Type Names
The URL path for creating work items with Chinese type names (e.g. `任务`) MUST use URL encoding:
```
POST /{project}/_apis/wit/workitems/$%E4%BB%BB%E5%8A%A1?api-version=2.0
```
Python `urllib.parse.quote('任务')` produces `%E4%BB%BB%E5%8A%A1`.
**Do NOT** pass the raw Chinese characters in the URL — Python's `http.client` will fail with `UnicodeEncodeError: 'ascii' codec can't encode`.
**Always use `curl -d @file.json`** for requests involving Chinese in the URL path.

### 12. Closing a 用户情景 Requires 3 Mandatory Evaluation Fields
When transitioning a 用户情景 to 已关闭, TFS requires three picklist fields:
- **质量评价** (`Custom.a6fb40d4-5f26-4167-b47c-b056ab423f49`)
- **服务态度** (`Custom.2286db83-008a-4bbc-bdd2-98a779a142d6`)
- **用户体验** (`Custom.b7a089cf-99c0-4d5c-ab03-8bd3f068194f`)

If missing, returns: `TF401320: 字段 质量评价 发生规则错误。错误代码: Required, HasValues, LimitedToValues, AllowsOldValue, InvalidEmpty。`

Valid values (all 5-score):
```
质量评价: 5-功能完备可正常运行，满足使用
服务态度: 5-服务亲切热情且耐心好
用户体验: 5-界面美观、布局合理、呈现清晰、操作极简
```

To discover valid values for any picklist field, find an existing closed item with values populated:
```
WIQL: SELECT [System.Id] FROM WorkItems WHERE [Custom.a6fb40d4-...] <> '' AND [System.State] = '已关闭'
```

## Task Creation Workflow (Daily Report Tasks)

### Principles
1. Every task is fixed 8 hours (OriginalEstimate=8, CompletedWork=8). Do NOT set RemainingWork when closing (leave empty).
2. User timezone is **UTC+8**. TFS stores UTC, so: local 08:30 = UTC 00:30, local 17:30 = UTC 09:30.
   - `StartDate` = `{date}T00:30:00Z` (displays as 08:30 local)
   - `TargetDate` / `FinishDate` = `{date}T09:30:00Z` (displays as 17:30 local)
3. **Always get current UTC time first**, add 8 hours to get user's local date. Use that local date. Never hardcode dates.
4. Description MUST use this template:
   ```
   1、今日完成开发情况（{具体内容}）
   2、BUG修复情况（无）
   3、需求沟通情况（无）
   4、其他（无）
   ```
5. Cannot set State=已关闭 during creation. Must create first (default state 新建), then PATCH to close.

### Step-by-Step

**Step 1: Get current local date**
```bash
py -3 -c "from datetime import datetime, timedelta, timezone; now=datetime.now(timezone.utc)+timedelta(hours=8); print(now.strftime('%Y-%m-%d'))"
```

**Step 2: Write create JSON to file**
```python
import json
date = '2026-05-09'  # from step 1
patch_data = [
    {'op': 'add', 'path': '/fields/System.Title', 'value': '任务标题'},
    {'op': 'add', 'path': '/fields/System.AssignedTo', 'value': 'TELLHOW\\yangtao'},
    {'op': 'add', 'path': '/fields/System.AreaPath', 'value': 'XiNanArea-New\\四川省区团队'},
    {'op': 'add', 'path': '/fields/System.IterationPath', 'value': 'XiNanArea-New\\迭代2026-5-1'},
    {'op': 'add', 'path': '/fields/Microsoft.VSTS.Scheduling.OriginalEstimate', 'value': 8},
    {'op': 'add', 'path': '/fields/Microsoft.VSTS.Scheduling.RemainingWork', 'value': 8},
    {'op': 'add', 'path': '/fields/Microsoft.VSTS.Scheduling.StartDate', 'value': f'{date}T00:30:00Z'},
    {'op': 'add', 'path': '/fields/Microsoft.VSTS.Scheduling.TargetDate', 'value': f'{date}T09:30:00Z'},
    {'op': 'add', 'path': '/fields/Microsoft.VSTS.Common.Activity', 'value': '开发'},
    {'op': 'add', 'path': '/fields/System.Description', 'value': '<div>1、今日完成开发情况（）<br>2、BUG修复情况（无）<br>3、需求沟通情况（无）<br>4、其他（无）</div>'},
    {'op': 'add', 'path': '/relations/-', 'value': {
        'rel': 'System.LinkTypes.Hierarchy-Reverse',
        'url': 'http://dev.tellhowsoft.com/DefaultCollection/_apis/wit/workItems/{parent_id}'
    }}
]
with open('tfs_create.json', 'w', encoding='utf-8') as f:
    json.dump(patch_data, f, ensure_ascii=False)
```

**Step 3: Create task via curl**
```bash
curl -u ":<PAT>" -X POST -H "Content-Type: application/json-patch+json" \
  -d @tfs_create.json \
  "http://dev.tellhowsoft.com/DefaultCollection/XiNanArea-New/_apis/wit/workitems/\$%E4%BB%BB%E5%8A%A1?api-version=2.0"
```

**Step 4: Close task via PATCH**
```python
patch_data = [
    {'op': 'replace', 'path': '/fields/System.State', 'value': '已关闭'},
    {'op': 'replace', 'path': '/fields/Microsoft.VSTS.Scheduling.CompletedWork', 'value': 8}
]
with open('tfs_close.json', 'w', encoding='utf-8') as f:
    json.dump(patch_data, f, ensure_ascii=False)
```
```bash
curl -u ":<PAT>" -X PATCH -H "Content-Type: application/json-patch+json" \
  -d @tfs_close.json \
  "http://dev.tellhowsoft.com/DefaultCollection/_apis/wit/workitems/{task_id}?api-version=2.0"
```

## Quick Reference: Common Operations

See `references/api-examples.md` for ready-to-use curl/Python snippets for common tasks.
