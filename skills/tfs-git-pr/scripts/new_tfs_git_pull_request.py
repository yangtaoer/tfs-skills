#!/usr/bin/env python3
"""Create or update a TFS Git pull request from any platform with Python 3."""
import argparse
import base64
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request


DEFAULT_BASE_URL = "http://dev.tellhowsoft.com/DefaultCollection"
DEFAULT_REMOTE_HOST = "dev.tellhowsoft.com"


def env_default(name, fallback=""):
    return os.environ.get(name, fallback)


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


def headers(content_type=None):
    pat = os.environ.get("TFS_PAT", "")
    if not pat:
        raise SystemExit("TFS_PAT is not set.")
    token = base64.b64encode((":" + pat).encode("ascii")).decode("ascii")
    result = {"Authorization": "Basic " + token}
    if content_type:
        result["Content-Type"] = content_type
    return result


def request_json(method, url, body=None, content_type="application/json; charset=utf-8"):
    data = None
    request_headers = headers(content_type if body is not None else None)
    if body is not None:
        data = json.dumps(body, ensure_ascii=False).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8-sig")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8-sig", errors="replace")
        raise SystemExit(f"TFS {method} failed {exc.code}: {detail}") from exc
    if not raw:
        return {}
    return json.loads(raw)


def parse_origin(repo_path, remote_host):
    origin = git(repo_path, "remote", "get-url", "origin")
    if remote_host not in origin:
        raise SystemExit(f"origin remote is not a {remote_host} TFS repository: {origin}")
    normalized = origin.strip()
    if normalized.endswith(".git"):
        normalized = normalized[:-4]
    match = re.search(r"/DefaultCollection/([^/]+)/_git/([^/]+)$", normalized)
    if not match:
        raise SystemExit(f"Cannot parse TFS project/repository from origin: {origin}")
    return {
        "Origin": origin,
        "Project": urllib.parse.unquote(match.group(1)),
        "Repository": urllib.parse.unquote(match.group(2)),
    }


def get_repository(base_url, project, repository_name):
    url = f"{base_url}/{urllib.parse.quote(project)}/_apis/git/repositories?api-version=2.0"
    repos = request_json("GET", url)
    for repo in repos.get("value", []):
        if repo.get("name") == repository_name:
            return repo
    raise SystemExit(f"Repository '{repository_name}' was not found in project '{project}'.")


def get_active_pr(base_url, project, repository_id, source_ref, target_ref):
    source = urllib.parse.quote(source_ref, safe="")
    target = urllib.parse.quote(target_ref, safe="")
    url = (
        f"{base_url}/{urllib.parse.quote(project)}/_apis/git/repositories/{repository_id}/pullRequests"
        f"?searchCriteria.status=active&searchCriteria.sourceRefName={source}"
        f"&searchCriteria.targetRefName={target}&api-version=2.0"
    )
    prs = request_json("GET", url)
    values = prs.get("value", [])
    return values[0] if values else None


def save_pr(base_url, project, repository_id, source_ref, target_ref, title, description):
    active = get_active_pr(base_url, project, repository_id, source_ref, target_ref)
    body = {"title": title, "description": description}
    if active:
        url = f"{base_url}/{urllib.parse.quote(project)}/_apis/git/repositories/{repository_id}/pullRequests/{active['pullRequestId']}?api-version=2.0"
        return request_json("PATCH", url, body)
    body.update({"sourceRefName": source_ref, "targetRefName": target_ref})
    url = f"{base_url}/{urllib.parse.quote(project)}/_apis/git/repositories/{repository_id}/pullRequests?api-version=2.0"
    return request_json("POST", url, body)


def enable_auto_complete(base_url, project, repository_id, pull_request, delete_source_branch):
    created_by = pull_request.get("createdBy") or {}
    creator_id = created_by.get("id")
    if not creator_id:
        raise SystemExit("Cannot enable auto-complete because the PR response does not include createdBy.id.")
    body = {
        "autoCompleteSetBy": {"id": creator_id},
        "completionOptions": {"deleteSourceBranch": delete_source_branch},
    }
    url = f"{base_url}/{urllib.parse.quote(project)}/_apis/git/repositories/{repository_id}/pullRequests/{pull_request['pullRequestId']}?api-version=2.0"
    updated = request_json("PATCH", url, body)
    if not updated.get("autoCompleteSetBy"):
        raise SystemExit("TFS accepted the PR update but autoCompleteSetBy was not returned.")
    return updated


