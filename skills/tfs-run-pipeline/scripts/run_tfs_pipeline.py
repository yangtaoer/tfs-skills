#!/usr/bin/env python3
"""Resolve, queue, and monitor a cataloged TFS delivery pipeline."""

from __future__ import annotations

import argparse
import base64
import json
import os
import sys
import time
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "http://dev.tellhowsoft.com/DefaultCollection"
ACTIVE_STATUSES = {"notStarted", "inProgress", "postponed"}


def default_catalog_path() -> Path:
    return (
        Path(__file__).resolve().parents[2]
        / "tfs-project-catalog"
        / "references"
        / "project-catalog.seed.json"
    )


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def resolve_project(catalog: dict[str, Any], value: str) -> dict[str, Any]:
    requested = value.strip()
    exact = [
        project
        for project in catalog.get("projects", [])
        if str(project.get("standardName", "")).strip() == requested
    ]
    if len(exact) == 1:
        return exact[0]

    aliases = [
        project
        for project in catalog.get("projects", [])
        if requested in [str(alias).strip() for alias in project.get("aliases", [])]
    ]
    if len(aliases) == 1:
        return aliases[0]
    if len(aliases) > 1:
        names = ", ".join(str(project.get("standardName")) for project in aliases)
        raise ValueError(f"alias maps to multiple projects: {requested} -> {names}")
    raise ValueError(f"project is not present in the catalog: {requested}")


def resolve_pipeline(project: dict[str, Any], definition_id: int | None) -> dict[str, Any]:
    pipelines = list(project.get("pipelines", []) or [])
    if definition_id is not None:
        matches = [p for p in pipelines if int(p.get("definitionId", 0)) == definition_id]
    else:
        matches = [p for p in pipelines if p.get("purpose") == "delivery"]
    if len(matches) == 1:
        return matches[0]
    standard_name = project.get("standardName", "<unknown>")
    if not matches:
        raise ValueError(f"no matching delivery pipeline is cataloged for {standard_name}")
    ids = ", ".join(str(p.get("definitionId")) for p in matches)
    raise ValueError(f"multiple delivery pipelines are cataloged for {standard_name}: {ids}")


