# TFS API Notes

## Authentication

Read `TFS_PAT` from the environment and use Basic auth with an empty username:

```text
Authorization: Basic base64(":<PAT>")
```

Do not print the token.

## Repository Discovery

The remote URL usually looks like:

```text
http://dev.tellhowsoft.com/DefaultCollection/<Project>/_git/<RepoName>
```

Use the project and repo name to get the repository id:

```text
GET /DefaultCollection/<Project>/_apis/git/repositories?api-version=2.0
```

## Create Pull Request

```text
POST /DefaultCollection/<Project>/_apis/git/repositories/<repoId>/pullRequests?api-version=2.0
```

Body:

```json
{
  "sourceRefName": "refs/heads/feature/1551572-yangtao",
  "targetRefName": "refs/heads/dev",
  "title": "feat(#1551572):...",
  "description": "..."
}
```

## Check PR Work Items

```text
GET /DefaultCollection/<Project>/_apis/git/repositories/<repoId>/pullRequests/<prId>/workitems?api-version=2.0
```

If the response does not include the work item id, add a work item relation.

## Saved Query For Commit Work Items

Before asking the user for a work item id during PR submission, execute the saved query:

```text
GET /DefaultCollection/XiNanArea-New/_apis/wit/queries/2fd5f73e-f5bc-4423-b289-7bcb1fb58977?$expand=all&api-version=2.0
GET /DefaultCollection/XiNanArea-New/_apis/wit/wiql/2fd5f73e-f5bc-4423-b289-7bcb1fb58977?api-version=2.0
```

The query is `queryType=oneHop`, so results may appear in `workItemRelations` instead of only `workItems`. Collect unique `source.id` and `target.id`, batch-fetch their details, and select the related `用户情景`. Ask the user only when no relevant story is present.

## Enable PR Auto-Complete

Patch the pull request after creation or reuse:

```text
PATCH /DefaultCollection/<Project>/_apis/git/repositories/<repoId>/pullRequests/<pullRequestId>?api-version=2.0
```

Body:

```json
{
  "autoCompleteSetBy": {
    "id": "<createdBy.id>"
  },
  "completionOptions": {
    "deleteSourceBranch": true
  }
}
```

Use the PR creator identity from `createdBy.id`. If TFS rejects the patch, stop and report that auto-complete could not be enabled.

## Explicit Work Item PR Link

Use this ArtifactLink URL shape:

```text
vstfs:///Git/PullRequestId/<projectId>%2F<repoId>%2F<pullRequestId>
```

Patch the work item:

```json
[
  {
    "op": "add",
    "path": "/relations/-",
    "value": {
      "rel": "ArtifactLink",
      "url": "vstfs:///Git/PullRequestId/<projectId>%2F<repoId>%2F<pullRequestId>",
      "attributes": {
        "name": "Pull Request"
      }
    }
  }
]
```
