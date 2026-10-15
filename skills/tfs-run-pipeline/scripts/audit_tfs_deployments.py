#!/usr/bin/env python3
"""Read-only discovery of classic Releases linked to cataloged Build definitions.

Only allowlisted deployment metadata is returned; service connection credentials,
variables, and arbitrary inline script bodies are never exported.
"""

from __future__ import annotations

import argparse
import json
import os
import re
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlencode, urlparse

from run_tfs_pipeline import DEFAULT_BASE_URL, TfsBuildClient, default_catalog_path


def audit_pipeline(project_name: str, pipeline: dict, base_url: str) -> dict:
    team_project = pipeline["tfsProject"]
    client = TfsBuildClient(base_url, team_project, os.environ["TFS_PAT"])

    def get(area: str, suffix: str, **query):
        query.setdefault("api-version", "4.1-preview.3")
        url = (
            f"{base_url.rstrip('/')}/{quote(team_project, safe='')}/_apis/"
            f"{area}/{suffix}?{urlencode(query)}"
        )
        return client.request_json("GET", url)

    definition_id = int(pipeline["definitionId"])
    build = client.get_definition(definition_id)
    project_id = build["project"]["id"]
    definitions = get(
        "release", "definitions", artifactType="Build",
        artifactSourceId=f"{project_id}:{definition_id}", **{"$top": 1000},
    )
    releases = []
    for summary in definitions.get("value", []):
        release = get("release", f"definitions/{summary['id']}")
        # Verify the exact source; do not rely on names or server-side filtering alone.
        sources = [
            a for a in release.get("artifacts", [])
            if a.get("type") == "Build"
            and str(a.get("definitionReference", {}).get("definition", {}).get("id"))
            == str(definition_id)
            and a.get("definitionReference", {}).get("project", {}).get("id") == project_id
        ]
        if not sources:
            continue
        aliases = {a["alias"] for a in sources}
        triggers = [
            t for t in release.get("triggers", [])
            if t.get("triggerType") == "artifactSource" and t.get("artifactAlias") in aliases
        ]
        environments = []
        for env in release.get("environments", []):
            targets = {}
            task_groups = []
            for phase in env.get("deployPhases", []):
                for task in phase.get("workflowTasks", []):
                    if not task.get("enabled", True):
                        continue
                    if task.get("definitionType") == "metaTask":
                        task_groups.append(task.get("taskId"))
                    inputs = task.get("inputs", {})
                    endpoint_id = inputs.get("sshEndpoint")
                    if not endpoint_id:
                        continue
                    if endpoint_id not in targets:
                        endpoint = get(
                            "serviceendpoint", f"endpoints/{endpoint_id}",
                            **{"api-version": "4.1-preview.1"},
                        )
                        url = endpoint.get("url") or ""
                        host = urlparse(url).hostname
                        if not host:
                            match = re.search(r"(?<![\d.])(?:\d{1,3}\.){3}\d{1,3}(?![\d.])", endpoint.get("name", ""))
                            host = match.group() if match else None
                        targets[endpoint_id] = {
                            "endpointId": endpoint_id, "endpointName": endpoint.get("name"),
                            "host": host, "hostEvidence": "service-connection-url" if url else "service-connection-name",
                            "sshPort": urlparse(url).port or 22, "directories": [],
                            "serviceScripts": [], "steps": [],
                        }
                    target = targets[endpoint_id]
                    folder = inputs.get("targetFolder")
                    if folder and folder not in target["directories"]:
                        target["directories"].append(folder)
                    inline = inputs.get("inline") or inputs.get("commands") or ""
                    for script in re.findall(r"(/[\w./-]+\.sh)\s+(?:start|stop|restart)\b", inline):
                        if script not in target["serviceScripts"]:
                            target["serviceScripts"].append(script)
                    target["steps"].append(task.get("name"))
            environments.append({
                "environmentId": env["id"], "name": env["name"],
                "conditions": env.get("conditions", []),
                "automaticApproval": all(
                    a.get("isAutomated", False)
                    for a in env.get("preDeployApprovals", {}).get("approvals", [])
                ),
                "schedules": env.get("schedules", []),
                "targets": list(targets.values()), "unexpandedTaskGroupIds": task_groups,
            })
        releases.append({
            "releaseDefinitionId": release["id"], "name": release["name"],
            "definitionUrl": f"{base_url.rstrip('/')}/{quote(team_project, safe='')}/_release?definitionId={release['id']}&view=mine&_a=releases",
            "artifactAliases": sorted(aliases), "automaticTrigger": bool(triggers),
            "triggerConditions": [t.get("triggerConditions", []) for t in triggers],
            "environments": environments,
        })
    return {
        "project": project_name, "definitionId": definition_id, "tfsProject": team_project,
        "checkedAt": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "status": "linked-releases-found" if releases else "no-linked-release-found",
        "releases": releases,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", default=str(default_catalog_path()))
    parser.add_argument("--project-name", help="Exact catalog standard name; omit to inspect all")
    parser.add_argument("--base-url", default=os.environ.get("TFS_BASE_URL", DEFAULT_BASE_URL))
    args = parser.parse_args()
    if not os.environ.get("TFS_PAT"):
        parser.error("TFS_PAT is required")
    catalog = json.loads(Path(args.catalog).read_text(encoding="utf-8"))
    jobs = [
        (p["standardName"], pipeline, args.base_url)
        for p in catalog.get("projects", [])
        if not args.project_name or p["standardName"] == args.project_name
        for pipeline in p.get("pipelines", [])
    ]
    if not jobs:
        parser.error("no cataloged pipelines matched")
    def run(job):
        try:
            return audit_pipeline(*job)
        except Exception as error:
            return {"project": job[0], "definitionId": job[1]["definitionId"],
                    "status": "audit-failed", "errorType": type(error).__name__}
    with ThreadPoolExecutor(max_workers=4) as pool:
        results = list(pool.map(run, jobs))
    print(json.dumps({"pipelines": results}, ensure_ascii=False, indent=2))
    return int(any(r["status"] == "audit-failed" for r in results))


if __name__ == "__main__":
    raise SystemExit(main())
