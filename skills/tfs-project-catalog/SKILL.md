---
name: tfs-project-catalog
description: Use when a TFS requirement, user story title, project alias, repository name, Excel project list, or local repo mapping must be resolved to a standard project name, TFS Git repositories, and target/base branches.
---

# TFS Project Catalog

## Overview

Resolve project names before any TFS story intake or development workflow. Standard project names are authoritative and must be written in TFS user story titles with Chinese brackets: `【标准项目名】需求标题`.

The catalog is the source of truth for:

- Standard project names.
- Project aliases, such as `省调网络发令` and `四川省调` mapping to `四川省调网络发令系统`.
- Repositories involved in each project.
- Base branches for those repositories.
- Delivery pipeline definitions, source branches, and definition URLs when known.
- Optional keywords and roles for frontend/backend/service matching.

## Required Files

- Read `references/catalog-schema.md` before creating or changing a catalog.
- Read `references/excel-import-notes.md` when the user provides an Excel project list.
- Use `references/project-catalog.seed.json` as the current tracked seed catalog when resolving known network-command projects.
- Use `scripts/resolve_tfs_workspace.py --help` for deterministic matching, local repo scanning, and workspace JSON generation.

## Catalog Rules

1. Treat `standardName` as the only name allowed inside `【】`.
2. Treat aliases as input-only matching terms. Do not write aliases into TFS story titles.
3. If a title already contains `【...】`, verify each bracketed value exists as a `standardName`.
4. If the input mentions aliases for multiple projects, keep all matched projects and require confirmation before creating or updating TFS work items.
5. If no project can be resolved, stop and ask the user to choose a standard project. Do not invent a project.
6. If two projects match with similar confidence, show both with aliases/repositories and ask the user to choose.
7. Never store PATs or credentials in the catalog.

## Unknown Projects

When story intake mentions a project that is not in the catalog, ask the user for:

- Standard project name to write inside `【】`.
- Known aliases.
- Involved repositories.
- Remote URL or code area + repo name.
- Base branch for each repository.
- Product name if known; otherwise use `临时项目交付`.

Proceed with the story only after the standard project name is confirmed. If repository details are incomplete, create the story but mark the project catalog as needing follow-up before workspace preparation.

## Matching Priority

Use this order:

1. Explicit bracketed standard names in the title, such as `【四川省调网络发令系统】`.
2. User explicitly named project or repository in the current request.
3. Alias match from the catalog.
4. Keyword match from the catalog.
5. Repository remote/name match from local repo scan.

## Local Paths

The GitHub-tracked catalog may contain repository remote URLs and default base branches. It may contain local path hints only if the user intentionally wants to publish them.

Prefer local-only files for machine-specific paths:

- `%USERPROFILE%\.codex\tfs-repo-index.local.json`
- `%USERPROFILE%\.codex\tfs-workspaces\<workItemId>\workspace.json`

## Output Contract

When resolving a project, report:

- Standard project name.
- Matched input term, such as alias or bracket value.
- Repositories, role, remote URL, and target branch.
- Delivery pipelines, including purpose, definition ID, definition URL, and source branch.
- Whether each repo was found locally.
- Ambiguities that require user confirmation.

## Handoff

- Use `tfs-story-intake` after resolving the project for user story creation.
- Use `tfs-requirement-workspace` after a work item exists and local repositories must be prepared.
