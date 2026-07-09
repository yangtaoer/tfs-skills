# Codex TFS Skills 中文说明

本仓库收集了一组面向本地部署 TFS / Azure DevOps Server 的 Codex 技能，用来让 Codex 更稳定地处理工单、日常任务、代码提交和 PR 提交流程。

GitHub: https://github.com/yangtaoer/tfs-skills

English: [README.md](README.md)

## 适用场景

这些技能主要覆盖七类日常工作：

- 通过 REST API 查询和更新 TFS 工作项。
- 创建、补录和关闭每日 TFS 任务。
- 维护标准项目名、别名、仓库远程地址和基础分支。
- 按 `【标准项目名】` 规范录入 TFS 用户情景。
- 把一个 TFS 需求解析成本地多仓开发工作区。
- 将本地代码提交到 TFS Git，并创建指向目标分支的 Pull Request。
- 从已评审用户情景开始，完成本地分支准备、开发、提交 PR、可选更新用户情景状态的端到端流程。

## 目录结构

```text
skills/
├── tfs-rest-api/        # 底层 TFS REST API 工作流和示例
├── tfs-daily-task/      # 每日任务创建、补录、关闭任务和用户情景状态流转
├── tfs-project-catalog/ # 标准项目名、别名、仓库、基础分支目录
├── tfs-story-intake/    # 使用【标准项目名】录入/规范化用户情景
├── tfs-requirement-workspace/ # 需求 -> 本地多仓开发工作区解析
├── tfs-git-pr/          # 分支、提交、推送、PR、自动完成、工作项关联
└── tfs-dev-workflow/    # 用户情景 -> 本地仓库 -> 功能分支 -> PR 的完整开发流程
```

## 技能说明

### `tfs-rest-api`

当 Codex 需要直接查询或更新 TFS 工作项时使用。

它记录了：

- 基于 PAT 的 Basic Auth 认证方式。
- WIQL 查询和二次批量拉取工作项详情。
- 工作项创建、更新、状态流转和父子关联。
- 分类节点 / 迭代路径查询。
- 常见 TFS 坑点：JSON Patch Content-Type、中文工作项类型 URL 编码、WIQL 返回只含 ID、响应里可能包含控制字符等。

### `tfs-daily-task`

当用户需要创建、补录或关闭每日工作任务时使用。

它支持：

- 在用户情景下创建 8 小时 `任务`。
- 创建后立即关闭任务。
- 使用固定的任务描述模板，并把简短输入扩写成专业、完整的工作描述。
- 按任务开始日期查询并匹配 `System.IterationPath`。
- 补录缺失工作日任务。
- 未指定父级时，按最近任务查找可复用的父级用户情景。
- 在用户明确要求时，处理用户情景的 `已评审`、`已解决`、`已关闭` 状态流转。

### `tfs-project-catalog`

当 Codex 需要把需求里的项目别名解析成标准项目名、仓库和基础分支时使用。

它会约束：

- 用户情景标题必须使用 `【标准项目名】`。
- `省调网络发令`、`四川省调` 这类别名只用于匹配，最终归一到标准项目名。
- 项目目录维护项目涉及的仓库、远程地址、角色和目标分支。
- 本机路径默认放在本地索引或需求工作区，不强制提交到 GitHub。

当前种子目录：

```text
skills/tfs-project-catalog/references/project-catalog.seed.json
```

配套解析脚本：

```powershell
py -3 skills/tfs-project-catalog/scripts/resolve_tfs_workspace.py --help
```

### `tfs-story-intake`

当用户要录入或规范化 TFS `用户情景` 时使用。

它支持：

- 通过 `tfs-project-catalog` 确认需求属于哪个标准项目。
- 把标题规范成 `【标准项目名】简洁需求标题`。
- 一个需求涉及多个项目时使用多个 `【】`。
- 生成需求描述和验收标准草稿。
- 创建前查询可能重复的有效用户情景。

### `tfs-requirement-workspace`

