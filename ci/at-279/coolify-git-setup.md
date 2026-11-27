# AT-279: Git-based Coolify candidate handoff

**Status:** review candidate only. No Coolify resource, VPS deployment, hosted route,
TLS certificate, or access policy has been verified by this PR. The project/environment
name supplied for a possible handoff is `estimate-agent → production`; it is a name,
not evidence that anything is running there.

## Identify the three artifacts

| Artifact | Exact identity | What was tested |
| --- | --- | --- |
| Portable local package | API `dac8c64c314bb362c6254825c65640ba732ca168`, web `1b95205596f50d38ba60254319bb12584bde3a5a`; [package manifest](package/MANIFEST.sha256) and [archive digest](ARCHIVE-SHA256.txt) | Disposable loopback Compose, five technical cases, static `/demo/review` screen, synthetic store reopen, and browser interactions. It is not a Git-based Coolify resource. |
| Refreshed Git candidate | The reviewed full SHA of this PR's head, with [`coolify-compose.yaml`](coolify-compose.yaml), API `dac8c64c314bb362c6254825c65640ba732ca168`, and web `1b95205596f50d38ba60254319bb12584bde3a5a` | CI builds the Git-fetched sources and tests the internal web origin without a host port. A temporary **CI-only** overlay binds web to `127.0.0.1:8080` for the same-origin browser test; it is not part of the deployment Compose. |
| Immutable fallback | Repository commit `46e97c160963bf094f04d3d9eb4319b61c435441`, API `dac8c64c314bb362c6254825c65640ba732ca168`, web `d8a6d359bf909872ebfe48d52dfe5d8980c2c68b` | The previously validated Git Compose candidate. This ref remains unchanged. Its old web source does not contain the refreshed review screen. |

The candidate Dockerfiles fetch public **exact commit SHAs** and verify `FETCH_HEAD`.
The Python, Node, Nginx, and uv base images are digest-pinned, and dependency locks
are consumed. Runtime needs no model provider or secret. Builds need HTTPS access
to GitHub, package registries, and base-image registries.

To reproduce the Git candidate on a disposable machine, from `ci/at-279` run:

```sh
docker compose -f coolify-compose.yaml config --quiet
docker compose -f coolify-compose.yaml build
docker compose -f coolify-compose.yaml up --no-build -d
python3 verify_coolify_git.py
docker compose -f coolify-compose.yaml down -v --remove-orphans
```

This default Compose publishes no host port. The PR's CI workflow creates a
temporary loopback overlay for browser testing and removes the disposable stack.

## Proposed owner handoff, after approval

1. In the intended `estimate-agent → production` project/environment, create a
   **Public Repository Application** from `https://github.com/oicrruf/estimate-api.git`
   with the **Docker Compose** build strategy. Do not use **Docker Compose Empty**:
   that mode lacks the Git checkout needed by the Dockerfiles and local `COPY`
   instructions. Do not enable automatic deployment or previews.
2. Select this PR's reviewed **full head SHA**, not a moving branch, if validating
   before integration. After integration, select and verify the resulting full
   `develop` commit SHA. Use Base Directory `/ci/at-279` and Docker Compose Location
   `/coolify-compose.yaml` relative to that directory. Confirm the selected file
   contains the two source pins in the table. If the installed UI cannot pin a
   commit, stop and resolve that control before deployment. The proposed UI or API
   path for pinning is not verified here.
3. Inspect the **generated** Compose before any authorized deploy. Keep Raw Compose
   disabled unless its generated proxy/network effects are understood. Only `web`
   should receive the approved HTTPS demo route at internal port `8080`; `api` and
   `seed` must have no domain or host `ports:`. Confirm the private `backplane`,
   `api`'s read-only `/data`, the dedicated `synthetic_store` volume, one-shot seed,
   resource limits, and absence of Docker socket or privileged access. Apply the
   owner's access policy before any link is shared.
4. If deployment is separately authorized, check Deployment Logs for the selected
   repository SHA and Dockerfile `FETCH_HEAD` pins. Check seed creation/reuse and API
   health without disclosing logs or data. Through the approved HTTPS demo route,
   test `/demo`, the five technical cases, and `/demo/review` with its eight,
   missing-measurement, and changed-ten synthetic cases. Verify API and seed have no
   direct public route. This PR does **not** perform these hosted checks.

For rollback, retain the last approved release and its volume identity in the
owner's change record. If the refreshed candidate fails, the owner can select the
immutable repository commit `46e97c160963bf094f04d3d9eb4319b61c435441`
and recheck the older five-scenario demo. Its source pins are fixed as shown above;
rollback is a separate authorized action, not a CI side effect. Do not discard or
migrate a persistent volume automatically.

The [AT-279 local validation guide](README.md) contains exact CI and disposable
Compose commands. The uninstalled [deployment workflow proposal](coolify-deploy-proposal.yml)
is a separate future design; it does not deploy this candidate.
