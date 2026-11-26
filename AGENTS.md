# Estimate API agent instructions

Work from current `develop` on `feature/AT-XXX-slug`; PR to `develop`. Use OpenSpec spec-driven: proposal, delta spec, design, tasks, validate, implement, verify, archive in one final issue commit. Keep Conventional Commits title `type(scope): imperative summary (AT-XXX)`. Local commit identity is Víctor M. Reyes <vm.reyesal@gmail.com>; do not change global Git config or add discretionary AI attribution. Required platform or license metadata is preserved.

For high-impact auth, RLS, migrations, pricing rules, cross-service security, and irreversible infrastructure, seek fresh-context design review when available; for ordinary bootstrap changes use focused tests and CI. Do not claim a review occurred unless it did.

Before integration, inspect current PR review threads and actionable feedback, base SHA, checks and security findings. Fix feedback in the same branch and rerun checks. Resolve threads only after verifying fixes. Use Squash & Merge only, verify one conventional issue commit on `develop`, then update Linear. Never force push protected branches.

Keep source and fixtures synthetic. No production secrets. Do not implement AT-277 Trivy gate until AT-207 is merged; the bootstrap includes defensive secret scanning.