当 TFS 需求已经存在，需要找到它涉及的本地仓库并准备开发上下文时使用。

它支持：

- 从用户情景标题解析 `【标准项目名】`。
- 解析一个或多个项目的全部仓库。
- 扫描本地仓库根目录。
- 优先按远程地址匹配本地仓库，其次按仓库名匹配。
- 生成需求级本地 workspace JSON。
- 确认后交给 `tfs-dev-workflow` 继续准备分支和开发。

### `tfs-git-pr`

当本地开发完成，需要提交到 `dev.tellhowsoft.com` 下的 TFS Git 仓库并创建 PR 时使用。

它会强制执行：

- 不直接在目标分支提交或推送。
- 首次使用时确认目标分支；未配置时才把 `dev` 作为兜底值。
- 从 `origin/<targetBranch>` 创建功能分支。
- 默认分支格式为 `feature/<workItemId>-<tfsAlias>`，例如 `feature/1551572-yangtao`。
- 提交标题格式为 `type(#workItemId):area-summary`。
- PR 标题必须与提交标题完全一致。
- PR 指向已确认的目标分支。
- 创建或复用 PR 后开启 auto-complete，并设置完成后删除源分支。
- 确保 PR 与 TFS 工作项关联。

配套 PowerShell 脚本：

```powershell
skills/tfs-git-pr/scripts/New-TfsGitPullRequest.ps1
```

跨平台 Python 脚本：

```bash
python3 skills/tfs-git-pr/scripts/new_tfs_git_pull_request.py --help
```

### `tfs-dev-workflow`

当用户希望从 TFS 已评审需求开始，完整推进到本地开发和 PR 提交时使用。

它会指导 Codex：

- 从配置的 TFS 保存查询中拉取已评审用户情景。
- 读取需求标题、状态、描述、验收标准和关联项。
- 要求用户提供本地仓库路径，而不是猜测需求和仓库的映射关系。
- 为每个涉及仓库从 `origin/<targetBranch>` 创建临时功能分支。
- 按代码库现有风格完成开发。
- 委托 `tfs-git-pr` 完成提交、推送、PR、auto-complete 和工作项关联。
- 仅在用户确认完成后，把用户情景状态更新为 `已解决`。

配套 PowerShell 脚本：

```powershell
skills/tfs-dev-workflow/scripts/Get-TfsSavedQueryWorkItems.ps1
skills/tfs-dev-workflow/scripts/Start-TfsFeatureBranch.ps1
skills/tfs-dev-workflow/scripts/Set-TfsWorkItemState.ps1
```

跨平台 Python 脚本：

```bash
python3 skills/tfs-dev-workflow/scripts/tfs_workflow.py --help
```

## 安装方式

把需要的技能目录复制到 Codex skills 目录中。

Windows PowerShell 示例：

```powershell
$repo = "C:\path\to\this\repo"
$skillsHome = "$env:USERPROFILE\.codex\skills"

Copy-Item -Recurse -Force "$repo\skills\tfs-rest-api" "$skillsHome\tfs-rest-api"
Copy-Item -Recurse -Force "$repo\skills\tfs-daily-task" "$skillsHome\tfs-daily-task"
Copy-Item -Recurse -Force "$repo\skills\tfs-project-catalog" "$skillsHome\tfs-project-catalog"
Copy-Item -Recurse -Force "$repo\skills\tfs-story-intake" "$skillsHome\tfs-story-intake"
Copy-Item -Recurse -Force "$repo\skills\tfs-requirement-workspace" "$skillsHome\tfs-requirement-workspace"
Copy-Item -Recurse -Force "$repo\skills\tfs-git-pr" "$skillsHome\tfs-git-pr"
Copy-Item -Recurse -Force "$repo\skills\tfs-dev-workflow" "$skillsHome\tfs-dev-workflow"
```

macOS / Linux 示例：