class TfsBuildClient:
    def __init__(self, base_url: str, tfs_project: str, pat: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.tfs_project = tfs_project
        encoded = base64.b64encode(f":{pat}".encode("utf-8")).decode("ascii")
        self.headers = {"Authorization": f"Basic {encoded}"}

    def api_url(self, suffix: str, **query: Any) -> str:
        params = {key: value for key, value in query.items() if value is not None}
        params.setdefault("api-version", "4.1")
        query_string = urlencode(params)
        project = quote(self.tfs_project, safe="")
        return f"{self.base_url}/{project}/_apis/build/{suffix}?{query_string}"

    def request_json(
        self, method: str, url: str, payload: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        headers = dict(self.headers)
        data = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            data = json.dumps(payload).encode("utf-8")
        request = Request(url, data=data, headers=headers, method=method)
        try:
            with urlopen(request, timeout=30) as response:
                return json.loads(response.read().decode("utf-8", errors="replace"))
        except HTTPError as error:
            body = error.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"TFS returned HTTP {error.code}: {body[:500]}") from error
        except URLError as error:
            raise RuntimeError(f"cannot reach TFS: {error.reason}") from error

    def get_definition(self, definition_id: int) -> dict[str, Any]:
        return self.request_json("GET", self.api_url(f"definitions/{definition_id}"))

    def recent_builds(self, definition_id: int) -> list[dict[str, Any]]:
        response = self.request_json(
            "GET",
            self.api_url(
                "builds",
                definitions=definition_id,
                **{"$top": 50},
                queryOrder="queueTimeDescending",
            ),
        )
        return list(response.get("value", []) or [])

    def queue_build(self, definition_id: int, source_branch: str) -> dict[str, Any]:
        payload: dict[str, Any] = {"definition": {"id": definition_id}}
        if source_branch:
            payload["sourceBranch"] = source_branch
        return self.request_json("POST", self.api_url("builds"), payload)

    def get_build(self, build_id: int) -> dict[str, Any]:
        return self.request_json("GET", self.api_url(f"builds/{build_id}"))

    def get_artifacts(self, build_id: int) -> list[dict[str, Any]]:
        response = self.request_json("GET", self.api_url(f"builds/{build_id}/artifacts"))
        return list(response.get("value", []) or [])


def normalize_branch(value: str) -> str:
    branch = value.strip()
    if branch and not branch.startswith("refs/heads/"):
        return f"refs/heads/{branch}"
    return branch


def pipeline_plan(
    project: dict[str, Any], pipeline: dict[str, Any], base_url: str, source_branch: str
) -> dict[str, Any]:
    tfs_project = str(pipeline.get("tfsProject") or "DCS")
    definition_id = int(pipeline["definitionId"])
    definition_url = pipeline.get("definitionUrl") or (
        f"{base_url.rstrip('/')}/{quote(tfs_project, safe='')}/_build?definitionId={definition_id}"
    )
    return {
        "standardName": project.get("standardName"),
        "pipelineName": pipeline.get("name"),
        "definitionId": definition_id,
        "definitionUrl": definition_url,
        "folderPath": pipeline.get("folderPath"),
        "tfsProject": tfs_project,
        "repository": pipeline.get("repository"),
        "sourceBranch": source_branch,
        "buildProfile": pipeline.get("buildProfile"),
        "expectedArtifact": pipeline.get("artifactName"),
    }


def live_check(
    client: TfsBuildClient, plan: dict[str, Any], force_new: bool
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    definition = client.get_definition(int(plan["definitionId"]))
    live_name = str(definition.get("name", ""))
    expected_name = str(plan.get("pipelineName") or "")
    if expected_name and live_name != expected_name:
        raise RuntimeError(
            f"catalog definition name mismatch: expected {expected_name!r}, got {live_name!r}"
        )
    if definition.get("queueStatus") not in (None, "enabled"):
        raise RuntimeError(f"pipeline is not enabled: {definition.get('queueStatus')}")

    expected_repository = str(plan.get("repository") or "")
    live_repository = str((definition.get("repository") or {}).get("name") or "")
    if expected_repository and live_repository != expected_repository:
        raise RuntimeError(
            "catalog repository mismatch: "
            f"expected {expected_repository!r}, got {live_repository!r}"
        )

    definition_steps = list(definition.get("build", []) or [])
    for phase in (definition.get("process") or {}).get("phases", []) or []:
        definition_steps.extend(phase.get("steps", []) or [])
    enabled_steps = [step for step in definition_steps if step.get("enabled")]
    maven_goals = [
        str((step.get("inputs") or {}).get("goals") or "")
        for step in enabled_steps
        if (step.get("inputs") or {}).get("goals")
    ]
    expected_profile = str(plan.get("buildProfile") or "")
    if expected_profile and not any(
        f"-P {expected_profile}" in goals or f"-P{expected_profile}" in goals
        for goals in maven_goals
    ):
        raise RuntimeError(
            f"catalog build profile {expected_profile!r} is not present in live Maven goals"
        )
    published_artifacts = [
        str((step.get("inputs") or {}).get("ArtifactName") or "")
        for step in enabled_steps
        if (step.get("inputs") or {}).get("ArtifactName")
    ]
    expected_artifact = str(plan.get("expectedArtifact") or "")
    if expected_artifact and expected_artifact not in published_artifacts:
        raise RuntimeError(
            f"catalog artifact {expected_artifact!r} is not published by the live definition"
        )

    active = [
        build
        for build in client.recent_builds(int(plan["definitionId"]))
        if build.get("status") in ACTIVE_STATUSES
        and normalize_branch(str(build.get("sourceBranch") or "")) == plan["sourceBranch"]
    ]
    active_build = None if force_new or not active else active[0]
    check = {
        "liveName": live_name,
        "queueStatus": definition.get("queueStatus"),
        "liveRepository": live_repository,
        "liveDefaultBranch": (definition.get("repository") or {}).get("defaultBranch"),
        "liveMavenGoals": maven_goals,
        "livePublishedArtifacts": published_artifacts,
        "activeBuildIds": [build.get("id") for build in active],
    }
    return check, active_build


def build_links(base_url: str, tfs_project: str, build_id: int) -> dict[str, str]:
    project = quote(tfs_project, safe="")
    root = f"{base_url.rstrip('/')}/{project}/_build/results?buildId={build_id}"
    return {
        "resultsUrl": f"{root}&view=results",
        "artifactsUrl": (
            f"{root}&view=artifacts&pathAsName=false&type=publishedArtifacts"
        ),
    }


def wait_for_build(
    client: TfsBuildClient, build_id: int, poll_seconds: int, timeout_seconds: int
) -> dict[str, Any]:
    deadline = time.monotonic() + timeout_seconds
    previous = None
    while True:
        build = client.get_build(build_id)
        state = (build.get("status"), build.get("result"))
        if state != previous:
            print(
                f"build {build_id}: status={state[0]} result={state[1]}",
                file=sys.stderr,
                flush=True,
            )
            previous = state
        if build.get("status") == "completed":
            return build
        if time.monotonic() >= deadline:
            raise TimeoutError(f"timed out waiting for build {build_id}")
        time.sleep(poll_seconds)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project-name", help="Standard project name or exact alias")
    parser.add_argument("--catalog", default=str(default_catalog_path()), help="Project catalog JSON")
    parser.add_argument(
        "--list-projects",
        action="store_true",
        help="List cataloged delivery pipelines without contacting TFS",
    )
    parser.add_argument("--definition-id", type=int, help="Select one cataloged definition explicitly")
    parser.add_argument("--base-url", default=os.environ.get("TFS_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--source-branch", default="", help="Optional branch override")
    action = parser.add_mutually_exclusive_group()
    action.add_argument("--check-definition", action="store_true", help="Read-only live validation")
    action.add_argument("--confirm-run", action="store_true", help="Authorize one build run")
    action.add_argument("--build-id", type=int, help="Monitor an already queued build")
    parser.add_argument("--force-new", action="store_true", help="Queue even when an active build exists")
    parser.add_argument("--poll-seconds", type=int, default=10)
    parser.add_argument("--timeout-seconds", type=int, default=3600)
    args = parser.parse_args()

    try:
        catalog = load_json(Path(args.catalog))
        if args.list_projects:
            if any(
                (
                    args.project_name,
                    args.definition_id,
                    args.source_branch,
                    args.check_definition,
                    args.confirm_run,
                    args.build_id,
                    args.force_new,
                )
            ):
                raise ValueError("--list-projects cannot be combined with run options")
            pipelines = []
            for catalog_project in catalog.get("projects", []) or []:
                for catalog_pipeline in catalog_project.get("pipelines", []) or []:
                    if catalog_pipeline.get("purpose") != "delivery":
                        continue
                    pipelines.append(
                        {
                            "standardName": catalog_project.get("standardName"),
                            "definitionId": catalog_pipeline.get("definitionId"),
                            "pipelineName": catalog_pipeline.get("name"),
                            "definitionUrl": catalog_pipeline.get("definitionUrl"),
                            "sourceBranch": catalog_pipeline.get("sourceBranch"),
                            "buildProfile": catalog_pipeline.get("buildProfile"),
                            "expectedArtifact": catalog_pipeline.get("artifactName"),
                        }
                    )
            pipelines.sort(key=lambda item: str(item.get("standardName") or ""))
            print(json.dumps({"projects": pipelines}, ensure_ascii=False, indent=2))
            return 0
        if not args.project_name:
            parser.error("--project-name is required unless --list-projects is used")
        project = resolve_project(catalog, args.project_name)
        pipeline = resolve_pipeline(project, args.definition_id)
        source_branch = normalize_branch(
            args.source_branch or str(pipeline.get("sourceBranch") or "")
        )
        if not source_branch:
            raise ValueError("the pipeline has no source branch")
        plan = pipeline_plan(project, pipeline, args.base_url, source_branch)

        if args.force_new and not args.confirm_run:
            raise ValueError("--force-new requires --confirm-run")
        if not args.check_definition and not args.confirm_run and not args.build_id:
            print(json.dumps({"action": "plan", **plan}, ensure_ascii=False, indent=2))
            return 0

        pat = os.environ.get("TFS_PAT", "")
        if not pat:
            raise RuntimeError("TFS_PAT is required for live pipeline operations")
        client = TfsBuildClient(args.base_url, str(plan["tfsProject"]), pat)
        check, active_build = live_check(client, plan, args.force_new)
        if args.check_definition:
            print(
                json.dumps(
                    {"action": "check", **plan, "live": check},
                    ensure_ascii=False,
                    indent=2,
                )
            )
            return 0

        if args.build_id:
            build = client.get_build(args.build_id)
            live_definition_id = int((build.get("definition") or {}).get("id") or 0)
            if live_definition_id != int(plan["definitionId"]):
                raise RuntimeError(
                    f"build {args.build_id} belongs to definition {live_definition_id}, "
                    f"not {plan['definitionId']}"
                )
            queue_action = "monitor-existing"
            print(f"monitoring build {build.get('id')}", file=sys.stderr, flush=True)
        elif active_build is not None:
            build = active_build
            queue_action = "wait-existing"
            print(f"using active build {build.get('id')}", file=sys.stderr, flush=True)
        else:
            build = client.queue_build(int(plan["definitionId"]), source_branch)
            queue_action = "queued"
            print(f"queued build {build.get('id')}", file=sys.stderr, flush=True)

        build_id = int(build["id"])
        completed = wait_for_build(client, build_id, args.poll_seconds, args.timeout_seconds)
        artifacts = client.get_artifacts(build_id)
        artifact_names = [str(artifact.get("name")) for artifact in artifacts]
        links = build_links(args.base_url, str(plan["tfsProject"]), build_id)
        expected = str(plan.get("expectedArtifact") or "")
        expected_found = not expected or expected in artifact_names
        result = {
            "action": queue_action,
            **plan,
            "buildId": build_id,
            "buildNumber": completed.get("buildNumber"),
            "status": completed.get("status"),
            "result": completed.get("result"),
            **links,
            "artifacts": artifact_names,
            "expectedArtifactFound": expected_found,
        }
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if completed.get("result") != "succeeded":
            return 3
        if not artifacts or not expected_found:
            return 4
        return 0
    except (ValueError, RuntimeError, TimeoutError, KeyError, OSError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
