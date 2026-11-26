#!/bin/sh
set -eu
if [ "$#" -ne 1 ]; then
  echo "Uso: sh runtime/prepare_build_ca.sh /ruta/al/ca-bundle-aprobado.pem" >&2
  exit 2
fi
source_bundle="$1"
test -f "$source_bundle" && test -r "$source_bundle" || { echo "Falta CA bundle legible" >&2; exit 2; }
test "$(realpath "$source_bundle")" != "$(realpath -m runtime/build-ca.pem)" || { echo "La fuente y el destino coinciden" >&2; exit 2; }
install -m 600 "$source_bundle" runtime/build-ca.pem
sha256sum runtime/build-ca.pem
