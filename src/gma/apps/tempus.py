from __future__ import annotations

import sqlite3
import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from gma.apps._shell import run_bash
from gma.apps.backend_baseline import BackendBaselineSpec, restore_backend_baseline

if TYPE_CHECKING:
    from gma.runtime.controller import AndroidController


TEMPUS_BACKEND_ROOT = "/tmp/gma_tempus_export"
TEMPUS_PROJECT_DIR = f"{TEMPUS_BACKEND_ROOT}/Spotify"
TEMPUS_HEALTH_URL = "http://localhost:8010/music"
TEMPUS_COMPOSE_PROJECT = "gma-tempus"
TEMPUS_DB_PATH = f"{TEMPUS_PROJECT_DIR}/data/navidrome.db"
TEMPUS_ANDROID_PACKAGE = "com.eddyizm.tempus.debug"
TEMPUS_ANDROID_DB_PATH = "/data/user/0/com.eddyizm.tempus.debug/databases/tempo_db"
TEMPUS_SERVER_URL = "http://10.0.2.2:8010/music"
TEMPUS_USERNAME = "testuserfjx"
TEMPUS_PASSWORD = "testpass123"


def _tempus_compose(command: str) -> str:
    return (
        f"cd {TEMPUS_PROJECT_DIR} && "
        f"docker compose --project-name {TEMPUS_COMPOSE_PROJECT} -f docker-compose.yml "
        f"{command}"
    )


TEMPUS_BASELINE = BackendBaselineSpec(
    label="Tempus",
    project_dir=TEMPUS_PROJECT_DIR,
    compose_up=_tempus_compose("up -d"),
    compose_down=_tempus_compose("down --remove-orphans"),
    containers=("navidrome",),
    volume_prefixes=(TEMPUS_COMPOSE_PROJECT,),
    health_urls=(TEMPUS_HEALTH_URL,),
    wait_seconds=120,
)


def reset_tempus_backend(client: AndroidController) -> None:
    if restore_backend_baseline(client, TEMPUS_BASELINE):
        clear_tempus_user_state(client)
        return
    run_bash(
        client,
        f"""
set -euo pipefail
docker rm -f navidrome >/dev/null 2>&1 || true
if [ -d {TEMPUS_PROJECT_DIR} ]; then
  {_tempus_compose('down -v --remove-orphans >/dev/null 2>&1 || true')}
fi
docker volume rm {TEMPUS_COMPOSE_PROJECT}_data >/dev/null 2>&1 || true
rm -rf {TEMPUS_BACKEND_ROOT}
""",
        timeout=120,
    )


def clear_tempus_user_state(client: AndroidController) -> None:
    """Remove user-created Navidrome state while preserving the music catalog."""
    run_bash(
        client,
        f"""
set -euo pipefail
if [ ! -f {TEMPUS_PROJECT_DIR}/data/navidrome.db ]; then
  exit 0
fi
sqlite3 {TEMPUS_PROJECT_DIR}/data/navidrome.db <<'SQL'
delete from playlist_tracks;
delete from playlist_fields;
delete from playlist;
delete from annotation where starred = 1 or play_count > 0 or rating > 0;
SQL
""",
        timeout=60,
    )


