#!/usr/bin/env python3
"""Cross-platform helpers for the TFS development workflow."""
import argparse
import base64
import json
import os
import subprocess
import sys
import urllib.parse
import urllib.request


DEFAULT_BASE_URL = "http://dev.tellhowsoft.com/DefaultCollection"
DEFAULT_REMOTE_HOST = "dev.tellhowsoft.com"


def env_default(name, fallback=""):
    return os.environ.get(name, fallback)


def tfs_headers(content_type=None):
    pat = os.environ.get("TFS_PAT", "")
    if not pat:
        raise SystemExit("TFS_PAT is not set.")
    token = base64.b64encode((":" + pat).encode("ascii")).decode("ascii")
    headers = {"Authorization": "Basic " + token}
    if content_type:
        headers["Content-Type"] = content_type
    return headers


def request_json(method, url, body=None, content_type="application/json; charset=utf-8"):
    data = None
    headers = tfs_headers(content_type if body is not None else None)
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8-sig")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8-sig", errors="replace")
        raise SystemExit(f"TFS {method} failed {exc.code}: {detail}") from exc
    if not raw:
        return {}
    return json.loads(raw)


def git(repo_path, *args):
    proc = subprocess.run(
        ["git", "-C", repo_path, *args],
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
    )
    if proc.returncode != 0:
        raise SystemExit(f"git {' '.join(args)} failed: {proc.stdout.strip()}")
    return proc.stdout.strip()


def parse_query_url(query_url):
    parsed = urllib.parse.urlparse(query_url)
    parts = [p for p in parsed.path.split("/") if p]
    try:
        default_index = parts.index("DefaultCollection")
        project = urllib.parse.unquote(parts[default_index + 1])
        query_index = parts.index("query")
        query_id = parts[query_index + 1]
    except (ValueError, IndexError) as exc:
        raise SystemExit(f"Unsupported TFS saved query URL: {query_url}") from exc
    base = f"{parsed.scheme}://{parsed.netloc}/DefaultCollection"
    return base, project, query_id


def field(fields, name):
    return fields.get(name)


def command_query(args):
    if not args.query_url:
        raise SystemExit("Query URL is required. Use --query-url or set TFS_USER_STORY_QUERY_URL.")
    parsed_base, project, query_id = parse_query_url(args.query_url)
    base_url = (args.tfs_base_url or parsed_base).rstrip("/")
    wiql_url = f"{base_url}/{urllib.parse.quote(project)}/_apis/wit/wiql/{query_id}?api-version=2.0"
    query_result = request_json("GET", wiql_url)

    ids = []
    for item in query_result.get("workItems", []):
        if item.get("id") and item["id"] not in ids:
            ids.append(item["id"])
    for relation in query_result.get("workItemRelations", []):
        for endpoint in ("source", "target"):
            item = relation.get(endpoint) or {}
            if item.get("id") and item["id"] not in ids:
                ids.append(item["id"])

    fields = ",".join([
        "System.Id",
        "System.WorkItemType",
        "System.Title",
        "System.State",
        "System.AreaPath",
        "System.IterationPath",
        "System.AssignedTo",
        "System.Description",
        "Microsoft.VSTS.Common.AcceptanceCriteria",
    ])
    items = []
    selected = ids[: args.max_items]
    for index in range(0, len(selected), 200):
        chunk = selected[index : index + 200]
        if not chunk:
            continue
        details_url = f"{base_url}/_apis/wit/workitems?ids={','.join(str(i) for i in chunk)}&fields={urllib.parse.quote(fields, safe=',.')}&api-version=2.0"
        details = request_json("GET", details_url)
        for work_item in details.get("value", []):
            fields_obj = work_item.get("fields", {})
            item = {
                "Id": work_item.get("id"),
                "WorkItemType": field(fields_obj, "System.WorkItemType"),
                "Title": field(fields_obj, "System.Title"),
                "State": field(fields_obj, "System.State"),
                "AreaPath": field(fields_obj, "System.AreaPath"),
                "IterationPath": field(fields_obj, "System.IterationPath"),
                "AssignedTo": field(fields_obj, "System.AssignedTo"),
                "Description": field(fields_obj, "System.Description"),
                "AcceptanceCriteria": field(fields_obj, "Microsoft.VSTS.Common.AcceptanceCriteria"),
            }
            type_ok = not args.work_item_type or item["WorkItemType"] == args.work_item_type
            state_ok = not args.state or item["State"] == args.state
            if type_ok and state_ok:
                items.append(item)

    print(json.dumps({
        "QueryUrl": args.query_url,
        "Project": project,
        "QueryId": query_id,
        "WorkItemTypeFilter": args.work_item_type,
        "StateFilter": args.state,
        "Count": len(items),
        "Items": items,
    }, ensure_ascii=False, indent=2))


