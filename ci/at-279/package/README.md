# Estimate Agent: portable private demo candidate

This package combines pinned public source commits with **synthetic data** for local
validation. It does not need an AI provider, key, account, or production database.
`SOURCE-SHAS.txt` pins the exact API and web commits; `sources/` is reconstructed
without `.git` or `.env*` files. This refreshed package is a candidate, not a
hosted demo or the original private tar.

## Start and check locally

Requirements: Docker Engine with BuildKit, Docker Compose v2, and Python 3 for the
verifier. The first build needs read access to official image registries, PyPI, and
npm. From this package directory:

```sh
docker compose config --quiet
python3 runtime/verify_compose.py
docker compose up --build -d
python3 runtime/smoke.py
```

Open **http://127.0.0.1:8080/demo** for the technical demo and
**http://127.0.0.1:8080/demo/review** for the synthetic scope-review screen.
Compose publishes only `127.0.0.1:8080`. Nginx serves Angular and proxies only
`GET /v1/demo/evaluate` to the API on the internal `backplane` network. The review
page loads a static same-origin fixture; it does not call a domain mutation API,
approve a BOM, persist a project, or make a commercial selection.

`seed` creates the synthetic store once in the `synthetic_store` volume; `api`
mounts it read-only and reopens it in a separate process. Container mode requires
`AT279_INTERNAL_CONTAINER_MODE=1`. The development API entry in
`sources/api/demo/preview_api.py` remains bound to `127.0.0.1`.

| Technical demo case | Query | Expected result |
| --- | --- | --- |
| Switch, 8 PoE | `?scenario=switch` | SW-16 compatible; SW-8 rejected for total ports |
| Switch, 12 PoE | `?scenario=switch&poe_ports_min=12` | No eligible purchasable selection |
| Camera, 4 units | `?scenario=camera&quantity=4` | Shared pool of 2 is insufficient |
| Camera, 2 units | `?scenario=camera&quantity=2` | CAM-POE compatible |
| UPS | `?scenario=ups` | Technically viable, with no offer |

For example: `curl -sS 'http://127.0.0.1:8080/v1/demo/evaluate?scenario=switch'`.
`runtime/smoke.py` also checks `/demo/review`, its synthetic fixture, disallowed
routes (404), invalid parameters (422), blocked POST (403), and the absence of CORS
and `storePath` exposure.

To check persistence without a second seed container, restart the stopped seed
container and then the API:

```sh
docker start -a at279-final-preview-seed-1
docker compose restart api
python3 runtime/smoke.py
```

The second seed result should contain `"store":"reused"`. If Compose chose a
different name, find it with `docker compose ps -a`. When done, remove **only this
synthetic stack** with `docker compose down -v --remove-orphans`. The two local
images may be removed separately with
`docker image rm at279-final-api:local at279-final-web:local`.

### Optional build CA

The normal build uses the builder's TLS trust store. Only if an approved proxy
requires an additional CA, pass its path explicitly. The helper does not read
environment variables. BuildKit mounts the certificate temporarily; it is not
copied into the image or package. Do not disable TLS.

```sh
sh runtime/prepare_build_ca.sh /path/to/approved-ca-bundle.pem
docker compose -f compose.yaml -f compose.tls-ca.yaml up --build -d
python3 runtime/smoke.py
rm runtime/build-ca.pem
```

### Python/Node fallback without Docker

Requirements: Python 3.12, `uv` 0.7.6, Node 24, and npm 11. Use two terminals.
In the first:

```sh
cd sources/api
uv run --frozen --extra demo python -m demo.agent.cli seed --store ./estimate-demo.rl
uv run --frozen --extra demo python -m demo.preview_api --store ./estimate-demo.rl --port 8001
```

In the second:

```sh
cd sources/app
npm ci --ignore-scripts --no-audit --no-fund
npm run demo:local
```

Open the local Angular URL reported by its server at `/demo` or `/demo/review`.
The development proxy sends `/v1/demo` to `127.0.0.1:8001`. With Python alone,
query `http://127.0.0.1:8001/v1/demo/evaluate?scenario=switch` and the other
technical cases above. `estimate-demo.rl` is disposable and contains only the
synthetic fixture.

## Limit before any private VPS deployment

**Do not use this loopback Compose file as a public deployment.** Neither Angular
nor its demo API has authentication. A later private setup needs a separate,
restricted resource, TLS at the proxy, confirmed server architecture and disk
space, and review of the generated Compose before it starts. Only the web service
should face the proxy on internal port 8080; do not add domains or host `ports:`
to `api` or `seed`. Verify the internal network, dedicated volume, one-shot seed,
access control, restart behavior, and removal using synthetic data. No hosting
panel, host, DNS, or live route has been inspected by this package validation.
