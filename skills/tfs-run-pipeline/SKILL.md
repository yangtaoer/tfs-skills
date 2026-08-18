---
name: tfs-run-pipeline
description: Run an existing TFS/Azure DevOps Server build pipeline for delivery, wait for the build to finish, verify published artifacts, and return the build results and artifact-page links. Use when the user asks to run, build, package, deliver, or obtain delivery artifacts for a project whose pipeline is registered in tfs-project-catalog.
---

# TFS Run Pipeline

## Overview

Resolve a project's delivery pipeline from `../tfs-project-catalog/references/project-catalog.seed.json`, queue one build, wait for its terminal result, and return the published-artifact page. Prefer the bundled script because it uses the TFS Build API deterministically and prevents accidental duplicate builds.

## Safety Rules

1. Treat requests to inspect, find, list, or explain a pipeline as read-only. Do not queue a build.
2. Treat an explicit request to run, build, package, or deliver the resolved project as authorization to queue one build.
3. Before queueing, report the standard project name, definition name and ID, source branch, and definition URL.
4. Do not pass a PAT on the command line or store it in the skill. Read `TFS_PAT` from the environment.
5. If the same definition and source branch already has an active build, wait for that build instead of queueing another. Use `--force-new` only when the user explicitly requests an additional build.
6. Do not report delivery success unless the build result is `succeeded` and the expected published artifact exists.

## Workflow

### 0. List supported projects

List every cataloged delivery pipeline without contacting TFS:

```powershell
python scripts/run_tfs_pipeline.py --list-projects
```

### 1. Resolve and check the pipeline

Use the standard name or an exact alias from the project catalog:

```powershell
python scripts/run_tfs_pipeline.py --project-name "四川省调网络发令" --check-definition
```

If the project is unknown, has no delivery pipeline, or has multiple delivery pipelines, stop and ask the user to choose. Do not guess a definition ID.

### 2. Queue and wait

After confirming the request authorizes a build, run:

```powershell
python scripts/run_tfs_pipeline.py --project-name "四川省调网络发令" --confirm-run
```

The script must remain attached until the build completes or the timeout is reached. It prints progress to stderr and a final JSON object to stdout.

### 3. Report the result

For a successful build, report:

- Standard project name.
- Pipeline name and definition ID.
- Build number and build ID.
- Source branch.
- Final result.
- Build results URL.
- Published-artifacts page URL.
- Artifact names, normally `drop`.

For a failed, canceled, or artifact-less build, report the results URL and the failure clearly. Do not present the artifacts URL as a successful delivery.

## Browser Fallback

Use the TFS web UI only when the Build API is unavailable but an authenticated browser session is available:

1. Open the catalog's `definitionUrl`.
2. Select **运行管道** and verify the configured source branch.
3. Submit exactly once.
4. Capture `buildId` from the redirected build-results URL.
5. Wait until the build reaches a terminal state.
6. Open `.../_build/results?buildId=<buildId>&view=artifacts&pathAsName=false&type=publishedArtifacts` and verify the expected artifact.

Do not click **运行** when the user's request is read-only.

## Script Options

- Omit action flags to resolve locally without contacting TFS.
- Use `--list-projects` to list every standard project with a delivery pipeline.
- Use `--check-definition` for a live read-only definition check.
- Use `--confirm-run` to authorize queueing and polling.
- Use `--build-id <id>` to resume monitoring an already queued build without queueing another.
- Use `--source-branch refs/heads/<branch>` only when the user requests a branch override.
- Use `--force-new` only for an explicitly requested additional build.
- Use `--timeout-seconds` and `--poll-seconds` to adjust waiting behavior.
