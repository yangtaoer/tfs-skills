[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$RepoPath,

    [Parameter(Mandatory = $true)]
    [string]$SourceBranch,

    [string]$TargetBranch = "dev",

    [Parameter(Mandatory = $true)]
    [string]$Title,

    [string]$Description = "",

    [int]$WorkItemId = 0,

    [bool]$SetAutoComplete = $true,

    [bool]$DeleteSourceBranch = $true,

    [string]$TfsBaseUrl = "http://dev.tellhowsoft.com/DefaultCollection"
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

function New-TfsHeaders {
    if (-not $env:TFS_PAT) {
        throw "TFS_PAT is not set."
    }

    $token = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes(":" + $env:TFS_PAT))
    return @{ Authorization = "Basic $token" }
}

function Invoke-TfsRest {
    param(
        [Parameter(Mandatory = $true)][string]$Method,
        [Parameter(Mandatory = $true)][string]$Uri,
        [object]$Body = $null,
        [string]$ContentType = "application/json; charset=utf-8"
    )

    $params = @{
        Uri     = $Uri
        Headers = $script:Headers
        Method  = $Method
    }

    if ($null -ne $Body) {
        $params.ContentType = $ContentType
        $params.Body = $Body
    }

    return Invoke-RestMethod @params
}

function Get-OriginInfo {
    $origin = Invoke-Git -Arguments @("remote", "get-url", "origin")
    if ($origin -notmatch "dev\.tellhowsoft\.com") {
        throw "origin remote is not a dev.tellhowsoft.com TFS repository: $origin"
    }

    $normalized = $origin.Trim()
    if ($normalized.EndsWith(".git")) {
        $normalized = $normalized.Substring(0, $normalized.Length - 4)
    }

    if ($normalized -notmatch "/DefaultCollection/([^/]+)/_git/([^/]+)$") {
        throw "Cannot parse TFS project/repository from origin: $origin"
    }

    return [pscustomobject]@{
        Origin     = $origin
        Project    = [Uri]::UnescapeDataString($Matches[1])
        Repository = [Uri]::UnescapeDataString($Matches[2])
    }
}

function Get-Repository {
    param(
        [Parameter(Mandatory = $true)][string]$Project,
        [Parameter(Mandatory = $true)][string]$RepositoryName
    )

    $reposUrl = "$TfsBaseUrl/$Project/_apis/git/repositories?api-version=2.0"
    $repos = Invoke-TfsRest -Method Get -Uri $reposUrl
    $repo = $repos.value | Where-Object { $_.name -eq $RepositoryName } | Select-Object -First 1
    if (-not $repo) {
        throw "Repository '$RepositoryName' was not found in project '$Project'."
    }
    return $repo
}

function Get-ActivePullRequest {
    param(
        [Parameter(Mandatory = $true)][string]$Project,
        [Parameter(Mandatory = $true)][string]$RepositoryId,
        [Parameter(Mandatory = $true)][string]$SourceRefName,
        [Parameter(Mandatory = $true)][string]$TargetRefName
    )

    $sourceQuery = [Uri]::EscapeDataString($SourceRefName)
    $targetQuery = [Uri]::EscapeDataString($TargetRefName)
    $url = "$TfsBaseUrl/$Project/_apis/git/repositories/$RepositoryId/pullRequests?searchCriteria.status=active&searchCriteria.sourceRefName=$sourceQuery&searchCriteria.targetRefName=$targetQuery&api-version=2.0"
    $prs = Invoke-TfsRest -Method Get -Uri $url
    return @($prs.value | Select-Object -First 1)
}

function Save-PullRequest {
    param(
        [Parameter(Mandatory = $true)][string]$Project,
        [Parameter(Mandatory = $true)][string]$RepositoryId,
        [Parameter(Mandatory = $true)][string]$SourceRefName,
        [Parameter(Mandatory = $true)][string]$TargetRefName
    )

    $active = @(Get-ActivePullRequest -Project $Project -RepositoryId $RepositoryId -SourceRefName $SourceRefName -TargetRefName $TargetRefName)
    if ($active.Count -gt 0) {
        $body = @{
            title       = $Title
            description = $Description
        } | ConvertTo-Json -Depth 8

        $patchUrl = "$TfsBaseUrl/$Project/_apis/git/repositories/$RepositoryId/pullRequests/$($active[0].pullRequestId)?api-version=2.0"
        return Invoke-TfsRest -Method Patch -Uri $patchUrl -Body $body
    }

    $body = @{
        sourceRefName = $SourceRefName
        targetRefName = $TargetRefName
        title         = $Title
        description   = $Description
    } | ConvertTo-Json -Depth 8

    $createUrl = "$TfsBaseUrl/$Project/_apis/git/repositories/$RepositoryId/pullRequests?api-version=2.0"
    return Invoke-TfsRest -Method Post -Uri $createUrl -Body $body
}

