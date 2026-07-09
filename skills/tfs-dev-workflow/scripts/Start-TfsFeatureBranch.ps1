[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RepoPath,

    [Parameter(Mandatory = $true)]
    [int]$WorkItemId,

    [string]$TfsAlias = $env:TFS_USER_ALIAS,

    [string]$TargetBranch = $env:TFS_TARGET_BRANCH,

    [string]$RemoteHost = $env:TFS_REPO_HOST
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-Git {
    param([Parameter(Mandatory = $true)][string[]]$Arguments)

    $output = & git -C $RepoPath @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "git $($Arguments -join ' ') failed: $output"
    }
    return ($output | Out-String).Trim()
}

if (-not (Test-Path -LiteralPath $RepoPath)) {
    throw "RepoPath does not exist: $RepoPath"
}

if ([string]::IsNullOrWhiteSpace($TfsAlias)) {
    throw "TfsAlias is required. Provide -TfsAlias or set TFS_USER_ALIAS."
}

if ([string]::IsNullOrWhiteSpace($TargetBranch)) {
    $TargetBranch = "dev"
}

if ([string]::IsNullOrWhiteSpace($RemoteHost)) {
    $RemoteHost = "dev.tellhowsoft.com"
}

$inside = Invoke-Git -Arguments @("rev-parse", "--is-inside-work-tree")
if ($inside -ne "true") {
    throw "RepoPath is not a git work tree: $RepoPath"
}

$origin = Invoke-Git -Arguments @("remote", "get-url", "origin")
if ($origin -notmatch [regex]::Escape($RemoteHost)) {
    throw "origin remote is not a $RemoteHost repository: $origin"
}

$status = Invoke-Git -Arguments @("status", "--short")
if (-not [string]::IsNullOrWhiteSpace($status)) {
    throw "Working tree is not clean. Preserve or commit existing changes before creating the feature branch.`n$status"
}

$branchName = "feature/$WorkItemId-$TfsAlias"
Invoke-Git -Arguments @("fetch", "origin", $TargetBranch) | Out-Null

$localBranches = Invoke-Git -Arguments @("branch", "--list", $branchName)
if ([string]::IsNullOrWhiteSpace($localBranches)) {
    Invoke-Git -Arguments @("switch", "-c", $branchName, "origin/$TargetBranch") | Out-Null
}
else {
    Invoke-Git -Arguments @("switch", $branchName) | Out-Null
}

[pscustomobject]@{
    RepoPath     = (Resolve-Path -LiteralPath $RepoPath).Path
    Branch       = $branchName
    Base         = "origin/$TargetBranch"
    Origin       = $origin
    WorkItemId   = $WorkItemId
    TfsAlias     = $TfsAlias
} | ConvertTo-Json -Depth 6
