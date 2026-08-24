---
name: tfs-run-pipeline
description: Run an existing TFS/Azure DevOps Server delivery pipeline or staged pipeline workflow, wait for required dependencies and builds to finish, verify published artifacts, and return the build results and artifact-page links. Use when the user asks to run, build, package, deliver, or obtain delivery artifacts for a project whose pipelines are registered in tfs-project-catalog.
---

# TFS Run Pipeline

## Overview

Resolve a project's delivery workflow from `../tfs-project-catalog/references/project-catalog.seed.json`. A workflow may contain one delivery pipeline or multiple ordered stages. Queue every pipeline in the current stage, wait for all of them, and only then start the next stage. Return the final delivery artifact pages. Prefer the bundled script because it uses the TFS Build API deterministically and prevents accidental duplicate builds.

## Safety Rules

1. Treat requests to inspect, find, list, or explain a pipeline as read-only. Do not queue a build.
2. Treat an explicit request to run, build, package, or deliver the resolved project as authorization to queue its complete cataloged workflow once.
3. Before queueing, report the standard project name and every stage's definition names, IDs, source branches, and definition URLs.
4. Do not pass a PAT on the command line or store it in the skill. Read `TFS_PAT` from the environment.
5. If the same definition and source branch already has an active build, wait for that build instead of queueing another. Use `--force-new` only when the user explicitly requests an additional build.
6. Queue all pipelines in one stage before waiting, so independent pipelines in that stage can run concurrently.
7. Do not queue a later stage unless every pipeline in the preceding stage finished with `succeeded`.
8. Do not report delivery success unless every workflow build succeeded and every `purpose: delivery` pipeline has its expected published artifact. Dependency pipelines may legitimately have no published build artifact.

## Workflow

### 0. List supported projects

List every cataloged pipeline workflow without contacting TFS:

```powershell
python scripts/run_tfs_pipeline.py --list-projects
```

### 1. Resolve and check the workflow

Use the standard name or an exact alias from the project catalog:

```powershell
python scripts/run_tfs_pipeline.py --project-name "自贡检修计划智能编排系统" --check-definition
```

This read-only command validates every definition, repository, branch, Maven profile when present, and visible published-artifact task. If an artifact is published inside a TFS task group and cannot be seen in the definition, preflight reports `deferred-to-build-result`; the script still verifies the actual artifact after the build.

### 2. Queue and wait

After confirming the request authorizes a build, run:

```powershell
python scripts/run_tfs_pipeline.py --project-name "自贡检修计划智能编排系统" --confirm-run
```

The script must remain attached until the complete workflow finishes or the timeout is reached. It prints progress to stderr and a final JSON object to stdout. For 自贡检修计划智能编排系统 it performs:

1. Stage 1: queue `9479` (backend dependency) and `9480` (frontend dependency), then wait for both.
2. Stage 2, only after Stage 1 succeeds: queue `9180` (backend delivery) and `9181` (frontend delivery), then wait for both and verify each `drop` artifact.

### 3. Report the result

For a successful build, report:

- Standard project name.
- Pipeline names, definition IDs, and stages.
- Build number and build ID.
- Source branch.
- Final result.
- Build results URL.
- Backend and frontend published-artifacts page URLs when labeled by `deliverable`.
- Artifact names, normally `drop`.

For a failed, canceled, or artifact-less delivery build, report the results URL and the failure clearly. Do not start later stages after a failed dependency and do not present the artifacts URL as a successful delivery.

## Browser Fallback

Use the TFS web UI only when the Build API is unavailable but an authenticated browser session is available:

1. Open every `definitionUrl` in the lowest pending stage.
2. For each pipeline in that stage, select **运行管道**, verify the configured source branch, and submit exactly once.
3. Capture each `buildId` from its redirected build-results URL and wait for all builds in the stage to finish.
4. If any build did not succeed, stop and do not run the next stage.
5. Repeat for the next stage only after all earlier builds succeeded.
6. For each delivery build, open `.../_build/results?buildId=<buildId>&view=artifacts&pathAsName=false&type=publishedArtifacts` and verify the expected artifact.

Do not click **运行** when the user's request is read-only.

## Script Options

- Omit action flags to resolve locally without contacting TFS.
- Use `--list-projects` to list every standard project and its runnable pipeline stages.
- Use `--check-definition` for a live read-only check of the complete workflow. Combine it with `--definition-id` to inspect one definition.
- Use `--confirm-run` to authorize queueing and polling the complete workflow. Do not combine it with `--definition-id` for a multi-stage project.
- Use `--build-id <id> --definition-id <definitionId>` to resume one already queued build in a multi-pipeline project without queueing another.
- Use `--source-branch refs/heads/<branch>` only with a single selected definition and only when the user requests a branch override.
- Use `--force-new` only for an explicitly requested additional build.
- Use `--timeout-seconds` and `--poll-seconds` to adjust waiting behavior.
