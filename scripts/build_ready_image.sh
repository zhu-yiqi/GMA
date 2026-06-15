#!/usr/bin/env bash
set -euo pipefail

# Build a GMA image, prepare a temporary runtime container, then commit the
# warmed container as a ready-to-run image. This captures backend baselines and
# the gma_ready_state emulator snapshot, which cannot be created in a normal
# docker build step.

BASE_IMAGE="${BASE_IMAGE:-gma:latest}"
READY_IMAGE="${READY_IMAGE:-gma:ready}"
CONTAINER="${CONTAINER:-gma_ready_builder}"
BACKEND_PORT="${BACKEND_PORT:-8199}"
ADB_PORT="${ADB_PORT:-5699}"
VNC_PORT="${VNC_PORT:-5999}"
BUILD=1
VERIFY_RESET=1
KEEP_CONTAINER=0
ENABLE_VNC=0

usage() {
  cat <<'EOF'
Usage: scripts/build_ready_image.sh [options]

Options:
  --base-image IMAGE     Base image to build/start (default: gma:latest)
  --ready-image IMAGE    Prepared output image tag (default: gma:ready)
  --container NAME       Temporary container name (default: gma_ready_builder)
  --backend-port PORT    Host backend port for preparation (default: 8199)
  --adb-port PORT        Host ADB relay port for preparation (default: 5699)
  --vnc-port PORT        Host noVNC port if --vnc is enabled (default: 5999)
  --no-build             Do not run docker build first
  --no-verify-reset      Skip final gma env reset verification before commit
  --keep-container       Keep the temporary container after commit/failure
  --vnc                  Enable noVNC in the temporary container
  -h, --help             Show this help

Environment overrides:
  BASE_IMAGE, READY_IMAGE, CONTAINER, BACKEND_PORT, ADB_PORT, VNC_PORT, GMA_BIN
EOF
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --base-image)
      BASE_IMAGE="$2"
      shift 2
      ;;
    --ready-image)
      READY_IMAGE="$2"
      shift 2
      ;;
    --container)
      CONTAINER="$2"
      shift 2
      ;;
    --backend-port)
      BACKEND_PORT="$2"
      shift 2
      ;;
    --adb-port)
      ADB_PORT="$2"
      shift 2
      ;;
    --vnc-port)
      VNC_PORT="$2"
      shift 2
      ;;
    --no-build)
      BUILD=0
      shift
      ;;
    --no-verify-reset)
      VERIFY_RESET=0
      shift
      ;;
    --keep-container)
      KEEP_CONTAINER=1
      shift
      ;;
    --vnc)
      ENABLE_VNC=1
      shift
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 2
      ;;
  esac
done

cd "$(dirname "$0")/.."

gma() {
  if [ -n "${GMA_BIN:-}" ]; then
    "$GMA_BIN" "$@"
  elif [ -x ./.venv/bin/gma ]; then
    ./.venv/bin/gma "$@"
  else
    uv run gma "$@"
  fi
}

wait_for_health() {
  local url="http://127.0.0.1:${BACKEND_PORT}/health"
  local deadline=$((SECONDS + 900))
  while [ "$SECONDS" -lt "$deadline" ]; do
    if curl -fsS "$url" >/dev/null 2>&1; then
      return 0
    fi
    sleep 5
  done
  echo "Timed out waiting for $url" >&2
  docker logs "$CONTAINER" --tail 200 >&2 || true
  return 1
}

cleanup_on_error() {
  if [ "$KEEP_CONTAINER" -eq 0 ]; then
    docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  fi
}
cleanup_on_exit() {
  local status=$?
  if [ "$status" -ne 0 ]; then
    cleanup_on_error
  fi
}
trap cleanup_on_exit EXIT

if [ "$BUILD" -eq 1 ]; then
  docker build -f docker/Dockerfile -t "$BASE_IMAGE" .
fi

docker rm -f "$CONTAINER" >/dev/null 2>&1 || true

vnc_args=()
if [ "$ENABLE_VNC" -eq 1 ]; then
  vnc_args=(-e ENABLE_VNC=true -p "${VNC_PORT}:5800")
else
  vnc_args=(-e ENABLE_VNC=false)
fi

docker run -d \
  --name "$CONTAINER" \
  --privileged \
  -p "${BACKEND_PORT}:8000" \
  -p "${ADB_PORT}:5556" \
  "${vnc_args[@]}" \
  "$BASE_IMAGE" >/dev/null

wait_for_health

gma env save-backend-baseline --url "http://localhost:${BACKEND_PORT}"

if [ "$VERIFY_RESET" -eq 1 ]; then
  gma env reset --url "http://localhost:${BACKEND_PORT}"
fi

docker exec "$CONTAINER" sh -lc 'adb emu kill >/dev/null 2>&1 || true; sync' >/dev/null 2>&1 || true
docker stop -t 60 "$CONTAINER" >/dev/null
docker commit "$CONTAINER" "$READY_IMAGE" >/dev/null

if [ "$KEEP_CONTAINER" -eq 0 ]; then
  docker rm -f "$CONTAINER" >/dev/null
fi

trap - EXIT
echo "Prepared image: $READY_IMAGE"
