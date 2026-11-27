# AT-279: local validation of private demo candidates

This workflow builds and tests two **candidates**, without deploying either. The portable
package pins the internal API source to `dac8c64c314bb362c6254825c65640ba732ca168`
and refreshes only the web source to the clean `estimate-app` `develop` commit
`1b95205596f50d38ba60254319bb12584bde3a5a`. The package manifest and
`ARCHIVE-SHA256.txt` identify this refreshed snapshot; it is not the original
private tar. Sources are reconstructed from public commits during CI and are not
committed here. No secrets, hosted services, registry push, or artifacts are needed.

## Run the portable candidate locally

From the repository root, `ci/at-279/assemble.sh` reconstructs the pinned sources
and checks the exact package hash. From `ci/at-279/package`:

```sh
docker compose config --quiet
python3 runtime/verify_compose.py
docker compose up --build -d
python3 ../verify_runtime.py
python3 ../verify_browser.py
```

The package [README](package/README.md) has prerequisites, cleanup, and a local
Python/Node fallback. Compose exposes only the web service on
`127.0.0.1:8080`; API and seed have no host ports. The API reopens a synthetic
Relate store mounted read-only, while the seed remains a one-shot writer on the
internal `backplane` network. The checks exercise five `/demo` scenarios through
the same-origin proxy, then load `/demo/review` and its static
`/fixtures/at248-review.v1.json` asset. The review screen shows requested,
proposed, and pending synthetic lines for eight cameras, missing measurements,
and a change to ten. It does not approve, persist, price, or submit a project.
The browser check needs ChromeDriver and Chrome/Chromium; CI supplies them.

The Git-based candidate in this PR uses the same pinned API and refreshed web
source through [`coolify-compose.yaml`](coolify-compose.yaml). Its deployable
Compose has **no host ports**. CI adds a temporary loopback-only overlay, outside
the deployable Compose, to exercise `/demo/review` and the five technical cases
in ChromeDriver through the web proxy. See the [Git handoff](coolify-git-setup.md)
for source pins, the proposed `estimate-agent → production` destination, and
checks that remain for an authorized owner.

The immutable Git-based fallback remains at API commit
`dac8c64c314bb362c6254825c65640ba732ca168`, web commit
`d8a6d359bf909872ebfe48d52dfe5d8980c2c68b`, and repository Compose
commit `46e97c160963bf094f04d3d9eb4319b61c435441`. That **repository ref** is
unchanged; it retains the older web pin and is the explicit rollback source.
The Dockerfile in this PR's new commit pins the refreshed web source. The
portable package, refreshed Git candidate, and fallback have distinct identities.

No VPS or Coolify deployment has been performed. Before any private deployment,
its owner must inspect the actual generated Compose, access control, TLS, volume,
and proxy configuration. The workflow only verifies disposable local containers;
it does not prove the behavior of a particular hosting panel or public route.
