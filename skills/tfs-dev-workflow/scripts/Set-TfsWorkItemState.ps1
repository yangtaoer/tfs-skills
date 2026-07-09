[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [int]$WorkItemId,

    [string]$State = "已解决",

    [string]$TfsBaseUrl = $env:TFS_BASE_URL
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

$headers = New-TfsHeaders
if ([string]::IsNullOrWhiteSpace($TfsBaseUrl)) {
    $TfsBaseUrl = "http://dev.tellhowsoft.com/DefaultCollection"
}

$patchObject = @{
    op    = "replace"
    path  = "/fields/System.State"
    value = $State
}
$patch = "[" + ($patchObject | ConvertTo-Json -Depth 8) + "]"
$url = "$TfsBaseUrl/_apis/wit/workitems/$WorkItemId`?api-version=2.0"
$updated = Invoke-RestMethod -Uri $url -Headers $headers -Method Patch -ContentType "application/json-patch+json" -Body $patch

[pscustomobject]@{
    Id    = $updated.id
    Title = $updated.fields.'System.Title'
    State = $updated.fields.'System.State'
} | ConvertTo-Json -Depth 5
