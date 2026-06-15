from __future__ import annotations

import json
import shlex
import time
from typing import TYPE_CHECKING

from gma.apps._shell import run_bash
from gma.apps.backend_baseline import BackendBaselineSpec, restore_backend_baseline

if TYPE_CHECKING:
    from gma.runtime.controller import AndroidController


MATTERMOST_PROJECT_DIR = "/tmp/gma_mattermost_docker"
MATTERMOST_HEALTH_URL = "http://localhost:8065/api/v4/system/ping"
MATTERMOST_ADMIN_EMAIL = "admin@test.com"
MATTERMOST_ADMIN_PASSWORD = "password"
MATTERMOST_ANDROID_PACKAGE = "com.mattermost.rnbeta"
MATTERMOST_ANDROID_SERVER_DB = "/data/user/0/com.mattermost.rnbeta/files/databases/aHR0cDovLzEwLjAuMi4yOjgwNjU=.db"


def _mattermost_compose(command: str) -> str:
    return (
        f"cd {MATTERMOST_PROJECT_DIR} && "
        "docker compose -f docker-compose.yml -f docker-compose.without-nginx.yml "
        f"{command}"
    )


MATTERMOST_BASELINE = BackendBaselineSpec(
    label="Mattermost",
    project_dir=MATTERMOST_PROJECT_DIR,
    compose_up=_mattermost_compose("up -d"),
    compose_down=_mattermost_compose("down --remove-orphans"),
    containers=("gma_mattermost_docker-mattermost-1", "gma_mattermost_docker-postgres-1"),
    volume_prefixes=("gma_mattermost_docker",),
    health_urls=(MATTERMOST_HEALTH_URL,),
    wait_seconds=180,
)


def ensure_mattermost_backend(client: AndroidController) -> None:
    run_bash(
        client,
        f'''
set -euo pipefail
if curl -fsS {MATTERMOST_HEALTH_URL} >/dev/null 2>&1; then
  exit 0
fi
rm -rf {MATTERMOST_PROJECT_DIR}
cp -rp /app/mattermost-docker-bk {MATTERMOST_PROJECT_DIR}
python3 - <<'PY'
from pathlib import Path
import shutil
project = Path("{MATTERMOST_PROJECT_DIR}")
for rel in ['volumes', 'volumes_finalized', 'data.jsonl']:
    target = project / rel
    if target.exists():
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
for rel in [
    'volumes/db/var/lib/postgresql/data',
    'volumes/app/mattermost/config',
    'volumes/app/mattermost/data',
    'volumes/app/mattermost/logs',
    'volumes/app/mattermost/plugins',
    'volumes/app/mattermost/client/plugins',
    'volumes/app/mattermost/bleve-indexes',
]:
    (project / rel).mkdir(parents=True, exist_ok=True)
env = project / '.env'
compose = project / 'docker-compose.yml'
env_text = env.read_text()
env_text = env_text.replace('DOMAIN=mm.example.com', 'DOMAIN=10.0.2.2')
env_text = env_text.replace('MM_SERVICESETTINGS_SITEURL=https://${{DOMAIN}}', 'MM_SERVICESETTINGS_SITEURL=http://10.0.2.2:8065')
if 'MM_SERVICESETTINGS_ALLOWCORSFROM=' not in env_text:
    env_text += chr(10) + 'MM_SERVICESETTINGS_ALLOWCORSFROM=http://10.0.2.2:8065' + chr(10)
env.write_text(env_text)
compose_text = compose.read_text()
needle = '      - MM_SERVICESETTINGS_SITEURL\\n'
insert = needle + '      - MM_SERVICESETTINGS_ALLOWCORSFROM\\n'
if 'MM_SERVICESETTINGS_ALLOWCORSFROM' not in compose_text:
    compose_text = compose_text.replace(needle, insert, 1)
ports_needle = '      # - ${{GITLAB_PKI_CHAIN_PATH}}:/etc/ssl/certs/pki_chain.pem:ro\\n    environment:\\n'
ports_insert = '      # - ${{GITLAB_PKI_CHAIN_PATH}}:/etc/ssl/certs/pki_chain.pem:ro\\n    ports:\\n      - ${{APP_PORT}}:8065\\n    environment:\\n'
if '${{APP_PORT}}:8065' not in compose_text:
    compose_text = compose_text.replace(ports_needle, ports_insert, 1)
compose.write_text(compose_text)
PY
chown -R 2000:2000 {MATTERMOST_PROJECT_DIR}/volumes/app/mattermost >/dev/null 2>&1 || true
{_mattermost_compose('up -d >/dev/null 2>&1')}
for _ in $(seq 1 60); do
  if curl -fsS {MATTERMOST_HEALTH_URL} >/dev/null 2>&1; then
    break
  fi
  sleep 2
done
if ! curl -fsS {MATTERMOST_HEALTH_URL} >/dev/null 2>&1; then
  echo "Mattermost backend did not become ready" >&2
  exit 1
fi
cd {MATTERMOST_PROJECT_DIR}
python3 - <<'PY'
import requests
payload = {{
    'email': {MATTERMOST_ADMIN_EMAIL!r},
    'username': 'admin',
    'password': {MATTERMOST_ADMIN_PASSWORD!r},
    'first_name': 'Admin',
    'last_name': 'User',
}}
try:
    requests.post('http://localhost:8065/api/v4/users', json=payload, timeout=30)
except Exception:
    pass
PY
''',
        timeout=240,
    )