def patch_tempus_catalog_durations(client: AndroidController) -> None:
    """Assign stable varied song durations and keep aggregate durations consistent."""
    run_bash(
        client,
        f"""
set -euo pipefail
if [ ! -f {TEMPUS_DB_PATH!r} ]; then
  exit 0
fi
python3 - <<'PY'
import hashlib
import sqlite3
from pathlib import Path

db = Path({TEMPUS_DB_PATH!r})
marker = db.parent / ".gma_varied_durations_v2"
conn = sqlite3.connect(db)
try:
    duration_stats = conn.execute(
        "select count(distinct cast(round(duration) as integer)), min(duration), max(duration) from media_file"
    ).fetchone()
    distinct_duration_count = duration_stats[0]
    min_duration = float(duration_stats[1] or 0)
    max_duration = float(duration_stats[2] or 0)
    mismatched_album_count = conn.execute(
        '''
        select count(*)
        from album a
        join (
            select album_id, round(sum(duration), 2) as total_duration
            from media_file
            group by album_id
        ) m on m.album_id = a.id
        where abs(round(a.duration, 2) - m.total_duration) > 0.01
        '''
    ).fetchone()[0]
    if (
        marker.exists()
        and distinct_duration_count >= 100
        and min_duration >= 180
        and max_duration <= 300
        and mismatched_album_count == 0
    ):
        raise SystemExit

    rows = conn.execute("select id from media_file").fetchall()
    updates = []
    for (media_id,) in rows:
        digest = hashlib.sha1(str(media_id).encode("utf-8")).digest()
        duration_seconds = 180 + int.from_bytes(digest[:4], "big") % 121
        updates.append((float(duration_seconds), media_id))
    conn.executemany("update media_file set duration = ? where id = ?", updates)
    conn.execute(
        '''
        update album
        set duration = coalesce((
            select sum(media_file.duration)
            from media_file
            where media_file.album_id = album.id
        ), 0)
        '''
    )
    tables = {{row[0] for row in conn.execute("select name from sqlite_master where type = 'table'")}}
    if {{"playlist", "playlist_tracks"}}.issubset(tables):
        conn.execute(
            '''
            update playlist
            set duration = coalesce((
                    select sum(media_file.duration)
                    from playlist_tracks
                    join media_file on media_file.id = playlist_tracks.media_file_id
                    where playlist_tracks.playlist_id = playlist.id
                ), 0),
                song_count = coalesce((
                    select count(*)
                    from playlist_tracks
                    where playlist_tracks.playlist_id = playlist.id
                ), 0)
            '''
        )
    conn.commit()
    marker.write_text("v2\\n", encoding="utf-8")
finally:
    conn.close()
PY
""",
        timeout=120,
    )


def ensure_tempus_backend(client: AndroidController) -> None:
    run_bash(
        client,
        f"""
set -euo pipefail

asset_tar="/app/dev/spotify-project.tar.gz"
if [ ! -f "$asset_tar" ]; then
  asset_tar="/app/mobileworld/spotify-project.tar.gz"
fi
if [ ! -f "$asset_tar" ]; then
  echo "Tempus project tarball not found" >&2
  exit 1
fi

validate_tempus_db() {{
  python3 - <<'PY'
import sqlite3, sys
db = "/tmp/gma_tempus_export/Spotify/data/navidrome.db"
try:
    conn = sqlite3.connect(db)
    media = conn.execute("select count(*) from media_file").fetchone()[0]
    artists = conn.execute("select count(*) from artist").fetchone()[0]
    album_links = conn.execute("select count(*) from album_artists where role='albumartist'").fetchone()[0]
    media_links = conn.execute("select count(*) from media_file_artists where role='artist'").fetchone()[0]
    unknown_participants = conn.execute(
        "select count(*) from media_file where coalesce(participants, '') like '%[Unknown Artist]%' and coalesce(artist, '') != '[Unknown Artist]'"
    ).fetchone()[0]
except Exception:
    sys.exit(1)
sys.exit(0 if media > 0 and artists > 0 and album_links > 0 and media_links > 0 and unknown_participants == 0 else 1)
PY
}}

if curl -fsS {TEMPUS_HEALTH_URL} >/dev/null 2>&1 && validate_tempus_db; then
  exit 0
fi

docker rm -f navidrome >/dev/null 2>&1 || true
if [ -d {TEMPUS_PROJECT_DIR} ]; then
  {_tempus_compose('down -v --remove-orphans >/dev/null 2>&1 || true')}
fi
rm -rf {TEMPUS_BACKEND_ROOT}
mkdir -p {TEMPUS_BACKEND_ROOT}
tar xzf "$asset_tar" -C {TEMPUS_BACKEND_ROOT}
python3 - <<'PY'
from pathlib import Path
import sqlite3
compose = Path("{TEMPUS_PROJECT_DIR}/docker-compose.yml")
lines = compose.read_text().splitlines()
if not any("ND_SCANNER_SCANONSTARTUP" in line for line in lines):
    updated = []
    inserted = False
    for line in lines:
        updated.append(line)
        if line.strip() == "ND_SCANSCHEDULE: 0":
            updated.append("      ND_SCANNER_ENABLED: 'false'")
            updated.append("      ND_SCANNER_SCANONSTARTUP: 'false'")
            inserted = True
    if not inserted:
        raise SystemExit("ND_SCANSCHEDULE line not found in Tempus compose file")
    compose.write_text("\\n".join(updated) + "\\n")

db = Path("{TEMPUS_PROJECT_DIR}/data/navidrome.db")
conn = sqlite3.connect(db)
media_cols = {{row[1] for row in conn.execute("pragma table_info(media_file)")}}
album_cols = {{row[1] for row in conn.execute("pragma table_info(album)")}}
conn.execute("delete from album_artists")
conn.execute(
    '''
    insert into album_artists (album_id, artist_id, role, sub_role)
    select id, album_artist_id, 'albumartist', ''
    from album
    where coalesce(album_artist_id, '') != ''
    '''
)
conn.execute("delete from media_file_artists")
conn.execute(
    '''
    insert into media_file_artists (media_file_id, artist_id, role, sub_role)
    select id, artist_id, 'artist', ''
    from media_file
    where coalesce(artist_id, '') != ''
    '''
)
if "participants" in album_cols:
    conn.execute(
        '''
        update album
        set participants = json_object(
            'albumartist',
            json_array(json_object('id', album_artist_id, 'name', album_artist))
        )
        where coalesce(album_artist_id, '') != ''
        '''
    )
if "search_participants" in album_cols:
    conn.execute(
        '''
        update album
        set search_participants = coalesce(album_artist, '')
        where coalesce(album_artist_id, '') != ''
        '''
    )
if "participants" in media_cols:
    conn.execute(
        '''
        update media_file
        set participants = json_object(
            'albumartist',
            json_array(
                json_object(
                    'id', coalesce((select album_artist_id from album where album.id = media_file.album_id), artist_id),
                    'name', coalesce((select album_artist from album where album.id = media_file.album_id), artist)
                )
            ),
            'artist',
            json_array(json_object('id', artist_id, 'name', artist))
        )
        where coalesce(artist_id, '') != ''
        '''
    )
if "search_participants" in media_cols:
    conn.execute(
        '''
        update media_file
        set search_participants = trim(
            coalesce(artist, '') || ' ' ||
            coalesce((select album_artist from album where album.id = media_file.album_id), '')
        )
        where coalesce(artist_id, '') != ''
        '''
    )
conn.commit()
conn.close()
PY
{_tempus_compose('up -d >/dev/null 2>&1')}
for _ in $(seq 1 60); do
  if curl -fsS {TEMPUS_HEALTH_URL} >/dev/null 2>&1 && validate_tempus_db; then
    exit 0
  fi
  sleep 2
done
echo "Tempus backend did not become ready with a valid artist catalog" >&2
exit 1
""",
        timeout=240,
    )
    patch_tempus_catalog_durations(client)