function Ensure-WorkItemLink {
    param(
        [Parameter(Mandatory = $true)][string]$Project,
        [Parameter(Mandatory = $true)][string]$ProjectId,
        [Parameter(Mandatory = $true)][string]$RepositoryId,
        [Parameter(Mandatory = $true)][int]$PullRequestId,
        [Parameter(Mandatory = $true)][int]$WorkItemId
    )

    $workItemsUrl = "$TfsBaseUrl/$Project/_apis/git/repositories/$RepositoryId/pullRequests/$PullRequestId/workitems?api-version=2.0"
    $refs = Invoke-TfsRest -Method Get -Uri $workItemsUrl
    if (@($refs.value | Where-Object { $_.id -eq [string]$WorkItemId }).Count -gt 0) {
        return $true
    }

    $artifactUrl = "vstfs:///Git/PullRequestId/$ProjectId%2F$RepositoryId%2F$PullRequestId"
    $workItemUrl = "$TfsBaseUrl/_apis/wit/workitems/$WorkItemId`?`$expand=relations&api-version=2.0"
    $workItem = Invoke-TfsRest -Method Get -Uri $workItemUrl
    $relations = @()
    if ($workItem.PSObject.Properties.Name -contains "relations") {
        $relations = @($workItem.relations)
    }
    $existing = @($relations | Where-Object { $_.url -eq $artifactUrl })
    if ($existing.Count -gt 0) {
        return $true
    }

    $patchObject = @{
        op    = "add"
        path  = "/relations/-"
        value = @{
            rel        = "ArtifactLink"
            url        = $artifactUrl
            attributes = @{
                name = "Pull Request"
            }
        }
    }
    $patch = "[" + ($patchObject | ConvertTo-Json -Depth 12) + "]"
    $updateUrl = "$TfsBaseUrl/_apis/wit/workitems/$WorkItemId`?api-version=2.0"
    [void](Invoke-TfsRest -Method Patch -Uri $updateUrl -Body $patch -ContentType "application/json-patch+json")
    return $true
}

function Enable-PullRequestAutoComplete {
    param(
        [Parameter(Mandatory = $true)][string]$Project,
        [Parameter(Mandatory = $true)][string]$RepositoryId,
        [Parameter(Mandatory = $true)][object]$PullRequest
    )

    if (-not ($PullRequest.PSObject.Properties.Name -contains "createdBy") -or
        -not ($PullRequest.createdBy.PSObject.Properties.Name -contains "id") -or
        [string]::IsNullOrWhiteSpace($PullRequest.createdBy.id)) {
        throw "Cannot enable auto-complete because the PR response does not include createdBy.id."
    }

    $body = @{
        autoCompleteSetBy = @{
            id = $PullRequest.createdBy.id
        }
        completionOptions = @{
            deleteSourceBranch = $DeleteSourceBranch
        }
    } | ConvertTo-Json -Depth 10

    $url = "$TfsBaseUrl/$Project/_apis/git/repositories/$RepositoryId/pullRequests/$($PullRequest.pullRequestId)?api-version=2.0"
    $updated = Invoke-TfsRest -Method Patch -Uri $url -Body $body
    if (-not ($updated.PSObject.Properties.Name -contains "autoCompleteSetBy") -or $null -eq $updated.autoCompleteSetBy) {
        throw "TFS accepted the PR update but autoCompleteSetBy was not returned."
    }

    return $updated
}

if (-not (Test-Path -LiteralPath $RepoPath)) {
    throw "RepoPath does not exist: $RepoPath"
}

$script:Headers = New-TfsHeaders
$originInfo = Get-OriginInfo
$repo = Get-Repository -Project $originInfo.Project -RepositoryName $originInfo.Repository

if ([string]::IsNullOrWhiteSpace($Description)) {
    $Description = "Source branch: $SourceBranch`nTarget branch: $TargetBranch`n`n$Title"
}

$sourceRef = "refs/heads/$SourceBranch"
$targetRef = "refs/heads/$TargetBranch"
$pr = Save-PullRequest -Project $originInfo.Project -RepositoryId $repo.id -SourceRefName $sourceRef -TargetRefName $targetRef

$autoCompleteEnabled = $false
if ($SetAutoComplete) {
    $pr = Enable-PullRequestAutoComplete -Project $originInfo.Project -RepositoryId $repo.id -PullRequest $pr
    $autoCompleteEnabled = $true
}

$linked = $false
if ($WorkItemId -gt 0) {
    $linked = Ensure-WorkItemLink -Project $originInfo.Project -ProjectId $repo.project.id -RepositoryId $repo.id -PullRequestId $pr.pullRequestId -WorkItemId $WorkItemId
}

$webUrl = "$TfsBaseUrl/$($originInfo.Project)/_git/$($originInfo.Repository)/pullrequest/$($pr.pullRequestId)"
[pscustomobject]@{
    PullRequestId = $pr.pullRequestId
    Status        = $pr.status
    Title         = $pr.title
    SourceBranch  = $SourceBranch
    TargetBranch  = $TargetBranch
    Project       = $originInfo.Project
    Repository    = $originInfo.Repository
    WorkItemId    = $(if ($WorkItemId -gt 0) { $WorkItemId } else { $null })
    WorkItemLinked = $linked
    AutoCompleteEnabled = $autoCompleteEnabled
    DeleteSourceBranch = $DeleteSourceBranch
    WebUrl        = $webUrl
    ApiUrl        = $pr.url
} | ConvertTo-Json -Depth 8
