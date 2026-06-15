from __future__ import annotations

import base64
import hashlib
import json
import re
import shlex
import subprocess
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING

import requests

from gma.apps._shell import run_bash
from gma.apps.backend_baseline import BackendBaselineSpec, restore_backend_baseline

if TYPE_CHECKING:
    from gma.runtime.controller import AndroidController


ELEMENTX_BACKEND_ROOT = "/tmp/gma_elementx_export"
ELEMENTX_PROJECT_DIR = f"{ELEMENTX_BACKEND_ROOT}/WhatsApp/synapse-docker"
ELEMENTX_HEALTH_URL = "http://localhost:8021/_matrix/client/versions"
ELEMENTX_BASE_URL = "http://localhost:8021"
ELEMENTX_COMPOSE_PROJECT = "gma-elementx"
ELEMENTX_HOMESERVER_YAML = Path(f"{ELEMENTX_PROJECT_DIR}/data/homeserver.yaml")
DEFAULT_ELEMENTX_PASSWORD = "password"
ELEMENTX_SERVER_URL = "http://10.0.2.2:8021"
ELEMENTX_SERVER_HOST = "10.0.2.2:8021"
ELEMENTX_DEFAULT_USERNAME = "testuser"
ELEMENTX_DEFAULT_PASSWORD = "testpass123"
ELEMENTX_DEFAULT_DISPLAY_NAME = "owner"

_SERVER_NAME_CACHE: str | None = None
_TOKEN_CACHE: dict[tuple[str, str], str] = {}
_CLOCK_OVERRIDE_PATCHED = False


def _elementx_compose(command: str) -> str:
    return (
        f"cd {ELEMENTX_PROJECT_DIR} && "
        f"docker compose --project-name {ELEMENTX_COMPOSE_PROJECT} -f docker-compose.yml "
        f"{command}"
    )


ELEMENTX_BASELINE = BackendBaselineSpec(
    label="ElementX",
    project_dir=ELEMENTX_PROJECT_DIR,
    compose_up=_elementx_compose("up -d"),
    compose_down=_elementx_compose("down --remove-orphans"),
    containers=("synapse", "synapse-db"),
    volume_prefixes=(ELEMENTX_COMPOSE_PROJECT,),
    health_urls=(ELEMENTX_HEALTH_URL,),
    wait_seconds=180,
)


def reset_elementx_backend(client: AndroidController) -> None:
    global _CLOCK_OVERRIDE_PATCHED, _SERVER_NAME_CACHE
    _TOKEN_CACHE.clear()
    _SERVER_NAME_CACHE = None
    _CLOCK_OVERRIDE_PATCHED = False
    if restore_backend_baseline(client, ELEMENTX_BASELINE):
        return
    run_bash(
        client,
        f"""
set -euo pipefail
if [ -d {ELEMENTX_PROJECT_DIR} ]; then
  {_elementx_compose('down -v --remove-orphans >/dev/null 2>&1 || true')}
fi
docker volume rm {ELEMENTX_COMPOSE_PROJECT}_postgres_data >/dev/null 2>&1 || true
rm -rf {ELEMENTX_BACKEND_ROOT}
""",
        timeout=120,
    )


def ensure_elementx_backend(client: AndroidController) -> None:
    run_bash(
        client,
        f"""
set -euo pipefail

project_tar="/app/dev/whatsapp-project.tar.gz"
if [ ! -f "$project_tar" ]; then
  project_tar="/app/mobileworld/whatsapp-project.tar.gz"
fi
if [ ! -f "$project_tar" ]; then
  echo "ElementX project tarball not found" >&2
  exit 1
fi

postgres_tar="/app/dev/whatsapp-postgres-volume.tar.gz"
if [ ! -f "$postgres_tar" ]; then
  postgres_tar="/app/mobileworld/whatsapp-postgres-volume.tar.gz"
fi
if [ ! -f "$postgres_tar" ]; then
  echo "ElementX postgres volume tarball not found" >&2
  exit 1
fi

patch_synapse_config() {{
python3 - <<'PY'
from pathlib import Path

path = Path({str(ELEMENTX_HOMESERVER_YAML)!r})
if not path.exists():
    print("missing")
    raise SystemExit(0)

text = path.read_text()
changed = False
if "search_all_users: true" not in text or "prefer_local_users: true" not in text:
    if not text.endswith("\\n"):
        text += "\\n"
    text += (
        "\\nuser_directory:\\n"
        "  enabled: true\\n"
        "  search_all_users: true\\n"
        "  prefer_local_users: true\\n"
    )
    changed = True
if "rc_login:" not in text:
    if not text.endswith("\\n"):
        text += "\\n"
    text += (
        "\\nrc_login:\\n"
        "  address:\\n"
        "    per_second: 1000\\n"
        "    burst_count: 1000\\n"
        "  account:\\n"
        "    per_second: 1000\\n"
        "    burst_count: 1000\\n"
        "  failed_attempts:\\n"
        "    per_second: 1000\\n"
        "    burst_count: 1000\\n"
    )
    changed = True
if changed:
    path.write_text(text)
    print("changed")
else:
    print("ok")
PY
}}

wait_backend_ready() {{
  for _ in $(seq 1 90); do
    if curl -fsS {ELEMENTX_HEALTH_URL} >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  return 1
}}

if [ -d {ELEMENTX_PROJECT_DIR} ]; then
  patch_status=$(patch_synapse_config)
  if curl -fsS {ELEMENTX_HEALTH_URL} >/dev/null 2>&1; then
    if [ "$patch_status" = "ok" ]; then
      exit 0
    fi
    {_elementx_compose('restart synapse >/dev/null 2>&1 || true')}
    {_elementx_compose('up -d synapse >/dev/null 2>&1 || true')}
    if wait_backend_ready; then
      exit 0
    fi
    echo "ElementX backend did not become ready after updating Synapse config" >&2
    exit 1
  fi
fi

rm -rf {ELEMENTX_BACKEND_ROOT}
mkdir -p {ELEMENTX_BACKEND_ROOT}
tar xzf "$project_tar" -C {ELEMENTX_BACKEND_ROOT}
patch_synapse_config >/dev/null
{_elementx_compose('up -d db >/dev/null 2>&1')}
for _ in $(seq 1 60); do
  if {_elementx_compose('exec -T db pg_isready -U synapse >/dev/null 2>&1')}; then
    break
  fi
  sleep 2
done
{_elementx_compose('stop db >/dev/null 2>&1 || true')}
VOLUME_PATH=$(docker volume inspect {ELEMENTX_COMPOSE_PROJECT}_postgres_data --format '{{{{.Mountpoint}}}}')
rm -rf "${{VOLUME_PATH:?}}/"*
tar xzf "$postgres_tar" -C "$VOLUME_PATH"
{_elementx_compose('up -d >/dev/null 2>&1')}
if wait_backend_ready; then
  exit 0
fi
echo "ElementX backend did not become ready" >&2
exit 1
""",
        timeout=300,
    )


def elementx_server_name() -> str:
    global _SERVER_NAME_CACHE
    if _SERVER_NAME_CACHE:
        return _SERVER_NAME_CACHE
    if ELEMENTX_HOMESERVER_YAML.exists():
        for line in ELEMENTX_HOMESERVER_YAML.read_text().splitlines():
            if line.strip().startswith("server_name:"):
                value = line.split(":", 1)[1].strip().strip('"').strip("'")
                if value:
                    _SERVER_NAME_CACHE = value
                    return value
    _SERVER_NAME_CACHE = "101.37.229.242"
    return _SERVER_NAME_CACHE


def elementx_user_id(username: str) -> str:
    return f"@{username}:{elementx_server_name()}"


def elementx_room_alias(alias_localpart: str) -> str:
    return f"#{alias_localpart}:{elementx_server_name()}"