def command_set_state(args):
    base_url = args.tfs_base_url.rstrip("/")
    patch = [{"op": "replace", "path": "/fields/System.State", "value": args.state}]
    url = f"{base_url}/_apis/wit/workitems/{args.work_item_id}?api-version=2.0"
    updated = request_json("PATCH", url, patch, "application/json-patch+json")
    fields_obj = updated.get("fields", {})
    print(json.dumps({
        "Id": updated.get("id"),
        "Title": fields_obj.get("System.Title"),
        "State": fields_obj.get("System.State"),
    }, ensure_ascii=False, indent=2))


def command_start_branch(args):
    repo_path = os.path.abspath(args.repo_path)
    if not os.path.isdir(repo_path):
        raise SystemExit(f"Repo path does not exist: {repo_path}")
    if not args.tfs_alias:
        raise SystemExit("TFS alias is required. Use --tfs-alias or set TFS_USER_ALIAS.")
    inside = git(repo_path, "rev-parse", "--is-inside-work-tree")
    if inside != "true":
        raise SystemExit(f"Repo path is not a git work tree: {repo_path}")
    origin = git(repo_path, "remote", "get-url", "origin")
    if args.remote_host not in origin:
        raise SystemExit(f"origin remote is not a {args.remote_host} repository: {origin}")
    status = git(repo_path, "status", "--short")
    if status:
        raise SystemExit("Working tree is not clean. Preserve or commit existing changes first.\n" + status)

    branch_name = f"feature/{args.work_item_id}-{args.tfs_alias}"
    git(repo_path, "fetch", "origin", args.target_branch)
    existing = git(repo_path, "branch", "--list", branch_name)
    if existing:
        git(repo_path, "switch", branch_name)
    else:
        git(repo_path, "switch", "-c", branch_name, f"origin/{args.target_branch}")
    print(json.dumps({
        "RepoPath": repo_path,
        "Branch": branch_name,
        "Base": f"origin/{args.target_branch}",
        "Origin": origin,
        "WorkItemId": args.work_item_id,
        "TfsAlias": args.tfs_alias,
    }, ensure_ascii=False, indent=2))


def main():
    parser = argparse.ArgumentParser(description="TFS development workflow helper")
    sub = parser.add_subparsers(dest="command", required=True)

    query = sub.add_parser("query", help="Query reviewed TFS user stories from a saved query")
    query.add_argument("--query-url", default=env_default("TFS_USER_STORY_QUERY_URL"))
    query.add_argument("--max-items", type=int, default=100)
    query.add_argument("--work-item-type", default="用户情景")
    query.add_argument("--state", default="已评审")
    query.add_argument("--tfs-base-url", default=env_default("TFS_BASE_URL"))
    query.set_defaults(func=command_query)

    set_state = sub.add_parser("set-state", help="Update a TFS work item state")
    set_state.add_argument("--work-item-id", type=int, required=True)
    set_state.add_argument("--state", default="已解决")
    set_state.add_argument("--tfs-base-url", default=env_default("TFS_BASE_URL", DEFAULT_BASE_URL))
    set_state.set_defaults(func=command_set_state)

    branch = sub.add_parser("start-branch", help="Create or switch to a feature branch from the target branch")
    branch.add_argument("--repo-path", required=True)
    branch.add_argument("--work-item-id", type=int, required=True)
    branch.add_argument("--tfs-alias", default=env_default("TFS_USER_ALIAS"))
    branch.add_argument("--target-branch", default=env_default("TFS_TARGET_BRANCH", "dev"))
    branch.add_argument("--remote-host", default=env_default("TFS_REPO_HOST", DEFAULT_REMOTE_HOST))
    branch.set_defaults(func=command_start_branch)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