def sync_tempus_app_state(
    client: AndroidController,
    *,
    username: str = TEMPUS_USERNAME,
    password: str = TEMPUS_PASSWORD,
) -> None:
    """Install Tempus, ensure Navidrome, and select the default server in-app."""
    ensure_tempus_backend(client)
    run_bash(
        client,
        f"""
set -euo pipefail
DEVICE=emulator-5554
PACKAGE={TEMPUS_ANDROID_PACKAGE!r}
DB_PATH={TEMPUS_ANDROID_DB_PATH!r}
SERVER_URL={TEMPUS_SERVER_URL!r}
USERNAME={username!r}
PASSWORD={password!r}

if ! adb -s "$DEVICE" shell pm path "$PACKAGE" >/dev/null 2>&1; then
  apk=/app/dev/tempus.apk
  if [ ! -f "$apk" ]; then
    apk=/app/mobileworld/tempus.apk
  fi
  if [ ! -f "$apk" ]; then
    echo "Tempus APK not found" >&2
    exit 1
  fi
  adb -s "$DEVICE" install -r -g "$apk" >/dev/null
fi

adb -s "$DEVICE" shell am force-stop "$PACKAGE" >/dev/null 2>&1 || true
adb -s "$DEVICE" shell pm clear "$PACKAGE" >/dev/null 2>&1 || true
adb -s "$DEVICE" shell monkey -p "$PACKAGE" -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1 || true
for _ in $(seq 1 30); do
  if adb -s "$DEVICE" shell test -f "$DB_PATH"; then
    break
  fi
  sleep 1
done
if ! adb -s "$DEVICE" shell test -f "$DB_PATH"; then
  echo "Tempus local database was not created" >&2
  exit 1
fi

adb -s "$DEVICE" shell uiautomator dump /sdcard/tempus_ready.xml >/dev/null 2>&1 || true
ui=$(adb -s "$DEVICE" shell cat /sdcard/tempus_ready.xml 2>/dev/null || true)
if printf '%s' "$ui" | grep -q 'Battery Optimizations'; then
  adb -s "$DEVICE" shell input tap 313 1458
  sleep 3
fi

adb -s "$DEVICE" shell am force-stop "$PACKAGE" >/dev/null 2>&1 || true
LOCAL_DB=/tmp/gma_tempus_app.db
owner=$(adb -s "$DEVICE" shell stat -c '%u:%g' "$DB_PATH" 2>/dev/null | tr -d '\r' || true)
rm -f "$LOCAL_DB" "$LOCAL_DB-wal" "$LOCAL_DB-shm"
adb -s "$DEVICE" pull "$DB_PATH" "$LOCAL_DB" >/dev/null
adb -s "$DEVICE" pull "$DB_PATH-wal" "$LOCAL_DB-wal" >/dev/null 2>&1 || true
adb -s "$DEVICE" pull "$DB_PATH-shm" "$LOCAL_DB-shm" >/dev/null 2>&1 || true
export USERNAME PASSWORD SERVER_URL
python3 - <<'PY'
import os
import sqlite3
import time

conn = sqlite3.connect("/tmp/gma_tempus_app.db")
conn.execute("delete from server")
conn.execute(
    "insert into server (id, server_name, username, password, address, local_address, "
    "timestamp, low_security, client_cert) values (?, ?, ?, ?, ?, null, ?, 1, null)",
    (
        "gma-tempus",
        "GMA Tempus",
        os.environ["USERNAME"],
        os.environ["PASSWORD"],
        os.environ["SERVER_URL"],
        int(time.time() * 1000),
    ),
)
conn.commit()
conn.execute("pragma wal_checkpoint(truncate)")
conn.close()
PY
adb -s "$DEVICE" push "$LOCAL_DB" "$DB_PATH" >/dev/null
adb -s "$DEVICE" shell rm -f "$DB_PATH-wal" "$DB_PATH-shm" >/dev/null 2>&1 || true
if [ -n "$owner" ]; then
  adb -s "$DEVICE" shell chown "$owner" "$DB_PATH" >/dev/null 2>&1 || true
fi

adb -s "$DEVICE" shell monkey -p "$PACKAGE" -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1 || true
sleep 5
adb -s "$DEVICE" shell uiautomator dump /sdcard/tempus_ready.xml >/dev/null 2>&1 || true
ui=$(adb -s "$DEVICE" shell cat /sdcard/tempus_ready.xml 2>/dev/null || true)
if printf '%s' "$ui" | grep -q 'Subsonic servers'; then
  adb -s "$DEVICE" shell input tap 540 830
  sleep 8
fi
adb -s "$DEVICE" shell input keyevent 3 >/dev/null 2>&1 || true
""",
        timeout=180,
    )