def reset_mattermost_backend(client: AndroidController) -> None:
    if restore_backend_baseline(client, MATTERMOST_BASELINE):
        return
    run_bash(
        client,
        f'''
set -euo pipefail
if [ -d {MATTERMOST_PROJECT_DIR} ]; then
  cd {MATTERMOST_PROJECT_DIR}
  docker compose down -v --remove-orphans >/dev/null 2>&1 || true
fi
rm -rf {MATTERMOST_PROJECT_DIR}
''',
        timeout=120,
    )




def mattermost_api_request(
    client: AndroidController,
    method: str,
    path: str,
    payload: dict | list | None = None,
    *,
    login_id: str = MATTERMOST_ADMIN_EMAIL,
    password: str = MATTERMOST_ADMIN_PASSWORD,
) -> dict:
    request_url = shlex.quote(f"http://localhost:8065{path}")
    login_body = shlex.quote(json.dumps({
        "login_id": login_id,
        "password": password,
    }))
    payload_body = shlex.quote(json.dumps(payload or {}))
    output = run_bash(
        client,
        f"""
set -euo pipefail
headers=$(mktemp)
trap 'rm -f "$headers"' EXIT
curl -fsS -D "$headers" -o /tmp/gma_mm_login.json -X POST http://localhost:8065/api/v4/users/login \
  -H 'Content-Type: application/json' \
  -d {login_body} >/dev/null

token=$(awk 'tolower($1)=="token:" {{print $2}}' "$headers" | tr -d '\\r')
if [ -z "$token" ]; then
  echo 'Missing Mattermost auth token' >&2
  exit 1
fi
if [ {json.dumps(method)} = "GET" ]; then
  curl -fsS -X {method} {request_url} \
    -H "Authorization: Bearer $token" \
    -H 'Content-Type: application/json'
else
  curl -fsS -X {method} {request_url} \
    -H "Authorization: Bearer $token" \
    -H 'Content-Type: application/json' \
    -d {payload_body}
fi
""",
        timeout=120,
    )
    return json.loads(output) if output else {}


def _ensure_mattermost_minimal_workspace(client: AndroidController) -> None:
    ensure_mattermost_backend(client)
    try:
        mattermost_api_request(client, "POST", "/api/v4/teams", {
            "name": "company",
            "display_name": "Company",
            "type": "O",
            "description": "Default baseline workspace",
            "allow_open_invite": True,
        })
    except Exception:
        pass

    team = mattermost_api_request(client, "GET", "/api/v4/teams/name/company")
    admin = mattermost_api_request(client, "GET", "/api/v4/users/username/admin")
    try:
        mattermost_api_request(
            client,
            "POST",
            f"/api/v4/teams/{team['id']}/members",
            {"team_id": team["id"], "user_id": admin["id"]},
        )
    except Exception:
        pass

    for name, display in (("town-square", "Town Square"), ("off-topic", "Off-Topic")):
        try:
            mattermost_api_request(client, "POST", "/api/v4/channels", {
                "team_id": team["id"],
                "name": name,
                "display_name": display,
                "type": "O",
                "purpose": "",
                "header": "",
            })
        except Exception:
            pass
        channel = mattermost_api_request(client, "GET", f"/api/v4/teams/name/company/channels/name/{name}")
        try:
            mattermost_api_request(
                client,
                "POST",
                f"/api/v4/channels/{channel['id']}/members",
                {"channel_id": channel["id"], "user_id": admin["id"]},
            )
        except Exception:
            pass



