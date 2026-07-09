# TFS REST API — Ready-to-Use Examples

All examples use `PAT` as placeholder for your Personal Access Token.

## Query My Work Items by Custom Field

```bash
py -3 -c "
import urllib.request, json, base64

pat = 'PAT'
credentials = base64.b64encode((':' + pat).encode()).decode()
headers = {'Authorization': 'Basic ' + credentials, 'Content-Type': 'application/json'}

query = {
    'query': \"SELECT [System.Id], [System.Title], [System.State] FROM WorkItems WHERE [System.TeamProject] = @Project AND [Custom.3d3cdcf5-de35-4448-afbb-bdfd963d2564] = @Me AND [System.WorkItemType] = '\u7528\u6237\u60c5\u666f' AND [System.State] = '\u5df2\u8bc4\u5ba1' ORDER BY [System.Id] DESC\"
}

data = json.dumps(query).encode('utf-8')
req = urllib.request.Request(
    'http://dev.tellhowsoft.com/DefaultCollection/XiNanArea-New/_apis/wit/wiql?api-version=2.0',
    data=data, headers=headers, method='POST'
)

with urllib.request.urlopen(req, timeout=30) as resp:
    result = json.loads(resp.read().decode('utf-8'))
    work_items = result.get('workItems', [])
    if work_items:
        ids = ','.join([str(w['id']) for w in work_items])
        detail_url = f'http://dev.tellhowsoft.com/DefaultCollection/_apis/wit/workitems?ids={ids}&fields=System.Id,System.Title,System.State&api-version=2.0'
        req2 = urllib.request.Request(detail_url, headers=headers)
        with urllib.request.urlopen(req2, timeout=30) as resp2:
            details = json.loads(resp2.read().decode('utf-8'))
            for item in details.get('value', []):
                f = item.get('fields', {})
                print(f'{f.get(\"System.Id\")} | {f.get(\"System.State\")} | {f.get(\"System.Title\")}')
"
```

## Create Child Task (via file-based approach)

Step 1 — Write JSON body to file:
```json
[
  {"op": "add", "path": "/fields/System.Title", "value": "任务标题"},
  {"op": "add", "path": "/fields/System.Description", "value": "任务描述"},
  {"op": "add", "path": "/fields/Microsoft.VSTS.Scheduling.RemainingWork", "value": 8},
  {"op": "add", "path": "/fields/Microsoft.VSTS.Scheduling.OriginalEstimate", "value": 8},
  {"op": "add", "path": "/fields/Microsoft.VSTS.Common.Activity", "value": "开发"},
  {"op": "add", "path": "/fields/System.IterationPath", "value": "XiNanArea-New\\迭代2026-5-1"},
  {"op": "add", "path": "/relations/-", "value": {
    "rel": "System.LinkTypes.Hierarchy-Reverse",
    "url": "http://dev.tellhowsoft.com/DefaultCollection/_apis/wit/workItems/PARENT_ID"
  }}
]
```

Step 2 — POST with curl (note the `$` before encoded type):
```bash
curl -s -u ":PAT" -X POST \
  -H "Content-Type: application/json-patch+json; charset=utf-8" \
  -d @tfs_create.json \
  "http://dev.tellhowsoft.com/DefaultCollection/XiNanArea-New/_apis/wit/workitems/$%E4%BB%BB%E5%8A%A1?api-version=2.0"
```

Note: `%E4%BB%BB%E5%8A%A1` = URL-encoded "任务"

## Close a Task

Step 1 — Write update JSON (RemainingWork must NOT be included):
```json
[
  {"op": "add", "path": "/fields/System.State", "value": "已关闭"},
  {"op": "add", "path": "/fields/Microsoft.VSTS.Scheduling.OriginalEstimate", "value": 8},
  {"op": "add", "path": "/fields/Microsoft.VSTS.Scheduling.CompletedWork", "value": 8}
]
```

Step 2 — PATCH:
```bash
curl -s -u ":PAT" -X PATCH \
  -H "Content-Type: application/json-patch+json; charset=utf-8" \
  -d @tfs_update.json \
  "http://dev.tellhowsoft.com/DefaultCollection/_apis/wit/workitems/TASK_ID?api-version=2.0"
```

## Update AreaPath and IterationPath

Must reactivate first if closed, then change paths, then close again:
```json
[
  {"op": "replace", "path": "/fields/System.State", "value": "新建"},
  {"op": "replace", "path": "/fields/System.AreaPath", "value": "XiNanArea-New\\四川省区团队"},
  {"op": "replace", "path": "/fields/System.IterationPath", "value": "XiNanArea-New\\迭代2026-5-1"}
]
```

## List All Iterations (find exact names)

```bash
curl -s -u ":PAT" \
  "http://dev.tellhowsoft.com/DefaultCollection/XiNanArea-New/_apis/wit/classificationnodes/iterations?\$depth=3&api-version=2.0"
```

## Find Custom Field Reference Names

```bash
curl -s -u ":PAT" \
  "http://dev.tellhowsoft.com/DefaultCollection/XiNanArea-New/_apis/wit/fields?api-version=2.0" \
  | py -3 -c "import sys,json; [print(f'{f[\"referenceName\"]} => {f[\"name\"]}') for f in json.loads(sys.stdin.read()).get('value',[]) if 'KEYWORD' in f.get('name','')]"
```
