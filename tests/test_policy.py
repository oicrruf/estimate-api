import os
import subprocess
from pathlib import Path

from pytest import MonkeyPatch

from scripts.check_policy import check_branch, check_commit, check_title


def git(repo: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(repo), *args], text=True).strip()


def synthetic_commit(
    repo: Path,
    title: str,
    author: str = "Víctor M. Reyes",
    committer: str = "Víctor M. Reyes",
    body: str = "",
) -> str:
    command = [
        "git",
        "-C",
        str(repo),
        "-c",
        f"user.name={committer}",
        "-c",
        "user.email=vm.reyesal@gmail.com",
        "commit",
        "--quiet",
        "--allow-empty",
        "-m",
        title,
    ]
    if body:
        command.extend(["-m", body])
    environment = {
        **os.environ,
        "GIT_AUTHOR_NAME": author,
        "GIT_AUTHOR_EMAIL": "vm.reyesal@gmail.com",
    }
    subprocess.run(command, check=True, env=environment)
    return git(repo, "rev-parse", "HEAD")


def test_valid_metadata() -> None:
    assert check_title("feat(api): initialize bootstrap (AT-207)", "AT-207")
    assert check_branch("feature/AT-207-api-bootstrap", "AT-207")
    assert check_title("feat(auth): add login (AT-209)", "AT-209")
    assert check_branch("feature/AT-209-login", "AT-209")


def test_rejects_mismatch_and_malformed_metadata() -> None:
    assert not check_title("feat(api): initialize bootstrap (AT-208)", "AT-207")
    assert not check_title("Merge pull request #1", "AT-207")
    assert not check_title("feat(api): missing issue", "AT-207")
    assert not check_branch("feature/AT-208-api-bootstrap", "AT-207")


def test_submitted_commit_policy(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "-C", str(repo), "init", "-q", "-b", "develop"], check=True)
    monkeypatch.chdir(repo)
    good = synthetic_commit(repo, "feat(api): initialize bootstrap (AT-207)")
    assert check_commit(good, "AT-207") == []
    wrong_author = synthetic_commit(repo, "fix(api): correct bootstrap (AT-207)", author="Other")
    assert "commit author must match approved local identity" in check_commit(
        wrong_author, "AT-207"
    )
    wrong_committer = synthetic_commit(
        repo, "fix(api): correct bootstrap (AT-207)", committer="Other"
    )
    assert "commit committer must match approved local identity" in check_commit(
        wrong_committer, "AT-207"
    )
    trailer = synthetic_commit(
        repo,
        "fix(api): correct bootstrap (AT-207)",
        body="Co-authored-by: Codex <assistant@example.invalid>",
    )
    assert "commit contains discretionary AI attribution" in check_commit(trailer, "AT-207")
    wrong_issue = synthetic_commit(repo, "fix(api): correct bootstrap (AT-208)")
    assert "commit subject must be Conventional Commits with issue ID" in check_commit(
        wrong_issue, "AT-207"
    )
    assert check_commit("HEAD", "AT-207") == ["commit must be an explicit 40-character SHA"]


def test_successor_issue_submitted_commit(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    repo = tmp_path / "successor"
    repo.mkdir()
    subprocess.run(["git", "-C", str(repo), "init", "-q", "-b", "develop"], check=True)
    monkeypatch.chdir(repo)
    title = "feat(auth): add login (AT-208)"
    head = synthetic_commit(repo, title)
    assert check_title(title, "AT-208")
    assert check_branch("feature/AT-208-login", "AT-208")
    assert check_commit(head, "AT-208") == []
    assert not check_branch("feature/AT-207-login", "AT-208")
