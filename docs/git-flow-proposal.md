# AT-207 Git Flow protections proposal

This document proposes settings and tests; it does not apply repository settings.

- Protect `develop` and `main`: require PR checks, no force pushes or deletions, and approved reviews per repository policy. Require the `verify` CI job, current branch, and resolved actionable review threads before merge.
- Disable merge commits, enable Squash & Merge for issue PRs, and consider disabling rebase merges to keep one final issue commit. Confirm the squash title matches the checked PR title and author identity before merging.
- Release promotion to `main` must be fast-forward-only after `git merge-base --is-ancestor main <candidate-sha>` and all release gates pass. A standard GitHub PR merge cannot implement that exact promotion; design an authorized, protected mechanism before use. AT-226 validates promotion, reconciliation, tags, and rollback.
- Hotfix starts from `main`; reconcile its effect into `develop` and any active release with tracked cherry-pick/reapplication and tests. Do not create merge commits.
- Secret scanning runs in CI without credentials. AT-277 later adds Trivy for dependencies, IaC and container images after AT-207 integrates. Dependency review and platform protections remain a separate effective configuration step.

Smoke policy test cases: valid conventional PR title and feature branch pass; wrong issue number, merge-style title, and wrong branch fail. `scripts/check_policy.py --commit <sha>` checks the eventual local commit subject, author and merge parent count. Actual squash SHA must be checked after merge before closing Linear.