```bash
repo="/path/to/this/repo"
skills_home="${CODEX_HOME:-$HOME/.codex}/skills"

mkdir -p "$skills_home"
cp -R "$repo/skills/tfs-rest-api" "$skills_home/tfs-rest-api"
cp -R "$repo/skills/tfs-daily-task" "$skills_home/tfs-daily-task"
cp -R "$repo/skills/tfs-project-catalog" "$skills_home/tfs-project-catalog"
cp -R "$repo/skills/tfs-story-intake" "$skills_home/tfs-story-intake"
cp -R "$repo/skills/tfs-requirement-workspace" "$skills_home/tfs-requirement-workspace"
cp -R "$repo/skills/tfs-git-pr" "$skills_home/tfs-git-pr"
cp -R "$repo/skills/tfs-dev-workflow" "$skills_home/tfs-dev-workflow"
```

安装或更新技能后，建议新开一个 Codex 线程，让技能元数据重新加载。

## 环境变量

调用 TFS API 的脚本需要先设置 `TFS_PAT`。

```powershell
$env:TFS_PAT = "<your-personal-access-token>"
```

常用可选变量：

```powershell
$env:TFS_USER_ALIAS = "your-alias"
$env:TFS_USER_STORY_QUERY_URL = "http://dev.tellhowsoft.com/DefaultCollection/XiNanArea-New/_queries/query/<query-id>"
$env:TFS_TARGET_BRANCH = "dev"
$env:TFS_BASE_URL = "http://dev.tellhowsoft.com/DefaultCollection"
$env:TFS_REPO_HOST = "dev.tellhowsoft.com"
$env:TFS_ASSIGNED_TO = "TELLHOW\your-alias"
$env:TFS_AREA_PATH = "XiNanArea-New\your-team"
```

macOS / Linux 示例：

```bash
export TFS_PAT="<your-personal-access-token>"
export TFS_USER_ALIAS="your-alias"
export TFS_USER_STORY_QUERY_URL="http://dev.tellhowsoft.com/DefaultCollection/XiNanArea-New/_queries/query/<query-id>"
export TFS_TARGET_BRANCH="dev"
export TFS_BASE_URL="http://dev.tellhowsoft.com/DefaultCollection"
export TFS_REPO_HOST="dev.tellhowsoft.com"
export TFS_ASSIGNED_TO="TELLHOW\\your-alias"
export TFS_AREA_PATH="XiNanArea-New\\your-team"
```

不要提交 PAT、密码、生成的请求 JSON、日志或本地配置文件。

## 典型用法

### 录入带标准项目名的用户情景

可以这样对 Codex 说：

```text
帮我录一个 TFS 用户情景，省调网络发令需要新增发令审核提醒，验收标准是审核人能收到提醒并跳转到待办。
```

Codex 应先使用 `tfs-project-catalog` 把 `省调网络发令` 解析为标准项目名，再使用 `tfs-story-intake` 生成类似 `【四川省调网络发令】新增发令审核提醒` 的标题、描述和验收标准，确认后创建用户情景。

新建用户情景默认状态为 `新建`，区域为 `XiNanArea-New\四川省区团队`，迭代选择符合当前日期的迭代；所属地区部为 `西南地区部`，所属省份为 `四川`，是否需要产品部支持为 `否`，是否需要上会讨论为 `否`，负责开发部门为 `地区部`，需求交付负责人为 `杨涛(四川)`，所属产品线为 `调度产品线`，产品名称优先从项目目录判断，无法判断时使用 `临时项目交付`。

### 把需求解析成本地多仓开发工作区

可以这样对 Codex 说：

```text
开始 1551572 这个需求，帮我找到它涉及的本地仓库并准备开发工作区。
```

Codex 应使用 `tfs-requirement-workspace`，读取用户情景标题里的 `【标准项目名】`，从项目目录解析仓库，扫描本地仓库根目录，生成 workspace JSON，并在准备分支前让用户确认。

### 创建每日 TFS 任务

可以这样对 Codex 说：

```text
帮我按今天的工作创建 TFS 任务，父级是 1580688，内容是完善巴中绩效考核系统交付闭环。
```

