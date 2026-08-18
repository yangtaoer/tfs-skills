#!/usr/bin/env python3
"""Resolve TFS projects and local repositories into a requirement workspace."""

from __future__ import annotations

import argparse
import configparser
import json
import os
import re
import subprocess
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any
from urllib.parse import urlparse


BRACKET_RE = re.compile(r"【([^】]+)】")


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def norm_remote(value: str | None) -> str:
    if not value:
        return ""
    text = value.strip().rstrip("/")
    parsed = urlparse(text)
    if parsed.scheme and parsed.netloc:
        return f"{parsed.scheme.lower()}://{parsed.netloc.lower()}{parsed.path.rstrip('/')}"
    return text.lower()


def repo_name_from_remote(remote: str) -> str:
    path = urlparse(remote).path if "://" in remote else remote
    name = path.rstrip("/").split("/")[-1]
    if name.endswith(".git"):
        name = name[:-4]
    return name


def validate_catalog(catalog: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    names: set[str] = set()
    aliases: dict[str, str] = {}
    pipeline_ids: set[tuple[str, int]] = set()
    for project in catalog.get("projects", []):
        name = str(project.get("standardName", "")).strip()
        if not name:
            errors.append("project missing standardName")
            continue
        if name in names:
            errors.append(f"duplicate standardName: {name}")
        names.add(name)
        for alias in project.get("aliases", []) or []:
            alias = str(alias).strip()
            if not alias:
                continue
            if alias in aliases and aliases[alias] != name:
                errors.append(f"alias maps to multiple projects: {alias}")
            aliases[alias] = name
        for pipeline in project.get("pipelines", []) or []:
            tfs_project = str(pipeline.get("tfsProject") or "").strip()
            definition_id = pipeline.get("definitionId")
            if not tfs_project:
                errors.append(f"{name}: pipeline missing tfsProject")
            if not isinstance(definition_id, int) or definition_id <= 0:
                errors.append(f"{name}: pipeline has invalid definitionId: {definition_id}")
            elif (tfs_project, definition_id) in pipeline_ids:
                errors.append(f"duplicate pipeline definition: {tfs_project}/{definition_id}")
            else:
                pipeline_ids.add((tfs_project, definition_id))
            source_branch = str(pipeline.get("sourceBranch") or "")
            if not source_branch.startswith("refs/heads/"):
                errors.append(
                    f"{name}/{definition_id}: sourceBranch must start with refs/heads/: {source_branch}"
                )
            definition_url = str(pipeline.get("definitionUrl") or "")
            if f"definitionId={definition_id}" not in definition_url:
                errors.append(
                    f"{name}/{definition_id}: definitionUrl must contain matching definitionId"
                )
        for repo in project.get("repos", []) or []:
            remote = norm_remote(repo.get("remote"))
            if not repo.get("name"):
                errors.append(f"{name}: repo missing name")
            if not remote:
                errors.append(f"{name}: repo {repo.get('name', '<unknown>')} missing remote")
                continue
            branch = str(repo.get("targetBranch") or project.get("defaultTargetBranch") or "")
            if branch.startswith("origin/"):
                owner = f"{name}/{repo.get('name')}/{branch}/{repo.get('module', '')}"
                errors.append(f"{owner}: targetBranch must omit origin/: {branch}")
    return errors


def extract_bracket_names(title: str) -> list[str]:
    return [m.group(1).strip() for m in BRACKET_RE.finditer(title or "") if m.group(1).strip()]


def resolve_projects(catalog: dict[str, Any], title: str, text: str = "") -> tuple[list[dict[str, Any]], list[str]]:
    projects = catalog.get("projects", []) or []
    by_name = {p.get("standardName"): p for p in projects}
    matched: list[dict[str, Any]] = []
    notes: list[str] = []

    bracket_names = extract_bracket_names(title)
    for name in bracket_names:
        if name in by_name:
            matched.append(by_name[name])
        else:
            notes.append(f"unknown bracket project: {name}")

    if matched:
        return dedupe_projects(matched), notes

    haystack = f"{title}\n{text}"
    scored: list[tuple[int, dict[str, Any], str]] = []
    for project in projects:
        score = 0
        reason_parts: list[str] = []
        name = project.get("standardName", "")
        if name and name in haystack:
            score += 100
            reason_parts.append("standardName")
        for alias in project.get("aliases", []) or []:
            if alias and alias in haystack:
                score += 50
                reason_parts.append(f"alias:{alias}")
        for keyword in project.get("keywords", []) or []:
            if keyword and keyword in haystack:
                score += 10
                reason_parts.append(f"keyword:{keyword}")
        if score:
            scored.append((score, project, ",".join(reason_parts)))

    scored.sort(key=lambda item: item[0], reverse=True)
    if scored:
        top_score = scored[0][0]
        matched = [p for score, p, _ in scored if score == top_score or score >= 50]
        notes.extend([f"matched {p.get('standardName')} by {reason}" for _, p, reason in scored[:5]])
    return dedupe_projects(matched), notes


def dedupe_projects(projects: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    result: list[dict[str, Any]] = []
    for project in projects:
        name = project.get("standardName")
        if name and name not in seen:
            seen.add(name)
            result.append(project)
    return result


def read_origin(repo_path: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "-C", str(repo_path), "remote", "get-url", "origin"],
            text=True,
            capture_output=True,
            timeout=5,
            check=False,
        )
        if result.returncode == 0:
            return result.stdout.strip()
    except Exception:
        pass

    git_config = repo_path / ".git" / "config"
    if git_config.exists():
        parser = configparser.ConfigParser()
        parser.read(git_config, encoding="utf-8")
        section = 'remote "origin"'
        if parser.has_section(section):
            return parser.get(section, "url", fallback="").strip()
    return ""


def scan_repos(roots: list[Path]) -> list[dict[str, str]]:
    repos: list[dict[str, str]] = []
    seen: set[str] = set()
    for root in roots:
        if not root.exists():
            continue
        candidates = [root] if (root / ".git").exists() else []
        candidates.extend(p.parent for p in root.rglob(".git") if p.name == ".git")
        for repo_path in candidates:
            key = str(repo_path.resolve()).lower()
            if key in seen:
                continue
            seen.add(key)
            origin = read_origin(repo_path)
            if not origin:
                continue
            repos.append(
                {
                    "path": str(repo_path),
                    "remote": origin,
                    "remoteNorm": norm_remote(origin),
                    "name": repo_path.name,
                    "remoteName": repo_name_from_remote(origin),
                }
            )
    return repos


def match_local_repo(repo: dict[str, Any], local_repos: list[dict[str, str]]) -> tuple[str, str, str]:
    expected_remote = norm_remote(repo.get("remote"))
    expected_name = str(repo.get("name") or repo_name_from_remote(expected_remote)).lower()
    for local in local_repos:
        if expected_remote and local["remoteNorm"] == expected_remote:
            return local["path"], "found", "remote"
    for local in local_repos:
        if local["name"].lower() == expected_name or local["remoteName"].lower() == expected_name:
            if expected_remote and local["remoteNorm"] != expected_remote:
                return local["path"], "remote-mismatch", "name"
            return local["path"], "found", "name"
    return "", "missing", "none"


def build_workspace(args: argparse.Namespace) -> dict[str, Any]:
    catalog = load_json(Path(args.catalog))
    projects, notes = resolve_projects(catalog, args.title or "", args.text or "")
    roots = [Path(p) for p in args.repo_root]
    local_repos = scan_repos(roots)
    alias = args.alias or os.environ.get("TFS_USER_ALIAS") or "user"
    feature_branch = f"feature/{args.work_item_id}-{alias}"
    now = datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds")
    workspace: dict[str, Any] = {
        "version": 1,
        "createdAt": now,
        "workItemId": int(args.work_item_id) if str(args.work_item_id).isdigit() else args.work_item_id,
        "title": args.title,
        "projects": [p.get("standardName") for p in projects],
        "featureBranch": feature_branch,
        "notes": notes,
        "repos": [],
        "pipelines": [],
    }
    seen_pipelines: set[tuple[str, int]] = set()
    seen_targets: set[tuple[str, str, str]] = set()
    for project in projects:
        for pipeline in project.get("pipelines", []) or []:
            pipeline_key = (
                str(pipeline.get("tfsProject") or ""),
                int(pipeline.get("definitionId") or 0),
            )
            if pipeline_key in seen_pipelines:
                continue
            seen_pipelines.add(pipeline_key)
            workspace["pipelines"].append(
                {
                    "project": project.get("standardName"),
                    "purpose": pipeline.get("purpose", ""),
                    "definitionId": pipeline.get("definitionId"),
                    "name": pipeline.get("name", ""),
                    "definitionUrl": pipeline.get("definitionUrl", ""),
                    "folderPath": pipeline.get("folderPath", ""),
                    "tfsProject": pipeline.get("tfsProject", ""),
                    "repository": pipeline.get("repository", ""),
                    "sourceBranch": pipeline.get("sourceBranch", ""),
                    "buildProfile": pipeline.get("buildProfile", ""),
                    "artifactName": pipeline.get("artifactName", ""),
                }
            )
        project_branch = project.get("defaultTargetBranch") or args.target_branch or ""
        for repo in project.get("repos", []) or []:
            remote = repo.get("remote", "")
            remote_norm = norm_remote(remote)
            target_branch = repo.get("targetBranch") or project_branch
            target_key = (remote_norm, str(target_branch), str(repo.get("module", "")))
            if target_key in seen_targets:
                continue
            seen_targets.add(target_key)
            local_path, status, reason = match_local_repo(repo, local_repos)
            workspace["repos"].append(
                {
                    "project": project.get("standardName"),
                    "name": repo.get("name") or repo_name_from_remote(remote),
                    "role": repo.get("role", ""),
                    "module": repo.get("module", ""),
                    "codeArea": repo.get("codeArea", ""),
                    "description": repo.get("description", ""),
                    "remote": remote,
                    "targetBranch": target_branch,
                    "localPath": local_path,
                    "matchStatus": status,
                    "matchReason": reason,
                }
            )
    return workspace


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", required=True, help="Path to project-catalog.json")
    parser.add_argument("--validate", action="store_true", help="Validate catalog and exit")
    parser.add_argument("--work-item-id", help="TFS work item id")
    parser.add_argument("--title", default="", help="TFS story title or draft title")
    parser.add_argument("--text", default="", help="Additional story description text for matching")
    parser.add_argument("--repo-root", action="append", default=[], help="Root directory to scan for git repositories")
    parser.add_argument("--target-branch", default="", help="Fallback target branch")
    parser.add_argument("--alias", default="", help="TFS alias used for feature branch naming")
    parser.add_argument("--out", default="", help="Output workspace JSON path")
    args = parser.parse_args()

    catalog_path = Path(args.catalog)
    catalog = load_json(catalog_path)
    errors = validate_catalog(catalog)
    if args.validate:
        if errors:
            for error in errors:
                print(f"ERROR: {error}")
            return 1
        print("Catalog OK")
        return 0
    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1
    if not args.work_item_id:
        parser.error("--work-item-id is required unless --validate is used")
    workspace = build_workspace(args)
    data = json.dumps(workspace, ensure_ascii=False, indent=2)
    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(data + "\n", encoding="utf-8")
        print(f"Wrote {out_path}")
    else:
        print(data)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