def ensure_work_item_link(base_url, project, project_id, repository_id, pull_request_id, work_item_id):
    url = f"{base_url}/{urllib.parse.quote(project)}/_apis/git/repositories/{repository_id}/pullRequests/{pull_request_id}/workitems?api-version=2.0"
    refs = request_json("GET", url)
    if any(str(item.get("id")) == str(work_item_id) for item in refs.get("value", [])):
        return True

    artifact_url = f"vstfs:///Git/PullRequestId/{project_id}%2F{repository_id}%2F{pull_request_id}"
    work_item_url = f"{base_url}/_apis/wit/workitems/{work_item_id}?$expand=relations&api-version=2.0"
    work_item = request_json("GET", work_item_url)
    for relation in work_item.get("relations", []):
        if relation.get("url") == artifact_url:
            return True

    patch = [{
        "op": "add",
        "path": "/relations/-",
        "value": {
            "rel": "ArtifactLink",
            "url": artifact_url,
            "attributes": {"name": "Pull Request"},
        },
    }]
    update_url = f"{base_url}/_apis/wit/workitems/{work_item_id}?api-version=2.0"
    request_json("PATCH", update_url, patch, "application/json-patch+json")
    return True


def main():
    parser = argparse.ArgumentParser(description="Create or update a TFS Git pull request")
    parser.add_argument("--repo-path", required=True)
    parser.add_argument("--source-branch", required=True)
    parser.add_argument("--target-branch", default=env_default("TFS_TARGET_BRANCH", "dev"))
    parser.add_argument("--title", required=True)
    parser.add_argument("--description", default="")
    parser.add_argument("--work-item-id", type=int, default=0)
    parser.add_argument("--tfs-base-url", default=env_default("TFS_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--remote-host", default=env_default("TFS_REPO_HOST", DEFAULT_REMOTE_HOST))
    parser.add_argument("--no-auto-complete", action="store_true")
    parser.add_argument("--keep-source-branch", action="store_true")
    args = parser.parse_args()

    repo_path = os.path.abspath(args.repo_path)
    if not os.path.isdir(repo_path):
        raise SystemExit(f"Repo path does not exist: {repo_path}")

    base_url = args.tfs_base_url.rstrip("/")
    origin_info = parse_origin(repo_path, args.remote_host)
    repo = get_repository(base_url, origin_info["Project"], origin_info["Repository"])
    description = args.description or f"Source branch: {args.source_branch}\nTarget branch: {args.target_branch}\n\n{args.title}"
    source_ref = "refs/heads/" + args.source_branch
    target_ref = "refs/heads/" + args.target_branch
    pr = save_pr(base_url, origin_info["Project"], repo["id"], source_ref, target_ref, args.title, description)

    auto_complete_enabled = False
    delete_source_branch = not args.keep_source_branch
    if not args.no_auto_complete:
        pr = enable_auto_complete(base_url, origin_info["Project"], repo["id"], pr, delete_source_branch)
        auto_complete_enabled = True

    linked = False
    if args.work_item_id > 0:
        linked = ensure_work_item_link(
            base_url,
            origin_info["Project"],
            repo["project"]["id"],
            repo["id"],
            pr["pullRequestId"],
            args.work_item_id,
        )

    web_url = f"{base_url}/{origin_info['Project']}/_git/{origin_info['Repository']}/pullrequest/{pr['pullRequestId']}"
    print(json.dumps({
        "PullRequestId": pr.get("pullRequestId"),
        "Status": pr.get("status"),
        "Title": pr.get("title"),
        "SourceBranch": args.source_branch,
        "TargetBranch": args.target_branch,
        "Project": origin_info["Project"],
        "Repository": origin_info["Repository"],
        "WorkItemId": args.work_item_id if args.work_item_id > 0 else None,
        "WorkItemLinked": linked,
        "AutoCompleteEnabled": auto_complete_enabled,
        "DeleteSourceBranch": delete_source_branch,
        "WebUrl": web_url,
        "ApiUrl": pr.get("url"),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