Codex 应使用 `tfs-daily-task`，按任务日期查询迭代，创建任务，并以 8 小时完成工时关闭任务。

### 补录多天任务

可以这样对 Codex 说：

```text
帮我补录 2026-06-01 到 2026-06-05 的 TFS 任务，父级 1580688，内容是巴中绩效考核系统联调。
```

Codex 应先确认哪些日期不需要补录，再按每个任务日期分别匹配迭代，创建并关闭任务。

### 提交代码并创建 TFS PR

可以这样对 Codex 说：

```text
开发完成了，提交到 TFS，用户情景 1551572，标题用 feat(#1551572):成都-配网拟票自动联想功能优化...
```

Codex 应使用 `tfs-git-pr`，确认目标分支，从 `origin/<targetBranch>` 创建功能分支，提交、推送、创建 PR，开启 auto-complete，设置源分支完成后删除，并验证工作项关联。

### 从已评审需求开始开发

可以这样对 Codex 说：

```text
从 TFS 已评审需求里选一个巴中绩效相关需求，仓库路径是 C:\work\workSpaceTellHow\th-dc-biz-bazhong，开始开发。
```

Codex 应使用 `tfs-dev-workflow`，从保存查询中加载候选需求，确认目标分支，为本地仓库创建 `feature/<workItemId>-<tfsAlias>` 分支，再按需求进入开发。

## 关键规则

### TFS 工作项规则

- 认证优先读取环境变量 `TFS_PAT`，不要打印或持久化 PAT。
- 创建或更新工作项时使用 `Content-Type: application/json-patch+json`。
- 创建中文类型工作项时，URL 中的类型名必须编码，例如 `任务` 使用 `%E4%BB%BB%E5%8A%A1`。
- WIQL 查询通常只返回工作项 ID，需要二次批量获取字段详情。
- WIQL 响应可能包含控制字符，Python 解析时可使用 `json.loads(text, strict=False)`。
- 任务不能在创建请求中直接设置为 `已关闭`，必须先创建，再 PATCH 关闭。
- 关闭任务时不要传 `RemainingWork=0`；关闭请求里不要包含 `RemainingWork`，只设置状态和完成工时。
- 迭代名称必须按任务开始日期查询分类节点确认，不要直接复用父级用户情景的迭代。

### Git / PR 规则

- 不直接在目标分支提交。
- 不直接推送目标分支。
- 不执行破坏性 Git 操作，除非用户明确要求。
- 每次提交前只暂存本次任务相关文件。
- PR 目标分支必须是已确认的分支。
- PR 标题必须与提交标题一致。
- 不手动合并 PR，通过 auto-complete 完成。
- 源分支删除通过 PR completion options 配置，不手动删除远程分支。

## 校验方式

本仓库可用以下命令做基础检查。

PowerShell 脚本语法检查：

```powershell
Get-ChildItem .\skills -Recurse -Filter *.ps1 | ForEach-Object {
  [scriptblock]::Create((Get-Content -LiteralPath $_.FullName -Raw)) | Out-Null
}
```

搜索明显 TODO 占位：

```powershell
Select-String -Path .\skills\*\*.md,.\README.md,.\README.zh-CN.md -Pattern "TODO","[TODO" -SimpleMatch |
  Where-Object { $_.Line -notmatch "TODO placeholders|TODO 占位|Select-String -Path" }
```

部分 Codex 技能校验脚本需要 `PyYAML`。如果本地没有安装，可手动检查 frontmatter，或在本地 Python 环境中安装后再运行校验。

## 维护建议

- 修改技能行为后，同步更新本 README 和对应技能目录下的 `references/` 文档。
- 修改 PR 或 TFS API 脚本后，至少运行脚本语法检查，并用 `--help` 或无副作用参数验证入口可用。
- 新增技能时，补充目录结构、安装命令、环境变量和典型用法。
- 与 TFS 交互的示例只使用占位 PAT，不要把真实请求文件、响应日志或令牌提交到仓库。
