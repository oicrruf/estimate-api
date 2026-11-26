"""Check PR and final commit metadata for Estimate Agent Git Flow."""

import argparse
import re
import subprocess
import sys

TITLE = re.compile(
    r"^(feat|fix|refactor|perf|test|docs|build|ci|chore|revert)"
    r"\([a-z][a-z0-9-]*\)!?: [a-z][^\n]* \(AT-[0-9]+\)$"
)
BRANCH = re.compile(r"^(feature|fix|hotfix)/AT-[0-9]+-[a-z0-9-]+$")
FORBIDDEN = re.compile(r"(?im)^(co-authored-by|generated-by):.*(codex|claude|chatgpt|openai)")


def check_title(title: str, issue: str) -> bool:
    return bool(TITLE.fullmatch(title) and title.endswith(f"({issue})"))


def check_branch(branch: str, issue: str) -> bool:
    return bool(BRANCH.fullmatch(branch) and f"/{issue}-" in branch)


def check_commit(sha: str, issue: str) -> list[str]:
    if not re.fullmatch(r"[0-9a-f]{40}", sha):
        return ["commit must be an explicit 40-character SHA"]
    data = subprocess.check_output(
        ["git", "show", "-s", "--format=%s%n%an%n%ae%n%cn%n%ce%n%B", sha], text=True
    ).splitlines()
    errors = []
    if not check_title(data[0], issue):
        errors.append("commit subject must be Conventional Commits with issue ID")
    if data[1:3] != ["Víctor M. Reyes", "vm.reyesal@gmail.com"]:
        errors.append("commit author must match approved local identity")
    if data[3:5] != ["Víctor M. Reyes", "vm.reyesal@gmail.com"]:
        errors.append("commit committer must match approved local identity")
    if FORBIDDEN.search("\n".join(data[5:])):
        errors.append("commit contains discretionary AI attribution")
    parents = subprocess.check_output(["git", "rev-list", "--parents", "-n", "1", sha], text=True)
    if len(parents.split()) > 2:
        errors.append("merge commits are prohibited")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--title")
    parser.add_argument("--branch")
    parser.add_argument("--commit")
    parser.add_argument("--issue")
    args = parser.parse_args()
    errors = []
    issue = args.issue
    if not issue and args.title:
        match = re.search(r"\((AT-[0-9]+)\)$", args.title)
        issue = match.group(1) if match else None
    if (args.title or args.branch or args.commit) and not issue:
        errors.append("issue ID is required or must appear at end of PR title")
    if args.title and issue and not check_title(args.title, issue):
        errors.append("PR title must be Conventional Commits with issue ID")
    if args.branch and issue and not check_branch(args.branch, issue):
        errors.append("branch must use feature/fix/hotfix/AT-XXX-slug")
    if args.commit and issue:
        errors.extend(check_commit(args.commit, issue))
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("Metadata policy passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
