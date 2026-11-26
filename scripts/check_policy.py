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
    data = subprocess.check_output(
        ["git", "show", "-s", "--format=%s%n%an%n%ae%n%B", sha], text=True
    ).splitlines()
    errors = []
    if not check_title(data[0], issue):
        errors.append("commit subject must be Conventional Commits with issue ID")
    if data[1:3] != ["Víctor M. Reyes", "vm.reyesal@gmail.com"]:
        errors.append("commit author must match approved local identity")
    if FORBIDDEN.search("\n".join(data[3:])):
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
    parser.add_argument("--issue", default="AT-207")
    args = parser.parse_args()
    errors = []
    if args.title and not check_title(args.title, args.issue):
        errors.append("PR title must be Conventional Commits with issue ID")
    if args.branch and not check_branch(args.branch, args.issue):
        errors.append("branch must use feature/fix/hotfix/AT-XXX-slug")
    if args.commit:
        errors.extend(check_commit(args.commit, args.issue))
    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1
    print("Metadata policy passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