def slugify_room_alias(name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    if not normalized:
        normalized = "room"
    digest = hashlib.sha1(name.encode("utf-8")).hexdigest()[:8]
    return f"gma-{normalized[:40]}-{digest}"


def _matrix_request(
    method: str,
    path: str,
    *,
    access_token: str | None = None,
    params: dict | None = None,
    json_payload: dict | None = None,
    data: bytes | None = None,
    headers: dict | None = None,
    expected: tuple[int, ...] = (200,),
):
    request_headers = dict(headers or {})
    if access_token:
        request_headers["Authorization"] = f"Bearer {access_token}"
    response = requests.request(
        method,
        f"{ELEMENTX_BASE_URL}{path}",
        params=params,
        json=json_payload,
        data=data,
        headers=request_headers,
        timeout=30,
    )
    if response.status_code not in expected:
        raise RuntimeError(
            f"ElementX API {method} {path} failed: {response.status_code} {response.text}"
        )
    if not response.text:
        return None
    try:
        return response.json()
    except json.JSONDecodeError:
        return response.text


def _elementx_account_data_url(user_id: str, event_type: str) -> str:
    encoded_user = requests.utils.quote(user_id, safe="")
    encoded_type = requests.utils.quote(event_type, safe="")
    return f"{ELEMENTX_BASE_URL}/_matrix/client/v3/user/{encoded_user}/account_data/{encoded_type}"


def _elementx_direct_account_data(access_token: str, user_id: str) -> dict[str, list[str]]:
    response = requests.get(
        _elementx_account_data_url(user_id, "m.direct"),
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=30,
    )
    if response.status_code == 404:
        return {}
    if response.status_code != 200:
        raise RuntimeError(
            f"ElementX account data GET m.direct failed: {response.status_code} {response.text}"
        )
    payload = response.json()
    if not isinstance(payload, dict):
        return {}
    direct: dict[str, list[str]] = {}
    for other_user_id, room_ids in payload.items():
        if isinstance(other_user_id, str) and isinstance(room_ids, list):
            direct[other_user_id] = [room_id for room_id in room_ids if isinstance(room_id, str)]
    return direct


def _mark_elementx_direct_room(
    *,
    access_token: str,
    user_id: str,
    other_user_id: str,
    room_id: str,
) -> None:
    direct = _elementx_direct_account_data(access_token, user_id)
    existing = [candidate for candidate in direct.get(other_user_id, []) if candidate != room_id]
    direct[other_user_id] = [room_id, *existing]
    _matrix_request(
        "PUT",
        f"/_matrix/client/v3/user/{requests.utils.quote(user_id, safe='')}/account_data/m.direct",
        access_token=access_token,
        json_payload=direct,
        expected=(200,),
    )


def _elementx_room_present_members(room_id: str, access_token: str) -> set[str]:
    state = _matrix_request(
        "GET",
        f"/_matrix/client/v3/rooms/{requests.utils.quote(room_id, safe='')}/state",
        access_token=access_token,
        expected=(200,),
    )
    return {
        event.get("state_key")
        for event in state
        if event.get("type") == "m.room.member"
        and event.get("state_key")
        and (event.get("content") or {}).get("membership") in {"join", "invite"}
    }


def _resolve_elementx_direct_room_id(
    *,
    access_token: str,
    user_id: str,
    other_user_id: str,
) -> str | None:
    expected_members = {user_id, other_user_id}
    direct = _elementx_direct_account_data(access_token, user_id)
    for room_id in direct.get(other_user_id, []):
        try:
            if _elementx_room_present_members(room_id, access_token) == expected_members:
                return room_id
        except Exception:
            continue

    joined = _matrix_request(
        "GET",
        "/_matrix/client/v3/joined_rooms",
        access_token=access_token,
        expected=(200,),
    )
    for room_id in joined.get("joined_rooms", []):
        try:
            if _elementx_room_present_members(room_id, access_token) == expected_members:
                return room_id
        except Exception:
            continue
    return None


def _ensure_elementx_clock_override_patch(client: AndroidController) -> None:
    """Allow asset insertion to create Matrix events with a controlled clock.

    Matrix event IDs are derived from the event JSON. Rewriting
    ``origin_server_ts`` after insertion corrupts the event, so timestamped
    assets must make Synapse use the target time while creating the event.
    """

    global _CLOCK_OVERRIDE_PATCHED
    # The Synapse container can be recreated by `gma env reset` while the GMA
    # server process stays alive. Always validate the patch in the live
    # container instead of trusting this process-local flag.

    run_bash(
        client,
        f"""
set -euo pipefail
cd {ELEMENTX_PROJECT_DIR}
changed=$(docker compose --project-name {ELEMENTX_COMPOSE_PROJECT} -f docker-compose.yml exec -T synapse python - <<'PY'
from pathlib import Path

path = Path('/usr/local/lib/python3.13/site-packages/synapse/util/clock.py')
text = path.read_text()
marker = 'GMA_SYNAPSE_TIME_MS'
if marker in text:
    print('ok')
    raise SystemExit(0)

if 'import os\\n' not in text:
    text = text.replace('import logging\\n', 'import logging\\nimport os\\n', 1)

old = '''    def time_msec(self) -> int:
        \"""Returns the current system time in milliseconds since epoch.\"""
        return int(self.time() * 1000)
'''
new = '''    def time_msec(self) -> int:
        \"""Returns the current system time in milliseconds since epoch.\"""
        override = os.environ.get("GMA_SYNAPSE_TIME_MS")
        if override is None:
            try:
                with open("/tmp/gma_synapse_time_ms", "r", encoding="utf-8") as handle:
                    override = handle.read().strip()
            except OSError:
                override = None
        if override:
            try:
                return int(override)
            except ValueError:
                pass
        return int(self.time() * 1000)
'''
if old not in text:
    raise RuntimeError('Could not patch Synapse clock.py time_msec')
path.write_text(text.replace(old, new, 1))
print('changed')
PY
)
if [ "$changed" = "changed" ]; then
  docker compose --project-name {ELEMENTX_COMPOSE_PROJECT} -f docker-compose.yml restart synapse >/dev/null
fi
for _ in $(seq 1 90); do
  if curl -fsS {ELEMENTX_HEALTH_URL} >/dev/null 2>&1; then
    exit 0
  fi
  sleep 1
done
echo "ElementX Synapse did not become ready after clock patch" >&2
exit 1
""",
        timeout=180,
    )
    _CLOCK_OVERRIDE_PATCHED = True


@contextmanager
def elementx_clock_override(
    client: AndroidController, created_at_ms: int | None
):
    if created_at_ms is None:
        yield
        return

    ensure_elementx_backend(client)
    _ensure_elementx_clock_override_patch(client)
    timestamp = int(created_at_ms)
    set_clock_command = shlex.quote(
        "printf '%s\\n' " + shlex.quote(str(timestamp)) + " > /tmp/gma_synapse_time_ms"
    )
    run_bash(
        client,
        f"""
set -euo pipefail
cd {ELEMENTX_PROJECT_DIR}
docker compose --project-name {ELEMENTX_COMPOSE_PROJECT} -f docker-compose.yml exec -T synapse sh -lc \
  {set_clock_command}
""",
        timeout=30,
    )
    try:
        yield
    finally:
        run_bash(
            client,
            f"""
set -euo pipefail
cd {ELEMENTX_PROJECT_DIR}
docker compose --project-name {ELEMENTX_COMPOSE_PROJECT} -f docker-compose.yml exec -T synapse sh -lc \
  'rm -f /tmp/gma_synapse_time_ms'
""",
            timeout=30,
        )


def _rate_limit_delay(response: requests.Response) -> float | None:
    try:
        body = response.json()
    except Exception:
        return None
    if body.get("errcode") != "M_LIMIT_EXCEEDED":
        return None
    retry_ms = body.get("retry_after_ms")
    try:
        return min(max(float(retry_ms) / 1000.0, 1.0), 60.0)
    except (TypeError, ValueError):
        return 5.0


def _login(username: str, password: str) -> str | None:
    last_response: requests.Response | None = None
    for _ in range(3):
        response = requests.post(
            f"{ELEMENTX_BASE_URL}/_matrix/client/v3/login",
            json={
                "type": "m.login.password",
                "identifier": {"type": "m.id.user", "user": username},
                "password": password,
            },
            timeout=30,
        )
        if response.status_code == 200:
            return response.json()["access_token"]
        if response.status_code in {401, 403}:
            return None
        delay = _rate_limit_delay(response)
        if delay is None:
            raise RuntimeError(f"ElementX login failed: {response.status_code} {response.text}")
        last_response = response
        time.sleep(delay + 1)
    assert last_response is not None
    raise RuntimeError(f"ElementX login failed: {last_response.status_code} {last_response.text}")


def _fetch_existing_access_token(username: str) -> str | None:
    user_id = elementx_user_id(username)
    cmd = (
        f"cd {ELEMENTX_PROJECT_DIR} && "
        f"docker compose --project-name {ELEMENTX_COMPOSE_PROJECT} -f docker-compose.yml "
        "exec -T db psql -U synapse -d synapse -At -c "
        + shlex.quote(
            f"select token from access_tokens where user_id = '{user_id}' order by id desc limit 1;"
        )
    )
    try:
        token = subprocess.check_output(["sh", "-lc", cmd], text=True).strip()
    except Exception:
        return None
    return token or None


def _token_is_valid(token: str) -> bool:
    try:
        _matrix_request(
            "GET",
            "/_matrix/client/v3/account/whoami",
            access_token=token,
            expected=(200,),
        )
        return True
    except Exception:
        return False


def ensure_elementx_user(
    client: AndroidController,
    username: str,
    *,
    password: str = DEFAULT_ELEMENTX_PASSWORD,
    display_name: str | None = None,
) -> str:
    ensure_elementx_backend(client)
    cache_key = (username, password)
    token = _TOKEN_CACHE.get(cache_key)
    if token and not _token_is_valid(token):
        _TOKEN_CACHE.pop(cache_key, None)
        token = None
    if token is None:
        token = _fetch_existing_access_token(username)
        if token and not _token_is_valid(token):
            token = None
    if token is None:
        response = None
        for _ in range(3):
            response = requests.post(
                f"{ELEMENTX_BASE_URL}/_matrix/client/v3/register",
                json={
                    "username": username,
                    "password": password,
                    "auth": {"type": "m.login.dummy"},
                },
                timeout=30,
            )
            delay = _rate_limit_delay(response)
            if delay is None:
                break
            time.sleep(delay + 1)
        assert response is not None
        if response.status_code == 200:
            token = response.json()["access_token"]
        else:
            body = {}
            try:
                body = response.json()
            except Exception:
                pass
            if body.get("errcode") != "M_USER_IN_USE":
                raise RuntimeError(
                    f"ElementX register failed: {response.status_code} {response.text}"
                )
            token = _login(username, password)
            if token is None:
                raise RuntimeError(f"ElementX user exists but login failed for {username}")
    _TOKEN_CACHE[cache_key] = token
    if display_name:
        _matrix_request(
            "PUT",
            f"/_matrix/client/v3/profile/{elementx_user_id(username)}/displayname",
            access_token=token,
            json_payload={"displayname": display_name},
            expected=(200,),
        )
    return token


def _default_password_for_username(username: str) -> str:
    if username == ELEMENTX_DEFAULT_USERNAME:
        return ELEMENTX_DEFAULT_PASSWORD
    return DEFAULT_ELEMENTX_PASSWORD


def _set_elementx_display_name_via_client(
    client: AndroidController,
    username: str,
    password: str,
    display_name: str | None,
) -> None:
    if not display_name:
        return
    script = r"""
set -euo pipefail
python3 - <<'PY'
import json
import time
from pathlib import Path
from urllib import error, parse, request

BASE = __BASE__
USERNAME = __USERNAME__
PASSWORD = __PASSWORD__
DISPLAY_NAME = __DISPLAY_NAME__
HOMESERVER_YAML = Path(__HOMESERVER_YAML__)


def request_json(method, path, payload=None, token=None, expected=(200,)):
    data = None
    headers = {}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["Authorization"] = "Bearer " + token
    req = request.Request(BASE + path, data=data, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            if resp.status not in expected:
                raise RuntimeError(f"{method} {path} failed: {resp.status} {body}")
            return json.loads(body or "{}")
    except error.HTTPError as exc:
        body = exc.read().decode("utf-8")
        if exc.code not in expected:
            raise RuntimeError(f"{method} {path} failed: {exc.code} {body}")
        return json.loads(body or "{}")


for _ in range(90):
    try:
        with request.urlopen(BASE + "/_matrix/client/versions", timeout=2):
            break
    except Exception:
        time.sleep(2)
else:
    raise RuntimeError("ElementX backend did not become reachable")

try:
    request_json(
        "POST",
        "/_matrix/client/v3/register",
        {"username": USERNAME, "password": PASSWORD, "auth": {"type": "m.login.dummy"}},
    )
except RuntimeError as exc:
    if "M_USER_IN_USE" not in str(exc):
        raise

login = request_json(
    "POST",
    "/_matrix/client/v3/login",
    {
        "type": "m.login.password",
        "identifier": {"type": "m.id.user", "user": USERNAME},
        "password": PASSWORD,
    },
)

server_name = "101.37.229.242"
if HOMESERVER_YAML.exists():
    for line in HOMESERVER_YAML.read_text().splitlines():
        if line.strip().startswith("server_name:"):
            value = line.split(":", 1)[1].strip().strip('"').strip("'")
            if value:
                server_name = value
                break

user_id = f"@{USERNAME}:{server_name}"
request_json(
    "PUT",
    "/_matrix/client/v3/profile/" + parse.quote(user_id, safe="") + "/displayname",
    {"displayname": DISPLAY_NAME},
    token=login["access_token"],
)
PY
"""
    script = (
        script.replace("__BASE__", repr(ELEMENTX_BASE_URL))
        .replace("__USERNAME__", repr(username))
        .replace("__PASSWORD__", repr(password))
        .replace("__DISPLAY_NAME__", repr(display_name))
        .replace("__HOMESERVER_YAML__", repr(str(ELEMENTX_HOMESERVER_YAML)))
    )
    run_bash(client, script, timeout=240)




def clear_elementx_user_state(
    client: AndroidController,
    username: str = ELEMENTX_DEFAULT_USERNAME,
) -> None:
    """Remove user-visible rooms/invites while preserving the Android login session.

    Clearing Android app data fixes stale ElementX timelines but forces a slow
    full UI login. Leaving and forgetting rooms on the homeserver keeps the
    mobile session valid while making the synced room list empty for the next
    task/reset. The Matrix backend lives inside the GMA container, so the
    cleanup executes there instead of using host-local HTTP.
    """
    ensure_elementx_backend(client)
    password = _default_password_for_username(username)
    server_name = elementx_server_name()
    script = r"""
set -euo pipefail
python3 - <<'PY'
import json
import shlex
import subprocess
from urllib.parse import quote

import requests

base = __BASE__
project_dir = __PROJECT_DIR__
compose_project = __COMPOSE_PROJECT__
username = __USERNAME__
password = __PASSWORD__
server_name = __SERVER_NAME__


def sql_literal(value: str) -> str:
    return value.replace("'", "''")


def run_sql(query: str) -> list[str]:
    cmd = (
        f"cd {project_dir} && "
        f"docker compose --project-name {compose_project} -f docker-compose.yml "
        "exec -T db psql -U synapse -d synapse -At -c "
        + shlex.quote(query)
    )
    return [
        line
        for line in subprocess.check_output(["sh", "-lc", cmd], text=True).splitlines()
        if line.strip()
    ]


def db_token() -> str | None:
    user_id = f"@{username}:{server_name}"
    query = (
        "select token from access_tokens where user_id = '"
        + sql_literal(user_id)
        + "' order by id desc limit 1;"
    )
    try:
        rows = run_sql(query)
        return rows[0] if rows else None
    except Exception:
        return None


def login_token() -> str | None:
    response = requests.post(
        base + "/_matrix/client/v3/login",
        json={
            "type": "m.login.password",
            "identifier": {"type": "m.id.user", "user": username},
            "password": password,
        },
        timeout=30,
    )
    if response.status_code == 200:
        return response.json()["access_token"]
    if response.status_code in {401, 403}:
        return None
    response.raise_for_status()
    return None


def request(method: str, path: str, *, expected=(200,), **kwargs):
    response = requests.request(method, base + path, timeout=30, **kwargs)
    if response.status_code not in expected:
        raise RuntimeError(f"{method} {path} failed: {response.status_code} {response.text}")
    if not response.text:
        return None
    try:
        return response.json()
    except Exception:
        return response.text


token = db_token() or login_token()
if not token:
    raise RuntimeError(f"Could not obtain ElementX token for {username}")
headers = {"Authorization": "Bearer " + token}
user_id = f"@{username}:{server_name}"


def delete_alias(alias: str) -> None:
    encoded_alias = quote(alias, safe="")
    try:
        request(
            "DELETE",
            "/_matrix/client/v3/directory/room/" + encoded_alias,
            headers=headers,
            expected=(200, 403, 404),
        )
    except Exception:
        pass


def cleanup_stale_aliases() -> None:
    alias_filter = (
        "room_alias like '#asset-check-elementx-%:%' "
        "or room_alias like '#asset-time-%:%' "
        "or room_alias like '#asset-%:%' "
        "or room_alias like '#gma-%:%'"
    )
    try:
        for alias in run_sql("select room_alias from room_aliases where " + alias_filter + ";"):
            delete_alias(alias)
    except Exception:
        pass
    try:
        run_sql("delete from room_aliases where " + alias_filter + ";")
    except Exception:
        pass


cleanup_stale_aliases()


def clear_user_room_metadata() -> None:
    encoded_user_id = quote(user_id, safe="")
    try:
        request(
            "PUT",
            "/_matrix/client/v3/user/" + encoded_user_id + "/account_data/m.direct",
            headers=headers,
            json={},
            expected=(200,),
        )
    except Exception:
        pass
    for table in ("room_account_data", "room_tags", "room_tags_revisions"):
        try:
            run_sql(
                "delete from " + table + " where user_id = '"
                + sql_literal(user_id)
                + "';"
            )
        except Exception:
            pass


clear_user_room_metadata()


def room_action(room_id: str, action: str, expected=(200, 403, 404)) -> None:
    encoded_room_id = quote(room_id, safe="")
    request(
        "POST",
        "/_matrix/client/v3/rooms/" + encoded_room_id + "/" + action,
        headers=headers,
        json={},
        expected=expected,
    )


joined_payload = request(
    "GET",
    "/_matrix/client/v3/joined_rooms",
    headers=headers,
    expected=(200,),
) or {}
joined_rooms = list(joined_payload.get("joined_rooms", []))
for room_id in joined_rooms:
    room_action(room_id, "leave")
    room_action(room_id, "forget", expected=(200, 400, 403, 404))

sync_payload = request(
    "GET",
    "/_matrix/client/v3/sync",
    headers=headers,
    params={"timeout": "0"},
    expected=(200,),
) or {}
invited_rooms = list((sync_payload.get("rooms", {}).get("invite", {}) or {}).keys())
for room_id in invited_rooms:
    room_action(room_id, "leave")
    room_action(room_id, "forget", expected=(200, 400, 403, 404))

left_rooms = []
try:
    left_rooms = run_sql(
        "select distinct cse.room_id "
        "from current_state_events cse "
        "join room_memberships rm on rm.event_id = cse.event_id "
        "where cse.type = 'm.room.member' "
        "and cse.state_key = '" + sql_literal(user_id) + "' "
        "and rm.membership = 'leave';"
    )
except Exception:
    left_rooms = []
for room_id in left_rooms:
    room_action(room_id, "forget", expected=(200, 400, 403, 404))

print(json.dumps({
    "joined_rooms_left": len(joined_rooms),
    "invites_left": len(invited_rooms),
    "left_rooms_forgotten": len(left_rooms),
}))
PY
adb -s emulator-5554 shell am force-stop io.element.android.x >/dev/null 2>&1 || true
"""
    script = (
        script.replace("__BASE__", repr(ELEMENTX_BASE_URL))
        .replace("__PROJECT_DIR__", repr(ELEMENTX_PROJECT_DIR))
        .replace("__COMPOSE_PROJECT__", repr(ELEMENTX_COMPOSE_PROJECT))
        .replace("__USERNAME__", repr(username))
        .replace("__PASSWORD__", repr(password))
        .replace("__SERVER_NAME__", repr(server_name))
    )
    run_bash(client, script, timeout=120)


def prune_elementx_unverified_devices(client: AndroidController) -> None:
    """Remove stale/synthetic Matrix devices that trigger ElementX send warnings.

    ElementX warns before sending encrypted messages when it sees unverified
    devices. Benchmark users other than testuser are backend-only fixtures, so
    they do not need persistent devices. For testuser, keep only the latest
    access-token device, which is the currently logged-in mobile session.
    """
    server_name = elementx_server_name()
    testuser_id = elementx_user_id(ELEMENTX_DEFAULT_USERNAME)
    _TOKEN_CACHE.clear()
    run_bash(
        client,
        f"""
set -euo pipefail
{_elementx_compose('exec -T db psql -U synapse -d synapse')} <<'SQL'
BEGIN;
CREATE TEMP TABLE gma_keep_device AS
  SELECT device_id
  FROM access_tokens
  WHERE user_id = '{testuser_id}' AND device_id IS NOT NULL
  ORDER BY id DESC
  LIMIT 1;

DELETE FROM access_tokens
WHERE user_id LIKE '%:{server_name}'
  AND (
    user_id <> '{testuser_id}'
    OR device_id IS NULL
    OR device_id NOT IN (SELECT device_id FROM gma_keep_device)
  );
DELETE FROM e2e_device_keys_json
WHERE user_id LIKE '%:{server_name}'
  AND (
    user_id <> '{testuser_id}'
    OR device_id NOT IN (SELECT device_id FROM gma_keep_device)
  );
DELETE FROM e2e_one_time_keys_json
WHERE user_id LIKE '%:{server_name}'
  AND (
    user_id <> '{testuser_id}'
    OR device_id NOT IN (SELECT device_id FROM gma_keep_device)
  );
DELETE FROM e2e_fallback_keys_json
WHERE user_id LIKE '%:{server_name}'
  AND (
    user_id <> '{testuser_id}'
    OR device_id NOT IN (SELECT device_id FROM gma_keep_device)
  );
DELETE FROM device_inbox
WHERE user_id LIKE '%:{server_name}'
  AND (
    user_id <> '{testuser_id}'
    OR device_id NOT IN (SELECT device_id FROM gma_keep_device)
  );
DELETE FROM event_txn_id_device_id
WHERE user_id LIKE '%:{server_name}'
  AND (
    user_id <> '{testuser_id}'
    OR device_id NOT IN (SELECT device_id FROM gma_keep_device)
  );
DELETE FROM device_lists_stream
WHERE user_id LIKE '%:{server_name}'
  AND (
    user_id <> '{testuser_id}'
    OR device_id NOT IN (SELECT device_id FROM gma_keep_device)
  );
DELETE FROM devices
WHERE user_id LIKE '%:{server_name}'
  AND (
    user_id <> '{testuser_id}'
    OR device_id NOT IN (SELECT device_id FROM gma_keep_device)
  );
DROP TABLE gma_keep_device;
COMMIT;
SQL
""",
        timeout=120,
    )


def resolve_elementx_room_id(reference: str) -> str:
    if reference.startswith("!"):
        return reference

    token = _TOKEN_CACHE.get((ELEMENTX_DEFAULT_USERNAME, ELEMENTX_DEFAULT_PASSWORD)) or _fetch_existing_access_token(ELEMENTX_DEFAULT_USERNAME)
    if token and not _token_is_valid(token):
        token = None
    if not token:
        token = _login(ELEMENTX_DEFAULT_USERNAME, ELEMENTX_DEFAULT_PASSWORD)
        if token:
            _TOKEN_CACHE[(ELEMENTX_DEFAULT_USERNAME, ELEMENTX_DEFAULT_PASSWORD)] = token

    if reference.startswith("@"):
        if not token:
            raise RuntimeError(f"Could not resolve ElementX DM room {reference!r}")
        room_id = _resolve_elementx_direct_room_id(
            access_token=token,
            user_id=elementx_user_id(ELEMENTX_DEFAULT_USERNAME),
            other_user_id=reference,
        )
        if room_id:
            return room_id
        raise RuntimeError(f"Could not resolve ElementX DM room {reference!r}")

    if reference.startswith("#"):
        aliases = [reference]
    else:
        # Some tasks pass an explicit alias localpart, while others pass a room
        # display name. Try the explicit alias first, then the generated alias.
        aliases = [elementx_room_alias(reference)]
        generated_alias = elementx_room_alias(slugify_room_alias(reference))
        if generated_alias not in aliases:
            aliases.append(generated_alias)

    last_error: Exception | None = None
    for alias in aliases:
        encoded_alias = requests.utils.quote(alias, safe="")
        try:
            payload = _matrix_request(
                "GET",
                f"/_matrix/client/v3/directory/room/{encoded_alias}",
                expected=(200,),
            )
            return payload["room_id"]
        except Exception as exc:
            last_error = exc

    if not token:
        if last_error:
            raise last_error
        raise RuntimeError(f"Could not resolve ElementX room {reference!r}")
    joined = _matrix_request(
        "GET",
        "/_matrix/client/v3/joined_rooms",
        access_token=token,
        expected=(200,),
    )
    for room_id in joined.get("joined_rooms", []):
        try:
            state = _matrix_request(
                "GET",
                f"/_matrix/client/v3/rooms/{requests.utils.quote(room_id, safe='')}/state/m.room.name",
                access_token=token,
                expected=(200,),
            )
        except Exception:
            continue
        if state.get("name") == reference:
            return room_id
    if last_error:
        raise last_error
    raise RuntimeError(f"Could not resolve ElementX room {reference!r}")


def ensure_elementx_room(
    client: AndroidController,
    *,
    name: str,
    room_type: str,
    creator_username: str,
    creator_password: str,
    members: list[str],
    member_passwords: dict[str, str] | None = None,
    alias_localpart: str | None = None,
    topic: str | None = None,
    encrypted: bool = False,
    parent_space: str | None = None,
) -> str:
    ensure_elementx_backend(client)
    member_passwords = member_passwords or {}
    creator_token = ensure_elementx_user(
        client,
        creator_username,
        password=creator_password,
    )

    if room_type == "dm":
        if len(members) != 1:
            raise ValueError("ElementX DM rooms must include exactly one invited member")
        member_username = members[0]
        member_password = member_passwords.get(
            member_username,
            _default_password_for_username(member_username),
        )
        member_token = ensure_elementx_user(client, member_username, password=member_password)
        creator_user_id = elementx_user_id(creator_username)
        member_user_id = elementx_user_id(member_username)
        room_id = _resolve_elementx_direct_room_id(
            access_token=creator_token,
            user_id=creator_user_id,
            other_user_id=member_user_id,
        )
        if room_id is None:
            payload: dict = {
                "preset": "trusted_private_chat",
                "is_direct": True,
                "invite": [member_user_id],
            }
            if encrypted:
                payload["initial_state"] = [
                    {
                        "type": "m.room.encryption",
                        "state_key": "",
                        "content": {"algorithm": "m.megolm.v1.aes-sha2"},
                    }
                ]
            created = _matrix_request(
                "POST",
                "/_matrix/client/v3/createRoom",
                access_token=creator_token,
                json_payload=payload,
                expected=(200,),
            )
            room_id = created["room_id"]
        creator_joined = _join_elementx_room(room_id, creator_token)
        member_joined = _join_elementx_room(room_id, member_token)
        if not creator_joined and member_joined:
            _invite_elementx_user(room_id, member_token, creator_username)
            creator_joined = _join_elementx_room(room_id, creator_token)
        if not creator_joined:
            raise RuntimeError(
                f"Could not join ElementX DM {room_id} as creator {creator_username}"
            )
        _mark_elementx_direct_room(
            access_token=creator_token,
            user_id=creator_user_id,
            other_user_id=member_user_id,
            room_id=room_id,
        )
        _mark_elementx_direct_room(
            access_token=member_token,
            user_id=member_user_id,
            other_user_id=creator_user_id,
            room_id=room_id,
        )
        return room_id

    alias_localpart = alias_localpart or slugify_room_alias(name)
    alias = elementx_room_alias(alias_localpart)
    try:
        room_id = resolve_elementx_room_id(alias)
    except Exception:
        payload: dict = {
            "name": name,
            "room_alias_name": alias_localpart,
            "topic": topic or "",
        }
        if room_type == "space":
            payload["creation_content"] = {"type": "m.space"}
            payload["preset"] = "private_chat"
        else:
            payload["preset"] = "private_chat"
            payload["invite"] = [elementx_user_id(member) for member in members]
        if encrypted and room_type != "space":
            payload["initial_state"] = [
                {
                    "type": "m.room.encryption",
                    "state_key": "",
                    "content": {"algorithm": "m.megolm.v1.aes-sha2"},
                }
            ]
        created = _matrix_request(
            "POST",
            "/_matrix/client/v3/createRoom",
            access_token=creator_token,
            json_payload=payload,
            expected=(200,),
        )
        room_id = created["room_id"]

    creator_joined = _join_elementx_room(room_id, creator_token)
    member_tokens: dict[str, str] = {}
    for member in members:
        password = member_passwords.get(member, _default_password_for_username(member))
        member_token = ensure_elementx_user(client, member, password=password)
        member_tokens[member] = member_token
        _join_elementx_room(room_id, member_token)

    if not creator_joined:
        for member_token in member_tokens.values():
            _invite_elementx_user(room_id, member_token, creator_username)
            if _join_elementx_room(room_id, creator_token):
                creator_joined = True
                break
    if not creator_joined:
        raise RuntimeError(
            f"Could not join ElementX room {room_id} as creator {creator_username}"
        )

    if topic:
        _matrix_request(
            "PUT",
            f"/_matrix/client/v3/rooms/{requests.utils.quote(room_id, safe='')}/state/m.room.topic",
            access_token=creator_token,
            json_payload={"topic": topic},
            expected=(200,),
        )

    if parent_space:
        parent_id = resolve_elementx_room_id(parent_space)
        encoded_parent = requests.utils.quote(parent_id, safe="")
        encoded_child = requests.utils.quote(room_id, safe="")
        state_content = {"via": [elementx_server_name()]}
        _matrix_request(
            "PUT",
            f"/_matrix/client/v3/rooms/{encoded_parent}/state/m.space.child/{encoded_child}",
            access_token=creator_token,
            json_payload=state_content,
            expected=(200,),
        )
        _matrix_request(
            "PUT",
            f"/_matrix/client/v3/rooms/{encoded_child}/state/m.space.parent/{encoded_parent}",
            access_token=creator_token,
            json_payload={"via": [elementx_server_name()], "canonical": True},
            expected=(200,),
        )
    return room_id


def send_elementx_message(
    client: AndroidController,
    *,
    room: str,
    sender_username: str,
    sender_password: str,
    text: str,
    reply_to_event_id: str | None = None,
    mentions_room: bool | None = None,
) -> str:
    ensure_elementx_backend(client)
    token = ensure_elementx_user(client, sender_username, password=sender_password)
    room_id = resolve_elementx_room_id(room)
    payload: dict = {"msgtype": "m.text", "body": text}
    if mentions_room:
        payload["m.mentions"] = {"room": True}
    if reply_to_event_id:
        payload["m.relates_to"] = {
            "m.in_reply_to": {"event_id": reply_to_event_id},
        }
    response = _matrix_request(
        "PUT",
        f"/_matrix/client/v3/rooms/{requests.utils.quote(room_id, safe='')}/send/m.room.message/{uuid.uuid4().hex}",
        access_token=token,
        json_payload=payload,
        expected=(200,),
    )
    return response["event_id"]


def send_elementx_file(
    client: AndroidController,
    *,
    room: str,
    sender_username: str,
    sender_password: str,
    filename: str,
    mime_type: str | None,
    content_b64: str,
) -> str:
    ensure_elementx_backend(client)
    token = ensure_elementx_user(client, sender_username, password=sender_password)
    room_id = resolve_elementx_room_id(room)
    content = base64.b64decode(content_b64)
    try:
        upload = _matrix_request(
            "POST",
            "/_matrix/media/v3/upload",
            access_token=token,
            params={"filename": filename},
            data=content,
            headers={"Content-Type": mime_type or "application/octet-stream"},
            expected=(200,),
        )
    except RuntimeError:
        upload = _matrix_request(
            "POST",
            "/_matrix/media/r0/upload",
            access_token=token,
            params={"filename": filename},
            data=content,
            headers={"Content-Type": mime_type or "application/octet-stream"},
            expected=(200,),
        )
    content_uri = upload.get("content_uri") if isinstance(upload, dict) else None
    if not content_uri:
        raise RuntimeError(f"ElementX media upload produced no content_uri: {upload}")
    payload = {
        "msgtype": "m.file",
        "body": filename,
        "filename": filename,
        "url": content_uri,
        "info": {
            "mimetype": mime_type or "application/octet-stream",
            "size": len(content),
        },
    }
    response = _matrix_request(
        "PUT",
        f"/_matrix/client/v3/rooms/{requests.utils.quote(room_id, safe='')}/send/m.room.message/{uuid.uuid4().hex}",
        access_token=token,
        json_payload=payload,
        expected=(200,),
    )
    return response["event_id"]


def set_elementx_event_timestamp(
    client: AndroidController,
    *,
    event_id: str,
    created_at_ms: int | None,
) -> None:
    if created_at_ms is None:
        return
    raise RuntimeError(
        "ElementX event timestamps must be applied before event creation with "
        "elementx_clock_override; rewriting Matrix event JSON corrupts event IDs."
    )


def set_elementx_room_timestamp(
    client: AndroidController,
    *,
    room: str,
    created_at_ms: int | None,
) -> None:
    if created_at_ms is None:
        return
    raise RuntimeError(
        "ElementX room timestamps must be applied before room creation with "
        "elementx_clock_override; rewriting Matrix event JSON corrupts event IDs."
    )


def find_elementx_message_event_id(
    client: AndroidController,
    *,
    room: str,
    text: str,
    sender_username: str | None = None,
) -> str | None:
    ensure_elementx_backend(client)
    room_id = resolve_elementx_room_id(room)

    def sql_literal(value: str) -> str:
        return value.replace("'", "''")

    sender_clause = ""
    if sender_username:
        sender_clause = (
            " and ej.json::json->>'sender' = '"
            + sql_literal(elementx_user_id(sender_username))
            + "'"
        )
    query = (
        "select e.event_id from events e join event_json ej on e.event_id = ej.event_id "
        + "where e.room_id = '" + sql_literal(room_id) + "' "
        + "and e.type = 'm.room.message' "
        + sender_clause
        + " and ej.json::json->'content'->>'body' = '" + sql_literal(text) + "' "
        + "order by e.stream_ordering desc limit 1;"
    )
    cmd = (
        f"cd {ELEMENTX_PROJECT_DIR} && "
        f"docker compose --project-name {ELEMENTX_COMPOSE_PROJECT} -f docker-compose.yml "
        "exec -T db psql -U synapse -d synapse -At -c "
        + shlex.quote(query)
    )
    event_id = subprocess.check_output(["sh", "-lc", cmd], text=True).strip()
    return event_id or None


def pin_elementx_event(
    client: AndroidController,
    *,
    room: str,
    event_id: str,
    pinning_username: str = "testuser",
    pinning_password: str = "testpass123",
) -> None:
    ensure_elementx_backend(client)
    token = ensure_elementx_user(client, pinning_username, password=pinning_password)
    room_id = resolve_elementx_room_id(room)
    encoded_room = requests.utils.quote(room_id, safe="")
    headers = {"Authorization": f"Bearer {token}"}
    state_url = f"{ELEMENTX_BASE_URL}/_matrix/client/v3/rooms/{encoded_room}/state/m.room.pinned_events"
    response = requests.get(state_url, headers=headers, timeout=30)
    if response.status_code == 200:
        pinned = list(response.json().get("pinned", []))
    elif response.status_code == 404:
        pinned = []
    else:
        raise RuntimeError(
            f"ElementX API GET pinned events failed: {response.status_code} {response.text}"
        )
    if event_id in pinned:
        return
    pinned.append(event_id)
    _matrix_request(
        "PUT",
        f"/_matrix/client/v3/rooms/{encoded_room}/state/m.room.pinned_events",
        access_token=token,
        json_payload={"pinned": pinned},
        expected=(200,),
    )


def pin_elementx_message(
    client: AndroidController,
    *,
    room: str,
    text: str,
    sender_username: str | None = None,
    pinning_username: str = "testuser",
    pinning_password: str = "testpass123",
) -> None:
    event_id = find_elementx_message_event_id(
        client,
        room=room,
        text=text,
        sender_username=sender_username,
    )
    if event_id is None:
        raise RuntimeError(f"Could not find ElementX message to pin in {room!r}: {text!r}")
    pin_elementx_event(
        client,
        room=room,
        event_id=event_id,
        pinning_username=pinning_username,
        pinning_password=pinning_password,
    )


def _join_elementx_room(room_id: str, token: str) -> bool:
    response = requests.post(
        f"{ELEMENTX_BASE_URL}/_matrix/client/v3/rooms/{requests.utils.quote(room_id, safe='')}/join",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if response.status_code == 200:
        return True
    if response.status_code == 403:
        return False
    raise RuntimeError(
        f"ElementX room join failed: {response.status_code} {response.text}"
    )


def _invite_elementx_user(room_id: str, token: str, username: str) -> None:
    response = requests.post(
        f"{ELEMENTX_BASE_URL}/_matrix/client/v3/rooms/{requests.utils.quote(room_id, safe='')}/invite",
        headers={"Authorization": f"Bearer {token}"},
        json={"user_id": elementx_user_id(username)},
        timeout=30,
    )
    if response.status_code in {200, 403}:
        return
    raise RuntimeError(
        f"ElementX room invite failed: {response.status_code} {response.text}"
    )


def send_elementx_poll(
    client: AndroidController,
    *,
    room: str,
    sender_username: str,
    sender_password: str,
    question: str,
    options: list[str],
    responses: list[dict],
    created_at_ms: int | None = None,
) -> str:
    ensure_elementx_backend(client)
    token = ensure_elementx_user(client, sender_username, password=sender_password)
    room_id = resolve_elementx_room_id(room)
    option_map = {
        option: str(uuid.uuid4())
        for option in options
    }
    poll_text = "\n".join([question] + [f"{index + 1}. {option}" for index, option in enumerate(options)])
    poll_payload = {
        "org.matrix.msc3381.poll.start": {
            "question": {"org.matrix.msc1767.text": question},
            "kind": "org.matrix.msc3381.poll.disclosed",
            "max_selections": 1,
            "answers": [
                {"id": option_map[option], "org.matrix.msc1767.text": option}
                for option in options
            ],
        },
        "org.matrix.msc1767.text": poll_text,
    }
    with elementx_clock_override(client, created_at_ms):
        response = _matrix_request(
            "PUT",
            f"/_matrix/client/v3/rooms/{requests.utils.quote(room_id, safe='')}/send/org.matrix.msc3381.poll.start/{uuid.uuid4().hex}",
            access_token=token,
            json_payload=poll_payload,
            expected=(200,),
        )
    poll_event_id = response["event_id"]
    for item in responses:
        responder_username = item["username"]
        responder_password = item.get("password", _default_password_for_username(responder_username))
        responder_token = ensure_elementx_user(
            client,
            responder_username,
            password=responder_password,
        )
        reply_payload = {
            "org.matrix.msc3381.poll.response": {"answers": [option_map[item["option"]]]},
            "m.relates_to": {"rel_type": "m.reference", "event_id": poll_event_id},
        }
        with elementx_clock_override(client, item.get("created_at_ms")):
            _matrix_request(
                "PUT",
                f"/_matrix/client/v3/rooms/{requests.utils.quote(room_id, safe='')}/send/org.matrix.msc3381.poll.response/{uuid.uuid4().hex}",
                access_token=responder_token,
                json_payload=reply_payload,
                expected=(200,),
            )
    return poll_event_id


def ensure_elementx_apk(client: AndroidController) -> None:
    run_bash(
        client,
        """
set -euo pipefail
DEVICE=emulator-5554
if adb -s "$DEVICE" shell pm path io.element.android.x >/dev/null 2>&1; then
  exit 0
fi
apk=/app/dev/elementx.apk
if [ ! -f "$apk" ]; then
  apk=/app/mobileworld/elementx.apk
fi
if [ ! -f "$apk" ]; then
  echo "ElementX APK not found" >&2
  exit 1
fi
adb -s "$DEVICE" install -r -g "$apk" >/dev/null
""",
        timeout=120,
    )




def elementx_backend_is_healthy(client: AndroidController) -> bool:
    try:
        run_bash(
            client,
            f"curl -fsS --max-time 5 {ELEMENTX_HEALTH_URL} >/dev/null",
            timeout=10,
        )
        return True
    except Exception:
        return False






def elementx_local_session_exists(client: AndroidController) -> bool:
    """Return whether ElementX has a persisted Android Matrix session."""
    try:
        output = run_bash(
            client,
            r"""
set -euo pipefail
DEVICE=emulator-5554
adb -s "$DEVICE" root >/dev/null 2>&1 || true
if adb -s "$DEVICE" shell 'test -n "$(find /data/user/0/io.element.android.x/files/sessions -name matrix-sdk-state.sqlite3 2>/dev/null | head -1)"'; then
  echo session_present
else
  echo session_missing
fi
""",
            timeout=20,
        )
        return "session_present" in output
    except Exception:
        return False



def elementx_app_is_signed_out(client: AndroidController) -> bool:
    """Bounded UI check for an invalid local ElementX session."""
    try:
        output = run_bash(
            client,
            r"""
set +e
DEVICE=emulator-5554
adb -s "$DEVICE" shell am force-stop io.element.android.x >/dev/null 2>&1 || true
adb -s "$DEVICE" shell monkey -p io.element.android.x -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1 || true
sleep 6
timeout 8s adb -s "$DEVICE" shell uiautomator dump /sdcard/elementx_signed_out_check.xml >/dev/null 2>&1 || true
ui="$(timeout 5s adb -s "$DEVICE" shell cat /sdcard/elementx_signed_out_check.xml 2>/dev/null || true)"
if printf '%s' "$ui" | grep -Eq 'You.re signed out|Sign in again|Sign in manually|Username'; then
  echo signed_out
elif printf '%s' "$ui" | grep -Eq 'No chats yet|Start chat|Your chats|Back up your chats|Chats|People|Rooms|Home'; then
  echo signed_in
else
  echo unknown
fi
adb -s "$DEVICE" shell input keyevent 3 >/dev/null 2>&1 || true
""",
            timeout=25,
        )
        return "signed_out" in output
    except Exception:
        return False

def elementx_app_is_signed_in(client: AndroidController) -> bool:
    try:
        output = run_bash(
            client,
            r"""
set -euo pipefail
DEVICE=emulator-5554

dump_ui() {
  adb -s "$DEVICE" shell rm -f /sdcard/elementx_repair_check.xml >/dev/null 2>&1 || true
  timeout 8 adb -s "$DEVICE" shell uiautomator dump /sdcard/elementx_repair_check.xml >/dev/null 2>&1 || true
  timeout 5 adb -s "$DEVICE" shell cat /sdcard/elementx_repair_check.xml 2>/dev/null || true
}

adb -s "$DEVICE" shell am force-stop io.element.android.x >/dev/null 2>&1 || true
adb -s "$DEVICE" shell monkey -p io.element.android.x -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1 || true
for _ in $(seq 1 35); do
  sleep 1
  ui="$(dump_ui)"
  if printf '%s' "$ui" | grep -Fq 'Report bug'; then
    adb -s "$DEVICE" shell input tap 615 1450 >/dev/null 2>&1 || true
    sleep 1
    ui="$(dump_ui)"
  fi
  if printf '%s' "$ui" | grep -Eq 'Your chats|Back up your chats|No chats yet|Start chat|Chats|People|Rooms|Home'; then
    adb -s "$DEVICE" shell input keyevent 3 >/dev/null 2>&1 || true
    echo signed_in
    exit 0
  fi
  if printf '%s' "$ui" | grep -Eq 'Be in your element|Sign in manually|Create account|You.re signed out|Username'; then
    echo signed_out
    exit 0
  fi
done
echo unknown
""",
            timeout=40,
        )
        return "signed_in" in output
    except Exception:
        return False

def repair_elementx_app_state(client: AndroidController) -> None:
    """Repair ElementX from a loaded snapshot.

    ElementX persists room summaries in encrypted Android-local state. Backend
    leave/forget cleanup alone can leave stale rooms visible in the chat list,
    so reset the app data and relogin after cleaning the homeserver state.
    """
    ensure_elementx_apk(client)
    ensure_elementx_backend(client)
    clear_elementx_user_state(client)
    sync_elementx_app_state(client)

def sync_elementx_app_state(
    client: AndroidController,
    *,
    username: str = ELEMENTX_DEFAULT_USERNAME,
    password: str | None = None,
) -> None:
    ensure_elementx_apk(client)
    ensure_elementx_backend(client)
    password = password or _default_password_for_username(username)
    display_name = ELEMENTX_DEFAULT_DISPLAY_NAME if username == ELEMENTX_DEFAULT_USERNAME else None
    _set_elementx_display_name_via_client(client, username, password, display_name)
    run_bash(
        client,
        f"""
set -euo pipefail

DEVICE=emulator-5554
SERVER_URL={ELEMENTX_SERVER_URL!r}
USERNAME={username!r}
PASSWORD={password!r}
LOCAL_HOST="${{SERVER_URL#http://}}"
LOCAL_HOST="${{LOCAL_HOST#https://}}"

dump_ui() {{
  adb -s "$DEVICE" shell rm -f /sdcard/elementx_reset.xml >/dev/null 2>&1 || true
  timeout 8 adb -s "$DEVICE" shell uiautomator dump /sdcard/elementx_reset.xml >/dev/null 2>&1 || true
  timeout 5 adb -s "$DEVICE" shell cat /sdcard/elementx_reset.xml 2>/dev/null || true
}}

escape_for_adb_text() {{
  printf '%s' "$1" | sed \
    -e 's/%/%25/g' \
    -e 's/ /%s/g' \
    -e 's/"/\\"/g' \
    -e 's/&/\\&/g' \
    -e 's/(/\\(/g' \
    -e 's/)/\\)/g' \
    -e 's/</\\</g' \
    -e 's/>/\\>/g' \
    -e 's/?/\\?/g' \
    -e "s/'/\\\\'/g" \
    -e 's/:/\\:/g' \
    -e 's/;/\\;/g' \
    -e 's/\\//\\\\\\//g'
}}

input_text() {{
  local escaped
  escaped="$(escape_for_adb_text "$1")"
  adb -s "$DEVICE" shell input text "$escaped"
}}

tap() {{
  adb -s "$DEVICE" shell input tap "$1" "$2"
}}

wait_for_text() {{
  local needle="$1"
  local timeout="${{2:-25}}"
  local elapsed=0
  while [ "$elapsed" -lt "$timeout" ]; do
    local xml
    xml="$(dump_ui || true)"
    if printf '%s' "$xml" | grep -Fq 'Report bug'; then
      tap 615 1450
      sleep 2
      elapsed=$((elapsed + 2))
      continue
    fi
    if printf '%s' "$xml" | grep -Fq "$needle"; then
      return 0
    fi
    sleep 1
    elapsed=$((elapsed + 1))
  done
  return 1
}}

wait_for_any_text() {{
  local timeout="$1"
  shift
  local elapsed=0
  while [ "$elapsed" -lt "$timeout" ]; do
    local xml
    xml="$(dump_ui || true)"
    if printf '%s' "$xml" | grep -Fq 'Report bug'; then
      tap 615 1450
      sleep 2
      elapsed=$((elapsed + 2))
      continue
    fi
    for needle in "$@"; do
      if printf '%s' "$xml" | grep -Fq "$needle"; then
        echo "$needle"
        return 0
      fi
    done
    sleep 1
    elapsed=$((elapsed + 1))
  done
  return 1
}}

get_element_center() {{
  local xml="$1"
  local text_match="$2"
  local node bounds x1 y1 x2 y2
  node="$(echo "$xml" | grep -o "<node [^>]*text=\\"${{text_match}}\\"[^>]*>" | head -1)"
  [ -z "$node" ] && return 1
  bounds="$(echo "$node" | grep -o 'bounds="\\[[0-9]*,[0-9]*\\]\\[[0-9]*,[0-9]*\\]"')"
  [ -z "$bounds" ] && return 1
  x1="$(echo "$bounds" | sed 's/bounds="\\[\\([0-9]*\\),.*/\\1/')"
  y1="$(echo "$bounds" | sed 's/bounds="\\[[0-9]*,\\([0-9]*\\)\\].*/\\1/')"
  x2="$(echo "$bounds" | sed 's/.*\\]\\[\\([0-9]*\\),.*/\\1/')"
  y2="$(echo "$bounds" | sed 's/.*\\]\\[[0-9]*,\\([0-9]*\\)\\].*/\\1/')"
  echo "$(( (x1 + x2) / 2 )) $(( (y1 + y2) / 2 ))"
}}

tap_element() {{
  local xml="$1"
  local label="$2"
  local fallback_x="${{3:-540}}"
  local fallback_y="${{4:-1900}}"
  local coords
  coords="$(get_element_center "$xml" "$label" 2>/dev/null)" || coords=""
  if [ -n "$coords" ]; then
    tap "${{coords% *}}" "${{coords#* }}"
  else
    tap "$fallback_x" "$fallback_y"
  fi
}}

dismiss_error_if_present() {{
  # Element X raises the Firebase pusher dialog a few seconds after reaching a
  # signed-in screen. Wait for it and persist the "do not show again" choice.
  local ui
  for _ in $(seq 1 8); do
    sleep 2
    ui="$(dump_ui || true)"
    if printf "%s" "$ui" | grep -Fq "Unable to register pusher"; then
      if printf "%s" "$ui" | grep -Fq "Do not show this again"; then
        tap 245 1400
        sleep 1
        ui="$(dump_ui || true)"
      fi
      tap_element "$ui" "OK" 816 2210
      sleep 2
      return 0
    fi
  done
}}

set_push_ignore_registration_error() {{
  adb -s "$DEVICE" root >/dev/null 2>&1 || true
  python3 - <<'PY2'
from pathlib import Path
Path('/tmp/elementx_push_store.preferences_pb').write_bytes(bytes.fromhex(
    '0a1e0a107075736850726f76696465724e616d65120a2a084669726562617365'
    '0a1d0a1769676e6f7265526567697374726174696f6e4572726f7212020801'
))
PY2
  local owner
  owner="$(adb -s "$DEVICE" shell stat -c '%u:%g' /data/user/0/io.element.android.x/files/datastore 2>/dev/null | tr -d '\r' || true)"
  adb -s "$DEVICE" shell find /data/user/0/io.element.android.x/files/datastore -name 'push_store_*.preferences_pb' 2>/dev/null | tr -d '\r' | while read -r path; do
    [ -z "$path" ] && continue
    adb -s "$DEVICE" push /tmp/elementx_push_store.preferences_pb "$path" >/dev/null 2>&1 || true
    if [ -n "$owner" ]; then
      adb -s "$DEVICE" shell chown "$owner" "$path" >/dev/null 2>&1 || true
    fi
    adb -s "$DEVICE" shell chmod 600 "$path" >/dev/null 2>&1 || true
  done
}}

provider_flow_done() {{
  case "$STATE" in
    'Username'|'Confirm your digital identity'|'Help improve Element X'|'Error'|'Allow notifications and never miss a message'|'Your chats'|'Back up your chats'|'Chats'|'People'|'Rooms'|'Home')
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}}

login_flow_done() {{
  case "$STATE" in
    'Confirm your digital identity'|'Help improve Element X'|'Error'|'Allow notifications and never miss a message'|'Your chats'|'Back up your chats'|'Chats'|'People'|'Rooms'|'Home')
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}}

adb -s "$DEVICE" shell am force-stop io.element.android.x >/dev/null 2>&1 || true
adb -s "$DEVICE" shell pm clear io.element.android.x >/dev/null 2>&1 || true
adb -s "$DEVICE" shell monkey -p io.element.android.x -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1 || true
sleep 3

STATE="$(wait_for_any_text 30 \
  'You’re signed out' \
  'Sign in manually' \
  'Change account provider' \
  'Find an account provider' \
  'You’re about to sign in to 10.0.2.2:8021' \
  'Username' \
  'Confirm your digital identity' \
  'Help improve Element X' \
  'Error' \
  'Allow notifications and never miss a message' \
  'Your chats' \
  'Back up your chats' \
  'Chats' \
  'People' \
  'Rooms' \
  'Home' || true)"

case "$STATE" in
  'Your chats'|'Back up your chats'|'Chats'|'People'|'Rooms'|'Home')
    set_push_ignore_registration_error
    dismiss_error_if_present
    adb -s "$DEVICE" shell input keyevent 3
    exit 0
    ;;
  'You’re signed out')
    tap 540 2210
    sleep 3
    ;;
esac

STATE="$(wait_for_any_text 30 \
  'Sign in manually' \
  'Change account provider' \
  'Find an account provider' \
  'You’re about to sign in to 10.0.2.2:8021' \
  'Username' \
  'Confirm your digital identity' \
  'Help improve Element X' \
  'Error' \
  'Allow notifications and never miss a message' \
  'Your chats' \
  'Back up your chats' \
  'Chats' \
  'People' \
  'Rooms' \
  'Home' || true)"

if [ "$STATE" = 'Sign in manually' ]; then
  tap 540 1880
  sleep 2
  STATE="$(wait_for_any_text 20 \
    'Change account provider' \
    'Find an account provider' \
    'Username' \
    'You’re about to sign in to 10.0.2.2:8021' \
    'Confirm your digital identity' \
    'Help improve Element X' \
    'Error' \
    'Allow notifications and never miss a message' \
    'Your chats' \
    'Back up your chats' \
    'Chats' \
    'People' \
    'Rooms' \
    'Home' || true)"
fi

if ! provider_flow_done; then
  # Element X exposes provider selection through a few Compose screens. Drive it
  # from the current UI each iteration instead of trusting a cached state; the
  # emulator can take several seconds to settle between these screens.
  provider_ready=0
  for _ in $(seq 1 14); do
    ui="$(dump_ui || true)"
    if printf '%s' "$ui" | grep -Eq 'Username|Confirm your digital identity|Help improve Element X|Error|Allow notifications and never miss a message|Your chats|Back up your chats|Chats|People|Rooms|Home'; then
      provider_ready=1
      break
    fi
    if printf '%s' "$ui" | grep -Fq "You’re about to sign in to $LOCAL_HOST"; then
      tap 540 2050
      sleep 4
      continue
    fi
    if printf '%s' "$ui" | grep -Fq 'Find an account provider'; then
      tap 540 880
      sleep 1
      input_text "$SERVER_URL"
      adb -s "$DEVICE" shell input keyevent 66
      sleep 2
      if wait_for_text "$LOCAL_HOST" 25; then
        tap 540 1115
        sleep 4
      fi
      continue
    fi
    if printf '%s' "$ui" | grep -Fq 'Other'; then
      tap_element "$ui" "Other" 540 1275
    elif printf '%s' "$ui" | grep -Fq 'You’re about to sign in to matrix.org'; then
      tap 540 2220
    elif printf '%s' "$ui" | grep -Fq 'Change account provider'; then
      tap 540 1275
    elif printf '%s' "$ui" | grep -Fq 'Sign in manually'; then
      tap 540 1880
    elif printf '%s' "$ui" | grep -Fq 'You’re signed out'; then
      tap 540 2210
    else
      tap 540 1275
    fi
    sleep 3
  done

  STATE="$(wait_for_any_text 20 \
    'Username' \
    'Confirm your digital identity' \
    'Help improve Element X' \
    'Error' \
    'Allow notifications and never miss a message' \
    'Your chats' \
    'Back up your chats' \
    'Chats' \
    'People' \
    'Rooms' \
    'Home' || true)"
  if [ "$provider_ready" != "1" ] && ! provider_flow_done; then
    echo "ElementX did not finish provider selection for $LOCAL_HOST" >&2
    dump_ui >&2 || true
    exit 1
  fi
fi

if ! login_flow_done && wait_for_text 'Username' 25; then
  tap 250 1080
  sleep 1
  input_text "$USERNAME"
  sleep 1
  tap 250 1275
  sleep 1
  input_text "$PASSWORD"
  sleep 1
  tap_element "$(dump_ui)" "Continue" 540 1870
  sleep 6
fi

STATE="$(wait_for_any_text 40 \
  'Confirm your digital identity' \
  'Help improve Element X' \
  'Error' \
  'Allow notifications and never miss a message' \
  'Your chats' \
  'Back up your chats' \
  'Chats' \
  'People' \
  'Rooms' \
  'Home' || true)"

if [ "$STATE" = 'Confirm your digital identity' ]; then
  tap_element "$(dump_ui)" "Can't confirm?" 540 1860
  sleep 3
  tap_element "$(dump_ui)" "Continue reset" 540 1900
  sleep 3
  tap_element "$(dump_ui)" "Yes, reset now" 290 1167
  sleep 3
  tap_element "$(dump_ui)" "Password" 228 770
  sleep 1
  input_text "$PASSWORD"
  sleep 1
  tap_element "$(dump_ui)" "Reset identity" 540 1900
  sleep 6
  STATE="$(wait_for_any_text 30 \
    'Help improve Element X' \
    'Error' \
    'Allow notifications and never miss a message' \
    'Your chats' \
    'Back up your chats' \
    'Chats' \
    'People' \
    'Rooms' \
    'Home' || true)"
fi

while true; do
  case "$STATE" in
    'Help improve Element X')
      tap_element "$(dump_ui)" "Not now" 816 2210
      sleep 3
      ;;
    'Error')
      ui="$(dump_ui)"
      if printf '%s' "$ui" | grep -Fq 'Do not show this again'; then
        tap 245 1400
        sleep 1
        ui="$(dump_ui)"
      fi
      tap_element "$ui" "OK" 816 2210
      sleep 3
      ;;
    'Allow notifications and never miss a message')
      ui="$(dump_ui)"
      if printf '%s' "$ui" | grep -Fq 'Not now'; then
        tap_element "$ui" "Not now" 540 1860
      else
        tap_element "$ui" "OK" 540 1860
      fi
      sleep 3
      ;;
    'Your chats'|'Back up your chats'|'Chats'|'People'|'Rooms'|'Home')
      set_push_ignore_registration_error
      dismiss_error_if_present
      adb -s "$DEVICE" shell input keyevent 3
      exit 0
      ;;
    *)
      break
      ;;
  esac
  STATE="$(wait_for_any_text 30 \
    'Help improve Element X' \
    'Error' \
    'Allow notifications and never miss a message' \
    'Your chats' \
    'Back up your chats' \
    'Chats' \
    'People' \
    'Rooms' \
    'Home' || true)"
done

echo 'ElementX did not reach a signed-in screen after reset' >&2
exit 1
""",
        timeout=600,
    )
    prune_elementx_unverified_devices(client)