def ensure_tempus_user(
    client: AndroidController,
    *,
    username: str,
    password: str = TEMPUS_PASSWORD,
    name: str | None = None,
    email: str | None = None,
    is_admin: bool = False,
) -> str:
    """Create or update a Navidrome user for task-specific Tempus sessions."""
    ensure_tempus_backend(client)
    if password != TEMPUS_PASSWORD:
        raise RuntimeError(
            "TempusUserAsset currently supports the default Tempus password only. "
            f"Use password={TEMPUS_PASSWORD!r}."
        )
    return run_bash(
        client,
        f"""
set -euo pipefail
python3 - <<'PY'
import sqlite3
import uuid
from datetime import UTC, datetime

db_path = {TEMPUS_DB_PATH!r}
default_username = {TEMPUS_USERNAME!r}
username = {username!r}
name = {name!r} or username
email = {email!r} or ""
is_admin = {bool(is_admin)!r}

conn = sqlite3.connect(db_path)
try:
    password_row = conn.execute(
        "select password from user where user_name = ? order by created_at limit 1",
        (default_username,),
    ).fetchone()
    if password_row is None:
        raise RuntimeError("Default Tempus user is missing; cannot copy password hash")
    password_hash = password_row[0]
    now = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M:%S")
    existing = conn.execute(
        "select id from user where user_name = ? order by created_at limit 1",
        (username,),
    ).fetchone()
    if existing is None:
        user_id = uuid.uuid4().hex
        conn.execute(
            '''
            insert into user (id, user_name, name, email, password, is_admin, created_at, updated_at)
            values (?, ?, ?, ?, ?, ?, ?, ?)
            ''',
            (user_id, username, name, email, password_hash, 1 if is_admin else 0, now, now),
        )
    else:
        user_id = existing[0]
        conn.execute(
            '''
            update user
            set name = ?, email = ?, password = ?, is_admin = ?, updated_at = ?
            where id = ?
            ''',
            (name, email, password_hash, 1 if is_admin else 0, now, user_id),
        )
    for (library_id,) in conn.execute("select id from library order by id").fetchall():
        conn.execute(
            "insert or ignore into user_library (user_id, library_id) values (?, ?)",
            (user_id, library_id),
        )
    conn.commit()
    print(user_id)
finally:
    conn.close()
PY
""",
        timeout=60,
    ).strip()




