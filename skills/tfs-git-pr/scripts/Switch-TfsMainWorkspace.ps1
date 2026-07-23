[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$MainRepoPath,

    [Parameter(Mandatory = $true)]
    [string]$SourceBranch,

    [string]$TemporaryWorktreePath
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-Git {
    param(
        [Parameter(Mandatory = $true)][string]$RepoPath,
        [Parameter(Mandatory = $true)][string[]]$Arguments
    )

    $output = & git -C $RepoPath @Arguments 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "git -C '$RepoPath' $($Arguments -join ' ') failed: $output"
    }
    return ($output | Out-String).Trim()
}

function Get-NormalizedPath {
    param([Parameter(Mandatory = $true)][string]$Path)

    return [System.IO.Path]::GetFullPath((Resolve-Path -LiteralPath $Path).Path).TrimEnd('\', '/')
}

function Get-GitCommonDirectory {
    param([Parameter(Mandatory = $true)][string]$RepoPath)

    $commonDirectory = Invoke-Git -RepoPath $RepoPath -Arguments @("rev-parse", "--git-common-dir")
    if (-not [System.IO.Path]::IsPathRooted($commonDirectory)) {
        $commonDirectory = Join-Path $RepoPath $commonDirectory
    }
    return [System.IO.Path]::GetFullPath($commonDirectory).TrimEnd('\', '/')
}

if (-not (Test-Path -LiteralPath $MainRepoPath)) {
    throw "MainRepoPath does not exist: $MainRepoPath"
}

$mainPath = Get-NormalizedPath -Path $MainRepoPath
if ((Invoke-Git -RepoPath $mainPath -Arguments @("rev-parse", "--is-inside-work-tree")) -ne "true") {
    throw "MainRepoPath is not a Git worktree: $mainPath"
}

$mainStatus = Invoke-Git -RepoPath $mainPath -Arguments @("status", "--porcelain")
if (-not [string]::IsNullOrWhiteSpace($mainStatus)) {
    throw "Main workspace is not clean; leave it unchanged and resolve these files first:`n$mainStatus"
}

Invoke-Git -RepoPath $mainPath -Arguments @("fetch", "origin", $SourceBranch) | Out-Null
$remoteSourceRef = "refs/remotes/origin/$SourceBranch"
& git -C $mainPath show-ref --verify --quiet $remoteSourceRef
if ($LASTEXITCODE -ne 0) {
    throw "Remote source branch does not exist: origin/$SourceBranch. The PR may already be merged; update the confirmed target branch instead."
}
$remoteCommit = Invoke-Git -RepoPath $mainPath -Arguments @("rev-parse", $remoteSourceRef)

$removedWorktree = $false
if (-not [string]::IsNullOrWhiteSpace($TemporaryWorktreePath) -and (Test-Path -LiteralPath $TemporaryWorktreePath)) {
    $temporaryPath = Get-NormalizedPath -Path $TemporaryWorktreePath
    if ($temporaryPath -eq $mainPath) {
        throw "TemporaryWorktreePath must not be the main workspace path."
    }
    if ((Get-GitCommonDirectory -RepoPath $temporaryPath) -ne (Get-GitCommonDirectory -RepoPath $mainPath)) {
        throw "Temporary worktree belongs to a different repository: $temporaryPath"
    }

    $temporaryStatus = Invoke-Git -RepoPath $temporaryPath -Arguments @("status", "--porcelain")
    if (-not [string]::IsNullOrWhiteSpace($temporaryStatus)) {
        throw "Temporary worktree is not clean; it will not be removed:`n$temporaryStatus"
    }
    $temporaryBranch = Invoke-Git -RepoPath $temporaryPath -Arguments @("branch", "--show-current")
    if ($temporaryBranch -ne $SourceBranch) {
        throw "Temporary worktree branch '$temporaryBranch' does not match source branch '$SourceBranch'."
    }
    $temporaryCommit = Invoke-Git -RepoPath $temporaryPath -Arguments @("rev-parse", "HEAD")
    if ($temporaryCommit -ne $remoteCommit) {
        throw "Temporary worktree HEAD is not fully pushed to origin/$SourceBranch."
    }

    Invoke-Git -RepoPath $mainPath -Arguments @("worktree", "remove", $temporaryPath) | Out-Null
    $removedWorktree = $true
}

Invoke-Git -RepoPath $mainPath -Arguments @("worktree", "prune") | Out-Null
$localBranch = Invoke-Git -RepoPath $mainPath -Arguments @("branch", "--list", $SourceBranch)
if ([string]::IsNullOrWhiteSpace($localBranch)) {
    Invoke-Git -RepoPath $mainPath -Arguments @("switch", "-c", $SourceBranch, "--track", "origin/$SourceBranch") | Out-Null
}
else {
    Invoke-Git -RepoPath $mainPath -Arguments @("switch", $SourceBranch) | Out-Null
    $localCommit = Invoke-Git -RepoPath $mainPath -Arguments @("rev-parse", "HEAD")
    if ($localCommit -ne $remoteCommit) {
        $counts = (Invoke-Git -RepoPath $mainPath -Arguments @("rev-list", "--left-right", "--count", "HEAD...origin/$SourceBranch")) -split '\s+'
        if ([int]$counts[0] -gt 0) {
            throw "Local source branch contains commits that are not on origin/$SourceBranch; it was not changed."
        }
        Invoke-Git -RepoPath $mainPath -Arguments @("merge", "--ff-only", "origin/$SourceBranch") | Out-Null
    }
}

$finalStatus = Invoke-Git -RepoPath $mainPath -Arguments @("status", "--porcelain")
if (-not [string]::IsNullOrWhiteSpace($finalStatus)) {
    throw "Main workspace became dirty after switching:`n$finalStatus"
}

[pscustomobject]@{
    MainRepoPath          = $mainPath
    SourceBranch          = (Invoke-Git -RepoPath $mainPath -Arguments @("branch", "--show-current"))
    Upstream              = (Invoke-Git -RepoPath $mainPath -Arguments @("rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"))
    Commit                = (Invoke-Git -RepoPath $mainPath -Arguments @("rev-parse", "HEAD"))
    TemporaryWorktreeRemoved = $removedWorktree
    Clean                 = $true
} | ConvertTo-Json -Depth 5
