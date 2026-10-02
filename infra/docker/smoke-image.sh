#!/bin/sh
# Prueba de humo de una imagen: la arranca, espera una respuesta 2xx y elimina el contenedor
# siempre, también si falla. La usan `make check` y CI (backend.yml, frontend.yml), así que
# ambos prueban exactamente lo mismo.
# Uso: smoke-image.sh <imagen> <puerto del contenedor> <ruta> [opciones de `docker run`…]
# SMOKE_HEADER_PATTERN (opcional): expresión regular extendida que debe cumplir alguna cabecera
# de la respuesta, sin distinguir mayúsculas (p. ej., la CSP del frontend).
# El puerto del host lo elige Docker en 127.0.0.1 y el nombre es único: no colisiona con el
# stack local. Los secretos se pasan por nombre (`-e VARIABLE`), nunca con su valor.
set -eu
image="$1" port="$2" path="$3"
shift 3
name="crm-smoke-$$"

cleanup() { docker rm -f "$name" >/dev/null 2>&1 || true; }
trap cleanup EXIT
trap 'exit 1' HUP INT TERM

docker run -d --name "$name" -p "127.0.0.1::$port" "$@" "$image" >/dev/null
i=0
while [ "$i" -lt 30 ]; do
  address="$(docker port "$name" "$port/tcp" 2>/dev/null | head -n 1)" || address=""
  if [ -n "$address" ] && curl -sf -o /dev/null "http://$address$path"; then
    if [ -n "${SMOKE_HEADER_PATTERN:-}" ] &&
      ! curl -sf -o /dev/null -D - "http://$address$path" | tr -d '\r' | grep -Eiq -- "$SMOKE_HEADER_PATTERN"; then
      echo "smoke FAIL: $image $path no envía la cabecera esperada" >&2
      exit 1
    fi
    echo "smoke OK: $image $path"
    exit 0
  fi
  i=$((i + 1))
  sleep 1
done
docker logs "$name" >&2 || true
echo "smoke FAIL: $image $path" >&2
exit 1
