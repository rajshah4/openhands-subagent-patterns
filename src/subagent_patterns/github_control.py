from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from subagent_patterns.models import BuildRequest

ROOT = Path(__file__).resolve().parents[2]


@dataclass
class GitHubControlResult:
    issue_url: str
    pr_url: str
    branch_name: str
    run_dir: Path


def _run(cmd: list[str], *, cwd: Path | None = None) -> str:
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.strip()


def _repo_slug() -> str:
    url = _origin_url()
    if url.startswith("git@github.com:"):
        return url.removeprefix("git@github.com:").removesuffix(".git")
    if url.startswith("https://github.com/"):
        return url.removeprefix("https://github.com/").removesuffix(".git")
    raise RuntimeError(f"Unsupported origin URL: {url}")


def _origin_url() -> str:
    return _run(["git", "remote", "get-url", "origin"], cwd=ROOT)


def run_github_control_demo(
    *,
    output_dir: Path,
    request: BuildRequest | None = None,
) -> GitHubControlResult:
    request = request or BuildRequest()
    repo_slug = _repo_slug()
    run_id = time.strftime("%Y%m%d-%H%M%S")
    run_dir = output_dir / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    issue_title = f"GitHub control demo: missing {request.missing_connector} connector ({run_id})"
    issue_body = f"""
This issue is a live demo of the GitHub control-plane workflow.

Application request:
- {request.user_description}

Missing dependency:
- {request.missing_connector} connector

Expected outcome:
- app flow continues on connector-independent areas: {", ".join(request.connector_independent_scope)}
- connector PR defines integration contract for blocked work: {", ".join(request.connector_dependent_scope)}
- PR comment simulates the integration trigger once the connector is ready

Run id: `{run_id}`
""".strip()
    issue_body_path = run_dir / "issue.md"
    issue_body_path.write_text(issue_body + "\n", encoding="utf-8")

    issue_url = _run(
        [
            "gh",
            "issue",
            "create",
            "--repo",
            repo_slug,
            "--title",
            issue_title,
            "--body-file",
            str(issue_body_path),
        ],
        cwd=ROOT,
    )
    issue_number = issue_url.rstrip("/").split("/")[-1]

    temp_dir = Path(tempfile.mkdtemp(prefix="gh-control-demo-"))
    try:
        clone_dir = temp_dir / "repo"
        _run(["git", "clone", _origin_url(), str(clone_dir)])

        branch_name = f"demo/github-control-{run_id}"
        _run(["git", "checkout", "-b", branch_name], cwd=clone_dir)

        artifact_dir = clone_dir / "demo_runs" / "github_control" / run_id
        artifact_dir.mkdir(parents=True, exist_ok=True)
        connector_path = artifact_dir / "connector_plan.md"
        handoff_path = artifact_dir / "connector_handoff.md"
        connector_path.write_text(
            (
                f"# {request.missing_connector.title()} Connector Plan\n\n"
                f"Run id: `{run_id}`\n\n"
                f"Issue: {issue_url}\n\n"
                f"This artifact simulates the output of a connector-building agent for {request.app_name}.\n"
                "- auth: oauth2 web flow\n"
                "- objects: leads, accounts, opportunities\n"
                "- operations: read/write sync plus smoke test plan\n"
                "- contract: normalize account, contact, and opportunity payloads for the app layer\n"
            ),
            encoding="utf-8",
        )
        handoff_path.write_text(
            (
                f"# Connector Handoff\n\n"
                f"Blocked work to resume once the {request.missing_connector} connector is available:\n"
                + "".join(f"- {item}\n" for item in request.connector_dependent_scope)
                + "\nApp work that can continue independently:\n"
                + "".join(f"- {item}\n" for item in request.connector_independent_scope)
                + "\nIntegration notes:\n"
                "- wire the connector behind the contract documented in `connector_plan.md`\n"
                "- validate smoke tests before merging the connector branch into the app flow\n"
            ),
            encoding="utf-8",
        )

        _run(
            [
                "git",
                "add",
                str(connector_path.relative_to(clone_dir)),
                str(handoff_path.relative_to(clone_dir)),
            ],
            cwd=clone_dir,
        )
        _run(["git", "commit", "-m", f"Add connector plan for GitHub control demo {run_id}"], cwd=clone_dir)
        _run(["git", "push", "-u", "origin", branch_name], cwd=clone_dir)

        pr_body_path = run_dir / "pr.md"
        pr_body_path.write_text(
            (
                f"## Demo PR\n\n"
                f"Closes #{issue_number}\n\n"
                "This PR is part of the GitHub control-plane demo.\n"
                "- adds connector planning and handoff artifacts\n"
                "- shows which app work stays unblocked while the connector is built\n"
                "- allows a follow-up integration trigger via comment\n"
            ),
            encoding="utf-8",
        )
        pr_url = _run(
            [
                "gh",
                "pr",
                "create",
                "--repo",
                repo_slug,
                "--draft",
                "--head",
                branch_name,
                "--title",
                f"Demo PR: connector artifact ({run_id})",
                "--body-file",
                str(pr_body_path),
            ],
            cwd=clone_dir,
        )
        pr_number = pr_url.rstrip("/").split("/")[-1]

        _run(
            [
                "gh",
                "issue",
                "comment",
                issue_number,
                "--repo",
                repo_slug,
                "--body",
                (
                    f"@OpenHands build the missing {request.missing_connector} connector. "
                    "Use the issue body as the contract and keep the app flow unblocked where possible."
                ),
            ],
            cwd=ROOT,
        )
        _run(
            [
                "gh",
                "pr",
                "comment",
                pr_number,
                "--repo",
                repo_slug,
                "--body",
                (
                    "@OpenHands integrate this connector into the app flow once validation is complete. "
                    "Resume the blocked items listed in the handoff artifact."
                ),
            ],
            cwd=ROOT,
        )

        summary = {
            "run_id": run_id,
            "repo": repo_slug,
            "issue_url": issue_url,
            "pr_url": pr_url,
            "branch_name": branch_name,
        }
        (run_dir / "summary.json").write_text(
            json.dumps(summary, indent=2) + "\n",
            encoding="utf-8",
        )
        return GitHubControlResult(
            issue_url=issue_url,
            pr_url=pr_url,
            branch_name=branch_name,
            run_dir=run_dir,
        )
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)
