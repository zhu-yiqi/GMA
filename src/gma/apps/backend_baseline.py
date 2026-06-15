from __future__ import annotations

import contextlib
import re
from dataclasses import dataclass
from typing import TYPE_CHECKING, Iterator

from loguru import logger

from gma.apps._shell import run_bash

if TYPE_CHECKING:
    from gma.runtime.controller import AndroidController


BASELINE_ROOT = "/tmp/gma_backend_baselines"
_DISABLED = 0


@dataclass(frozen=True)
class BackendBaselineSpec:
    label: str
    project_dir: str
    compose_up: str
    compose_down: str
    containers: tuple[str, ...] = ()
    volume_prefixes: tuple[str, ...] = ()
    health_urls: tuple[str, ...] = ()
    wait_seconds: int = 180

    @property
    def key(self) -> str:
        return re.sub(r"[^a-z0-9]+", "-", self.label.lower()).strip("-")


@contextlib.contextmanager
def baseline_disabled() -> Iterator[None]:
    global _DISABLED
    _DISABLED += 1
    try:
        yield
    finally:
        _DISABLED -= 1


def _disabled() -> bool:
    return _DISABLED > 0


def _shell_words(values: tuple[str, ...]) -> str:
    # These names are fixed Docker identifiers without whitespace. Keep the
    # variable contents unquoted so `for item in $ITEMS` sees the real names,
    # not quote characters embedded into the names.
    return " ".join(values)


def _health_script(spec: BackendBaselineSpec) -> str:
    if not spec.health_urls:
        return "true"
    checks = " && ".join(f"curl -fsS --max-time 5 {url} >/dev/null 2>&1" for url in spec.health_urls)
    return f"for _ in $(seq 1 {spec.wait_seconds}); do if {checks}; then exit 0; fi; sleep 1; done; exit 1"


def restore_backend_baseline(client: AndroidController, spec: BackendBaselineSpec) -> bool:
    """Restore a clean backend baseline if one has been saved for this app."""
    if _disabled():
        return False
    exists_script = f"""
set -euo pipefail
BASE={BASELINE_ROOT}/{spec.key}
if [ -f "$BASE/project.tar" ]; then
  echo present
else
  echo missing
fi
"""
    if run_bash(client, exists_script, timeout=20).strip() != "present":
        logger.info(f"{spec.label} backend baseline unavailable")
        return False
    script = f"""
set -euo pipefail
BASE={BASELINE_ROOT}/{spec.key}
PROJECT_DIR={spec.project_dir!r}
PROJECT_PARENT=$(dirname "$PROJECT_DIR")
PROJECT_NAME=$(basename "$PROJECT_DIR")
CONTAINERS="{_shell_words(spec.containers)}"
VOLUME_PREFIXES="{_shell_words(spec.volume_prefixes)}"

if [ -d "$PROJECT_DIR" ]; then
  {spec.compose_down} >/dev/null 2>&1 || true
fi
if [ -n "$CONTAINERS" ]; then
  # shellcheck disable=SC2086
  docker rm -f $CONTAINERS >/dev/null 2>&1 || true
fi

for prefix in $VOLUME_PREFIXES; do
  for volume in $(docker volume ls --format '{{{{.Name}}}}' | grep -E "^${{prefix}}_" || true); do
    docker volume rm -f "$volume" >/dev/null 2>&1 || true
  done
done

rm -rf "$PROJECT_DIR"
mkdir -p "$PROJECT_PARENT"
tar -C "$PROJECT_PARENT" -xf "$BASE/project.tar"

if [ -f "$BASE/volumes.txt" ]; then
  while IFS= read -r volume; do
    [ -n "$volume" ] || continue
    archive="$BASE/volumes/${{volume}}.tar"
    [ -f "$archive" ] || continue
    docker volume create "$volume" >/dev/null
    mountpoint=$(docker volume inspect "$volume" --format '{{{{.Mountpoint}}}}')
    rm -rf "${{mountpoint:?}}/"*
    tar -C "$mountpoint" -xf "$archive"
  done < "$BASE/volumes.txt"
fi

if [ -d "$BASE/images" ]; then
  for image_archive in "$BASE"/images/*.tar; do
    [ -f "$image_archive" ] || continue
    docker load -i "$image_archive" >/dev/null
  done
fi

{spec.compose_up} >/dev/null 2>&1
{_health_script(spec)}
"""
    try:
        run_bash(client, script, timeout=max(120, spec.wait_seconds + 90))
        logger.info(f"Restored {spec.label} backend from baseline")
        return True
    except Exception as exc:
        logger.info(f"{spec.label} backend baseline unavailable or failed: {exc}")
        return False


def save_backend_baseline(client: AndroidController, spec: BackendBaselineSpec) -> None:
    """Save the currently clean backend state as the reusable reset baseline."""
    script = f"""
set -euo pipefail
BASE={BASELINE_ROOT}/{spec.key}
TMP="${{BASE}}.tmp"
PROJECT_DIR={spec.project_dir!r}
PROJECT_PARENT=$(dirname "$PROJECT_DIR")
PROJECT_NAME=$(basename "$PROJECT_DIR")
CONTAINERS="{_shell_words(spec.containers)}"
VOLUME_PREFIXES="{_shell_words(spec.volume_prefixes)}"

if [ ! -d "$PROJECT_DIR" ]; then
  echo "Project directory missing: $PROJECT_DIR" >&2
  exit 1
fi

rm -rf "$TMP"
mkdir -p "$TMP/volumes" "$TMP/images"

if [ -d "$PROJECT_DIR" ]; then
  {spec.compose_down} >/dev/null 2>&1 || true
fi
if [ -n "$CONTAINERS" ]; then
  # shellcheck disable=SC2086
  docker rm -f $CONTAINERS >/dev/null 2>&1 || true
fi

# Dereference the top-level project path. Some deploy bundles expose the
# project directory as a symlink into an extracted export root; saving the
# symlink alone makes the baseline unusable in a freshly committed image.
tar -C "$PROJECT_PARENT" -chf "$TMP/project.tar" "$PROJECT_NAME"
: > "$TMP/images.txt"
if [ -f "$PROJECT_DIR/docker-compose.yml" ]; then
  (cd "$PROJECT_DIR" && docker compose -f docker-compose.yml config --images | sort -u) > "$TMP/images.txt" || : > "$TMP/images.txt"
fi
while IFS= read -r image; do
  [ -n "$image" ] || continue
  if ! docker image inspect "$image" >/dev/null 2>&1; then
    continue
  fi
  safe=$(printf "%s" "$image" | sed "s/[^A-Za-z0-9_.-]/_/g")
  docker save -o "$TMP/images/${{safe}}.tar" "$image"
done < "$TMP/images.txt"

: > "$TMP/volumes.txt"
for prefix in $VOLUME_PREFIXES; do
  for volume in $(docker volume ls --format '{{{{.Name}}}}' | grep -E "^${{prefix}}_" || true); do
    mountpoint=$(docker volume inspect "$volume" --format '{{{{.Mountpoint}}}}')
    tar -C "$mountpoint" -cf "$TMP/volumes/${{volume}}.tar" .
    echo "$volume" >> "$TMP/volumes.txt"
  done
done

rm -rf "$BASE"
mv "$TMP" "$BASE"

{spec.compose_up} >/dev/null 2>&1
{_health_script(spec)}
"""
    run_bash(client, script, timeout=max(180, spec.wait_seconds + 180))
    logger.info(f"Saved {spec.label} backend baseline")
