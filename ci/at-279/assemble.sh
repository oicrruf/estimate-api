#!/usr/bin/env bash
set -euo pipefail

repo_root="$(git rev-parse --show-toplevel)"
package="$repo_root/ci/at-279/package"
api_sha="$(awk '$1 == "oicrruf/estimate-api" && $2 == "develop" { print $3 }' "$package/SOURCE-SHAS.txt")"
app_sha="$(awk '$1 == "oicrruf/estimate-app" && $2 == "develop" { print $3 }' "$package/SOURCE-SHAS.txt")"
[[ "$api_sha" =~ ^[0-9a-f]{40}$ && "$app_sha" =~ ^[0-9a-f]{40}$ ]]

mkdir -p "$package/sources/api" "$package/sources/app"
test -z "$(find "$package/sources" -mindepth 2 -print -quit)" || {
  echo 'Las fuentes deben comenzar vacías' >&2
  exit 2
}

test "$(git -C "$repo_root" rev-parse "$api_sha^{commit}")" = "$api_sha"
git -C "$repo_root" archive "$api_sha" | tar -x -C "$package/sources/api"

scratch="$(mktemp -d)"
trap 'rm -rf "$scratch"' EXIT
git -C "$scratch" init --quiet
git -C "$scratch" remote add origin https://github.com/oicrruf/estimate-app.git
git -C "$scratch" fetch --quiet --no-tags --depth 1 origin "$app_sha"
test "$(git -C "$scratch" rev-parse FETCH_HEAD)" = "$app_sha"
git -C "$scratch" archive "$app_sha" | tar -x -C "$package/sources/app"
find "$package/sources" -type f -name '.env*' -delete

python3 "$repo_root/ci/at-279/verify_bundle.py"