def repair_tempus_app_state(client: AndroidController) -> None:
    """Refresh Tempus Android state against the current Navidrome backend."""
    ensure_tempus_backend(client)
    sync_tempus_app_state(client)

def ensure_tempus_playlist(
    client: AndroidController,
    *,
    name: str,
    owner_username: str,
    comment: str | None,
    public: bool | None,
    track_titles: list[str],
    track_albums: dict[str, str] | None = None,
) -> str:
    ensure_tempus_backend(client)
    conn = sqlite3.connect(TEMPUS_DB_PATH)
    try:
        owner_row = conn.execute(
            "select id from user where user_name = ?",
            (owner_username,),
        ).fetchone()
        if owner_row is None:
            owner_row = conn.execute("select id from user order by created_at limit 1").fetchone()
        if owner_row is None:
            raise RuntimeError("Tempus playlist owner could not be resolved")
        owner_id = owner_row[0]

        track_rows = []
        track_albums = track_albums or {}
        for title in track_titles:
            album_name = track_albums.get(title)
            if album_name:
                row = conn.execute(
                    "select id, duration, size from media_file where title = ? and album = ? order by id limit 1",
                    (title, album_name),
                ).fetchone()
            else:
                row = conn.execute(
                    "select id, duration, size from media_file where title = ? order by id limit 1",
                    (title,),
                ).fetchone()
            if row is None:
                suffix = f" on album {album_name}" if album_name else ""
                raise RuntimeError(f"Tempus track title not found: {title}{suffix}")
            track_rows.append(row)

        playlist_row = conn.execute(
            "select id from playlist where owner_id = ? and name = ?",
            (owner_id, name),
        ).fetchone()
        playlist_id = playlist_row[0] if playlist_row else uuid.uuid4().hex
        now = datetime.now(tz=UTC).strftime("%Y-%m-%d %H:%M:%S")
        total_duration = float(sum(row[1] or 0 for row in track_rows))
        total_size = int(sum(row[2] or 0 for row in track_rows))
        if playlist_row is None:
            conn.execute(
                """
                insert into playlist (
                    id, name, comment, duration, song_count, public, created_at, updated_at,
                    path, sync, size, rules, evaluated_at, owner_id, uploaded_image, external_image_url
                ) values (?, ?, ?, ?, ?, ?, ?, ?, '', false, ?, null, ?, ?, '', '')
                """,
                (
                    playlist_id,
                    name,
                    comment or "",
                    total_duration,
                    len(track_rows),
                    1 if public else 0,
                    now,
                    now,
                    total_size,
                    now,
                    owner_id,
                ),
            )
        else:
            conn.execute("delete from playlist_tracks where playlist_id = ?", (playlist_id,))
            conn.execute(
                """
                update playlist
                set comment = ?, duration = ?, song_count = ?, public = ?, updated_at = ?, size = ?, evaluated_at = ?
                where id = ?
                """,
                (
                    comment or "",
                    total_duration,
                    len(track_rows),
                    1 if public else 0,
                    now,
                    total_size,
                    now,
                    playlist_id,
                ),
            )
        next_track_id = conn.execute("select coalesce(max(id), 0) from playlist_tracks").fetchone()[0] + 1
        for offset, (media_file_id, _duration, _size) in enumerate(track_rows):
            conn.execute(
                "insert into playlist_tracks (id, playlist_id, media_file_id) values (?, ?, ?)",
                (next_track_id + offset, playlist_id, media_file_id),
            )
        conn.commit()
        return playlist_id
    finally:
        conn.close()
