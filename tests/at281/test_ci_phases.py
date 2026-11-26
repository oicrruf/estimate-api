"""The protected summary gate fails closed for every required CI phase."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/ci.yml"
GATE = ROOT / "ci/at-281/verify-phases.sh"
PHASES = {
    "PYTHON_QUALITY_RESULT": "python-quality",
    "PYTEST_RESULT": "pytest",
    "OPENAPI_RESULT": "openapi",
    "OPENSPEC_EVIDENCE_RESULT": "openspec-evidence",
    "SECURITY_METADATA_RESULT": "security-metadata",
    "CONTAINER_RESULT": "container",
}


def _gate(statuses: dict[str, str]) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    for phase in PHASES:
        env.pop(phase, None)
    env.update(statuses)
    return subprocess.run(
        ["bash", str(GATE)], cwd=ROOT, env=env, text=True, capture_output=True, check=False
    )


def test_all_required_phases_succeed() -> None:
    result = _gate(dict.fromkeys(PHASES, "success"))
    assert result.returncode == 0
    assert result.stdout.count(": success\n") == len(PHASES)


@pytest.mark.parametrize("phase", PHASES)
@pytest.mark.parametrize("outcome", ["failure", "skipped", "cancelled", "missing"])
def test_any_non_success_result_fails_closed(phase: str, outcome: str) -> None:
    statuses = dict.fromkeys(PHASES, "success")
    if outcome == "missing":
        del statuses[phase]
    else:
        statuses[phase] = outcome
    result = _gate(statuses)
    assert result.returncode != 0
    assert f"{phase}: {outcome}\n" in result.stdout


def test_workflow_maps_every_required_job_to_the_protected_gate() -> None:
    workflow = WORKFLOW.read_text()
    assert "permissions:\n  contents: read\n" in workflow
    assert "  verify:\n    name: verify\n    if: ${{ always() }}\n" in workflow
    needs = (
        "needs: [python-quality, pytest, openapi, openspec-evidence, security-metadata, container]"
    )
    assert needs in workflow
    for phase, job in PHASES.items():
        assert f"{phase}: ${{{{ needs.{job}.result }}}}" in workflow
    assert "run: bash ci/at-281/verify-phases.sh" in workflow


def test_pr_only_metadata_does_not_skip_push_secret_scan() -> None:
    workflow = WORKFLOW.read_text()
    metadata = workflow.index("      - name: Verify PR metadata")
    assert workflow.index("      - name: Scan for secrets") < metadata
    assert "if: github.event_name == 'pull_request'" in workflow[metadata : metadata + 180]
    assert workflow.count("if: github.event_name == 'pull_request'") == 1