def login_mattermost_app(
    client: AndroidController,
    username: str,
    password: str = MATTERMOST_ADMIN_PASSWORD,
    *,
    server_url: str = "http://10.0.2.2:8065",
    server_display_name: str = "Company",
) -> None:
    device_arg = shlex.quote(getattr(client, "device", "emulator-5554"))
    username_arg = shlex.quote(username)
    password_arg = shlex.quote(password)
    server_url_arg = shlex.quote(server_url)
    server_name_arg = shlex.quote(server_display_name)
    run_bash(
        client,
        f"""
set -euo pipefail

DEVICE={device_arg}
USERNAME={username_arg}
PASSWORD={password_arg}
SERVER_URL={server_url_arg}
SERVER_NAME={server_name_arg}

dump_ui() {{
  adb -s "$DEVICE" shell uiautomator dump /sdcard/mm_login.xml >/dev/null 2>&1
  adb -s "$DEVICE" shell cat /sdcard/mm_login.xml
}}

adb -s "$DEVICE" shell am force-stop com.mattermost.rnbeta >/dev/null 2>&1 || true
adb -s "$DEVICE" shell pm clear com.mattermost.rnbeta >/dev/null 2>&1 || true
adb -s "$DEVICE" shell monkey -p com.mattermost.rnbeta -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1
sleep 3

ui="$(dump_ui)"
if printf '%s' "$ui" | grep -q 'permission_allow_button'; then
  adb -s "$DEVICE" shell input tap 540 1305
  sleep 2
fi

adb -s "$DEVICE" shell input tap 541 1185
sleep 1
adb -s "$DEVICE" shell input text "$SERVER_URL"
sleep 1
adb -s "$DEVICE" shell input tap 541 1323
sleep 1
adb -s "$DEVICE" shell input text "$SERVER_NAME"
sleep 1

ui="$(dump_ui)"
if printf '%s' "$ui" | grep -Eq 'server_form.server_url.input.error|server_form.connect.button.disabled|Cannot connect to the server'; then
  echo 'Mattermost server validation failed during session login setup' >&2
  exit 1
fi
if ! printf '%s' "$ui" | grep -q 'resource-id="server_form.connect.button"'; then
  echo 'Mattermost did not enable the connect button after session login setup' >&2
  exit 1
fi

adb -s "$DEVICE" shell input tap 540 1748
for _ in $(seq 1 60); do
  sleep 1
  ui="$(dump_ui)"
  if printf '%s' "$ui" | grep -Eq 'login_form.username.input|login.screen'; then
    break
  fi
done

if ! printf '%s' "$ui" | grep -Eq 'login_form.username.input|login.screen'; then
  echo 'Mattermost did not reach the login screen during session login setup' >&2
  exit 1
fi

adb -s "$DEVICE" shell input tap 540 1218
sleep 1
adb -s "$DEVICE" shell input text "$USERNAME"
sleep 1
adb -s "$DEVICE" shell input keyevent 4
sleep 1
adb -s "$DEVICE" shell input tap 514 1428
sleep 1
adb -s "$DEVICE" shell input text "$PASSWORD"
sleep 1
adb -s "$DEVICE" shell input tap 540 1695

for _ in $(seq 1 50); do
  ui="$(dump_ui)"
  if printf '%s' "$ui" | grep -q 'channel_list_header.team_display_name'; then
    adb -s "$DEVICE" shell input keyevent 3
    sleep 1
    exit 0
  fi
  if printf '%s' "$ui" | grep -Eq 'Select a team|team_sidebar.team_list.team_list_item'; then
    adb -s "$DEVICE" shell input tap 540 745
    sleep 2
    ui="$(dump_ui)"
    if printf '%s' "$ui" | grep -q 'channel_list_header.team_display_name'; then
      adb -s "$DEVICE" shell input keyevent 3
      sleep 1
      exit 0
    fi
  fi
  sleep 1
done

echo 'Mattermost did not reach the channel list during session login setup' >&2
exit 1
""",
        timeout=180,
    )



def mattermost_backend_is_healthy(client: AndroidController) -> bool:
    try:
        run_bash(
            client,
            f"curl -fsS --max-time 5 {MATTERMOST_HEALTH_URL} >/dev/null",
            timeout=10,
        )
        return True
    except Exception:
        return False




def mattermost_app_has_server_session(client: AndroidController) -> bool:
    try:
        run_bash(
            client,
            f"""
set -euo pipefail
DEVICE=emulator-5554
adb -s "$DEVICE" root >/dev/null 2>&1 || true
adb -s "$DEVICE" shell pm path {MATTERMOST_ANDROID_PACKAGE} >/dev/null
adb -s "$DEVICE" shell test -f {MATTERMOST_ANDROID_SERVER_DB}
""",
            timeout=15,
        )
        return True
    except Exception:
        return False

def repair_mattermost_app_state(client: AndroidController) -> None:
    """Refresh Mattermost Android state against the current backend.

    The mobile app keeps a local channel/message database. A valid server row is
    not enough to prove that database matches the reset backend, so always run
    the login flow. The login helper clears the package before reconnecting.
    """
    backend_was_healthy = mattermost_backend_is_healthy(client)
    _ensure_mattermost_minimal_workspace(client)
    if backend_was_healthy:
        time.sleep(2)
    login_mattermost_app(client, username="admin", password=MATTERMOST_ADMIN_PASSWORD)

def sync_mattermost_app_state(client: AndroidController) -> None:
    reset_mattermost_backend(client)
    _ensure_mattermost_minimal_workspace(client)
    # The mobile app can reject the server URL briefly after Mattermost first
    # reports healthy. Give the app-facing endpoint a moment, then retry fast
    # if the first validation attempt still races startup.
    time.sleep(10)
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            login_mattermost_app(client, username="admin", password=MATTERMOST_ADMIN_PASSWORD)
            return
        except Exception as exc:
            last_error = exc
            if attempt == 0:
                time.sleep(10)
                continue
            raise
    if last_error is not None:
        raise last_error
