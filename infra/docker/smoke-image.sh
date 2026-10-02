#!/bin/sh
# Prueba de humo de una imagen: la arranca, espera una respuesta 2xx y elimina el contenedor
# siempre, también si falla. La usan `make check` y CI (backend.yml, frontend.yml), así que
# ambos prueban exactamente lo mismo.
# Uso: smoke-image.sh <imagen> <puerto del contenedor> <ruta> [opciones de `docker run`…]
# SMOKE_CHECK (opcional): comando que recibe la URL base del contenedor como último argumento
# y debe terminar con 0 (p. ej., las cabeceras de seguridad del frontend).
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
    if [ -n "${SMOKE_CHECK:-}" ] && ! $SMOKE_CHECK "http://$address"; then
      echo "smoke FAIL: $image no pasa la comprobación: $SMOKE_CHECK" >&2
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
