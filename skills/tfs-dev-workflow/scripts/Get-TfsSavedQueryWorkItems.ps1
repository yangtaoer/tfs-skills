[CmdletBinding()]
param(
    [string]$QueryUrl = $env:TFS_USER_STORY_QUERY_URL,

    [int]$MaxItems = 100,

    [string]$WorkItemType = "用户情景",

    [string]$State = "已评审",

    [string]$TfsBaseUrl = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function New-TfsHeaders {
    if (-not $env:TFS_PAT) {
        throw "TFS_PAT is not set."
    }

    $token = [Convert]::ToBase64String([Text.Encoding]::ASCII.GetBytes(":" + $env:TFS_PAT))
    return @{ Authorization = "Basic $token" }
}

function Get-FieldValue {
    param(
        [Parameter(Mandatory = $true)][object]$Fields,
        [Parameter(Mandatory = $true)][string]$Name
    )

    if ($Fields.PSObject.Properties.Name -contains $Name) {
        return $Fields.PSObject.Properties[$Name].Value
    }
    return $null
}

if ([string]::IsNullOrWhiteSpace($QueryUrl)) {
    throw "QueryUrl is required. Provide -QueryUrl or set TFS_USER_STORY_QUERY_URL."
}

$uri = [Uri]$QueryUrl
$absolute = $uri.AbsoluteUri.TrimEnd("/")
if ($absolute -notmatch "^(?<base>https?://[^/]+/DefaultCollection)/(?<project>[^/]+)/_queries/query/(?<queryId>[0-9a-fA-F-]+)") {
    throw "Unsupported TFS saved query URL: $QueryUrl"
}

$base = if ([string]::IsNullOrWhiteSpace($TfsBaseUrl)) { $Matches.base } else { $TfsBaseUrl.TrimEnd("/") }
$project = [Uri]::UnescapeDataString($Matches.project)
$queryId = $Matches.queryId
$headers = New-TfsHeaders

$wiqlUrl = "$base/$project/_apis/wit/wiql/$queryId`?api-version=2.0"
$queryResult = Invoke-RestMethod -Uri $wiqlUrl -Headers $headers -Method Get

$ids = New-Object System.Collections.Generic.List[int]
if ($queryResult.PSObject.Properties.Name -contains "workItems") {
    foreach ($item in @($queryResult.workItems)) {
        if ($item.id -and -not $ids.Contains([int]$item.id)) {
            $ids.Add([int]$item.id) | Out-Null
        }
    }
}

if ($queryResult.PSObject.Properties.Name -contains "workItemRelations") {
    foreach ($relation in @($queryResult.workItemRelations)) {
        foreach ($endpointName in @("source", "target")) {
            if (($relation.PSObject.Properties.Name -contains $endpointName) -and
                $null -ne $relation.$endpointName -and
                ($relation.$endpointName.PSObject.Properties.Name -contains "id")) {
                $id = [int]$relation.$endpointName.id
                if (-not $ids.Contains($id)) {
                    $ids.Add($id) | Out-Null
                }
            }
        }
    }
}

if ($ids.Count -eq 0) {
    [pscustomobject]@{
        QueryUrl = $QueryUrl
        Count    = 0
        Items    = @()
    } | ConvertTo-Json -Depth 8
    exit 0
}

$selectedIds = @($ids | Select-Object -First $MaxItems)
$fields = @(
    "System.Id",
    "System.WorkItemType",
    "System.Title",
    "System.State",
    "System.AreaPath",
    "System.IterationPath",
    "System.AssignedTo",
    "System.Description",
    "Microsoft.VSTS.Common.AcceptanceCriteria"
) -join ","

$allItems = New-Object System.Collections.Generic.List[object]
for ($i = 0; $i -lt $selectedIds.Count; $i += 200) {
    $chunk = @($selectedIds[$i..([Math]::Min($i + 199, $selectedIds.Count - 1))])
    $idsQuery = ($chunk -join ",")
    $detailsUrl = "$base/_apis/wit/workitems?ids=$idsQuery&fields=$fields&api-version=2.0"
    $details = Invoke-RestMethod -Uri $detailsUrl -Headers $headers -Method Get
    foreach ($workItem in @($details.value)) {
        $f = $workItem.fields
        $itemObject = [pscustomobject]@{
            Id                 = $workItem.id
            WorkItemType       = Get-FieldValue -Fields $f -Name "System.WorkItemType"
            Title              = Get-FieldValue -Fields $f -Name "System.Title"
            State              = Get-FieldValue -Fields $f -Name "System.State"
            AreaPath           = Get-FieldValue -Fields $f -Name "System.AreaPath"
            IterationPath      = Get-FieldValue -Fields $f -Name "System.IterationPath"
            AssignedTo         = Get-FieldValue -Fields $f -Name "System.AssignedTo"
            Description        = Get-FieldValue -Fields $f -Name "System.Description"
            AcceptanceCriteria = Get-FieldValue -Fields $f -Name "Microsoft.VSTS.Common.AcceptanceCriteria"
        }

        $typeMatches = [string]::IsNullOrWhiteSpace($WorkItemType) -or $itemObject.WorkItemType -eq $WorkItemType
        $stateMatches = [string]::IsNullOrWhiteSpace($State) -or $itemObject.State -eq $State
        if ($typeMatches -and $stateMatches) {
            $allItems.Add($itemObject) | Out-Null
        }
    }
}

$itemsArray = @($allItems.ToArray())
[pscustomobject]@{
    QueryUrl = $QueryUrl
    Project  = $project
    QueryId  = $queryId
    WorkItemTypeFilter = $WorkItemType
    StateFilter = $State
    Count    = $itemsArray.Count
    Items    = $itemsArray
} | ConvertTo-Json -Depth 10
