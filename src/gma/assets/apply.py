from __future__ import annotations

import base64
import json
import random
import sqlite3
import shlex
import subprocess
import time
from datetime import UTC, datetime
from pathlib import Path
from tempfile import NamedTemporaryFile
from urllib.parse import urlparse
from typing import TYPE_CHECKING

from loguru import logger

from gma.apps.backend_baseline import BackendBaselineSpec, restore_backend_baseline
from gma.apps.mattermost import (
    ensure_mattermost_backend as _ensure_mattermost_backend,
    login_mattermost_app as _login_mattermost_app,
    mattermost_api_request as _mattermost_api_request,
)
from gma.apps.elementx import (
    elementx_clock_override as _elementx_clock_override,
    ensure_elementx_room as _ensure_elementx_room,
    ensure_elementx_user as _ensure_elementx_user,
    find_elementx_message_event_id as _find_elementx_message_event_id,
    pin_elementx_event as _pin_elementx_event,
    send_elementx_file as _send_elementx_file,
    send_elementx_message as _send_elementx_message,
    send_elementx_poll as _send_elementx_poll,
    prune_elementx_unverified_devices as _prune_elementx_unverified_devices,
    sync_elementx_app_state as _sync_elementx_app_state,
)
from gma.apps.tempus import (
    TEMPUS_DB_PATH,
    ensure_tempus_playlist as _ensure_tempus_playlist,
    ensure_tempus_user as _ensure_tempus_user,
    sync_tempus_app_state as _sync_tempus_app_state,
)
from gma.apps.mall import apply_mall_asset as _apply_mall_asset, login_mall_app as _login_mall_app
from gma.apps.meituan import apply_meituan_asset as _apply_meituan_asset, login_meituan_app as _login_meituan_app
from gma.apps.travel import apply_travel_asset as _apply_travel_asset
from gma.apps.xiaoshiliu import apply_xiaoshiliu_asset as _apply_xiaoshiliu_asset, login_xiaoshiliu_app as _login_xiaoshiliu_app
from gma.apps.hmdp import apply_hmdp_asset as _apply_hmdp_asset, login_hmdp_app as _login_hmdp_app
from gma.assets.models import (
    AlarmAsset,
    Asset,
    CalendarEventAsset,
    ContactAsset,
    DeviceFileAsset,
    ElementXFileAsset,
    ElementXMessageAsset,
    ElementXPollAsset,
    ElementXRoomAsset,
    ElementXSessionAsset,
    ElementXUserAsset,
    HmdpBlogAsset,
    HmdpBlogCommentAsset,
    HmdpBlogLikeAsset,
    HmdpFollowAsset,
    HmdpShopAsset,
    HmdpShopFavoriteAsset,
    HmdpShopReviewAsset,
    HmdpSessionAsset,
    HmdpUserAsset,
    HmdpVoucherAsset,
    HmdpVoucherOrderAsset,
    MailAccountAsset,
    MailMessageAsset,
    MailAttachment,
    MallAddressAsset,
    MallBrandAsset,
    MallCartItemAsset,
    MallMemberAsset,
    MallOrderAsset,
    MallProductAsset,
    MallReviewAsset,
    MallSessionAsset,
    MastodonAccountAsset,
    MastodonBookmarkAsset,
    MastodonFavoriteAsset,
    MastodonFollowAsset,
    MastodonMediaStatusAsset,
    MastodonPollStatusAsset,
    MastodonPollVoteAsset,
    MastodonReblogAsset,
    MastodonSessionAsset,
    MastodonStatusAsset,
    MeituanAddressAsset,
    MeituanCartItemAsset,
    MeituanCollectionAsset,
    MeituanCommentAsset,
    MeituanFoodAsset,
    MeituanOrderAsset,
    MeituanRestaurantAsset,
    MeituanSessionAsset,
    MeituanUserAsset,
    TravelAttractionBookingAsset,
    TravelFavoriteAsset,
    TravelFlightBookingAsset,
    TravelHotelBookingAsset,
    TravelReviewAsset,
    TravelUserAsset,
    MattermostChannelAsset,
    MattermostChannelMembershipAsset,
    MattermostDirectChannelAsset,
    MattermostDirectPostAsset,
    MattermostFilePostAsset,
    MattermostPostAsset,
    MattermostReactionAsset,
    MattermostSessionAsset,
    MattermostTeamAsset,
    MattermostUserAsset,
    SmsMessageAsset,
    TempusFavoriteAsset,
    TempusPlaylistAsset,
    TempusSessionAsset,
    TempusUserAsset,
    XiaoShiLiuCollectionAsset,
    XiaoShiLiuCommentAsset,
    XiaoShiLiuFollowAsset,
    XiaoShiLiuLikeAsset,
    XiaoShiLiuNotificationAsset,
    XiaoShiLiuPostAsset,
    XiaoShiLiuSessionAsset,
    XiaoShiLiuUserAsset,
    parse_asset,
    parse_assets,
    serialize_asset,
)

if TYPE_CHECKING:
    from gma.runtime.controller import AndroidController
    from gma.tasks.base import BaseTask


ALARMS_DB_PATH = "/data/user_de/0/com.google.android.deskclock/databases/alarms.db"
CALENDAR_DB_PATH = "/data/user/0/org.fossify.calendar/databases/events.db"
CONTACTS_DB_PATH = "/data/user/0/com.android.providers.contacts/databases/contacts2.db"
MAIL_STATE_PATH = "/sdcard/Android/data/com.gmailclone/files/state.json"
MAIL_SENT_PATH = "/sdcard/Android/data/com.gmailclone/files/sentEmail.json"
MAIL_SENT_HISTORY_PATH = "/sdcard/Android/data/com.gmailclone/files/sentEmailHistory.json"
MAIL_ATTACHMENTS_DIR = "/sdcard/Android/data/com.gmailclone/files/attachments"
MAIL_PACKAGE = "com.gmailclone"
MAIL_FILES_DIR = "/sdcard/Android/data/com.gmailclone/files"
MASTODON_PROJECT_DIR = "/tmp/gma_mastodon_docker"
MASTODON_HEALTH_URL = "http://localhost:3000/health"
MASTODON_PROJECT_NAME = "mastodon-docker"
SMS_DB_PATH = "/data/user/0/com.android.providers.telephony/databases/mmssms.db"
MESSAGES_PACKAGE = "com.google.android.apps.messaging"



def apply_assets(client, assets: list[Asset], task: BaseTask | None = None) -> None:
    if not assets:
        return
    parsed = parse_assets(assets)
    task_root = _task_root(task)
    sms_assets = [asset for asset in parsed if isinstance(asset, SmsMessageAsset)]
    has_elementx_asset = any(
        isinstance(
            asset,
            (
                ElementXUserAsset,
                ElementXSessionAsset,
                ElementXRoomAsset,
                ElementXMessageAsset,
                ElementXFileAsset,
                ElementXPollAsset,
                ),
        )
        for asset in parsed
    )
    host_side_assets = (
        TempusUserAsset,
        TempusSessionAsset,
        XiaoShiLiuUserAsset,
        XiaoShiLiuSessionAsset,
        XiaoShiLiuPostAsset,
        XiaoShiLiuCommentAsset,
        XiaoShiLiuLikeAsset,
        XiaoShiLiuCollectionAsset,
        XiaoShiLiuFollowAsset,
        XiaoShiLiuNotificationAsset,
        MallMemberAsset,
        MallSessionAsset,
        MallAddressAsset,
        MallBrandAsset,
        MallProductAsset,
        MallCartItemAsset,
        MallOrderAsset,
        MallReviewAsset,
        MeituanUserAsset,
        MeituanSessionAsset,
        MeituanRestaurantAsset,
        MeituanFoodAsset,
        MeituanAddressAsset,
        MeituanCartItemAsset,
        MeituanOrderAsset,
        MeituanCollectionAsset,
        TravelAttractionBookingAsset,
        TravelFavoriteAsset,
        TravelFlightBookingAsset,
        TravelHotelBookingAsset,
        TravelReviewAsset,
        TravelUserAsset,
        HmdpBlogAsset,
        HmdpBlogCommentAsset,
        HmdpBlogLikeAsset,
        HmdpFollowAsset,
        HmdpShopAsset,
        HmdpShopFavoriteAsset,
        HmdpShopReviewAsset,
        HmdpUserAsset,
        HmdpSessionAsset,
        HmdpVoucherAsset,
        HmdpVoucherOrderAsset,
        MeituanCommentAsset,
        MastodonAccountAsset,
        MastodonSessionAsset,
        MastodonStatusAsset,
        MastodonMediaStatusAsset,
        MastodonPollStatusAsset,
        MastodonFollowAsset,
        MastodonFavoriteAsset,
        MastodonReblogAsset,
        MastodonBookmarkAsset,
        MastodonPollVoteAsset,
    )
    if hasattr(client, "apply_assets_remote"):
        remote_batch: list[Asset] = []

        def flush_remote_batch() -> None:
            nonlocal remote_batch
            if not remote_batch:
                return
            client.apply_assets_remote(
                [serialize_asset(asset, task_root) for asset in remote_batch]
            )
            remote_batch = []

        for asset in parsed:
            if isinstance(asset, host_side_assets):
                flush_remote_batch()
                _apply_asset_direct(client, asset, task_root=task_root)
            else:
                remote_batch.append(asset)
        flush_remote_batch()
        if has_elementx_asset:
            _prune_elementx_unverified_devices(client)
        return
    for asset in parsed:
        _apply_asset_direct(client, asset, task_root=task_root)
    if sms_assets:
        _rebuild_messages_app_cache(client, sms_assets)
    if has_elementx_asset:
        _prune_elementx_unverified_devices(client)


def _task_root(task: BaseTask | None) -> Path | None:
    if task is None:
        return None
    module = __import__(task.__class__.__module__, fromlist=[task.__class__.__name__])
    module_file = getattr(module, "__file__", None)
    return Path(module_file).resolve().parent if module_file else None


def _apply_asset_direct(client: AndroidController, asset: Asset, task_root: Path | None = None) -> None:
    asset = parse_asset(asset)
    if isinstance(asset, ContactAsset):
        _insert_contact(client, asset)
    elif isinstance(asset, SmsMessageAsset):
        _insert_sms(client, asset)
    elif isinstance(asset, AlarmAsset):
        _insert_alarm(client, asset)
    elif isinstance(asset, CalendarEventAsset):
        _insert_calendar_event(client, asset)
    elif isinstance(asset, DeviceFileAsset):
        _insert_device_file(client, asset, task_root=task_root)
    elif isinstance(asset, ElementXUserAsset):
        _insert_elementx_user(client, asset)
    elif isinstance(asset, ElementXSessionAsset):
        _insert_elementx_session(client, asset)
    elif isinstance(asset, ElementXRoomAsset):
        _insert_elementx_room(client, asset)
    elif isinstance(asset, ElementXMessageAsset):
        _insert_elementx_message(client, asset)
    elif isinstance(asset, ElementXFileAsset):
        _insert_elementx_file(client, asset, task_root=task_root)
    elif isinstance(asset, ElementXPollAsset):
        _insert_elementx_poll(client, asset)
    elif isinstance(asset, MailAccountAsset):
        _insert_mail_account(client, asset)
    elif isinstance(asset, MailMessageAsset):
        _insert_mail_message(client, asset)
    elif isinstance(asset, MattermostTeamAsset):
        _insert_mattermost_team(client, asset)
    elif isinstance(asset, MattermostSessionAsset):
        _insert_mattermost_session(client, asset)
    elif isinstance(asset, MattermostChannelAsset):
        _insert_mattermost_channel(client, asset)
    elif isinstance(asset, MattermostChannelMembershipAsset):
        _insert_mattermost_channel_membership(client, asset)
    elif isinstance(asset, MattermostDirectChannelAsset):
        _insert_mattermost_direct_channel(client, asset)
    elif isinstance(asset, MattermostUserAsset):
        _insert_mattermost_user(client, asset)
    elif isinstance(asset, MattermostPostAsset):
        _insert_mattermost_post(client, asset)
    elif isinstance(asset, MattermostFilePostAsset):
        _insert_mattermost_file_post(client, asset, task_root=task_root)
    elif isinstance(asset, MattermostDirectPostAsset):
        _insert_mattermost_direct_post(client, asset)
    elif isinstance(asset, MattermostReactionAsset):
        _insert_mattermost_reaction(client, asset)
    elif isinstance(asset, TempusPlaylistAsset):
        _insert_tempus_playlist(client, asset)
    elif isinstance(asset, TempusFavoriteAsset):
        _insert_tempus_favorite(client, asset)
    elif isinstance(asset, TempusUserAsset):
        _insert_tempus_user(client, asset)
    elif isinstance(asset, TempusSessionAsset):
        _insert_tempus_session(client, asset)
    elif isinstance(asset, MastodonAccountAsset):
        _insert_mastodon_account(client, asset)
    elif isinstance(asset, MastodonSessionAsset):
        _insert_mastodon_session(client, asset)
    elif isinstance(asset, MastodonStatusAsset):
        _insert_mastodon_status(client, asset, task_root=task_root)
    elif isinstance(asset, MastodonFollowAsset):
        _insert_mastodon_follow(client, asset)
    elif isinstance(asset, MastodonFavoriteAsset):
        _insert_mastodon_status_interaction(client, asset, interaction="favorite")
    elif isinstance(asset, MastodonReblogAsset):
        _insert_mastodon_status_interaction(client, asset, interaction="reblog")
    elif isinstance(asset, MastodonBookmarkAsset):
        _insert_mastodon_status_interaction(client, asset, interaction="bookmark")
    elif isinstance(asset, MastodonPollVoteAsset):
        _insert_mastodon_poll_vote(client, asset)
    elif isinstance(asset, XiaoShiLiuSessionAsset):
        _insert_xiaoshiliu_session(client, asset)
    elif isinstance(asset, (XiaoShiLiuUserAsset, XiaoShiLiuPostAsset, XiaoShiLiuCommentAsset, XiaoShiLiuLikeAsset, XiaoShiLiuCollectionAsset, XiaoShiLiuFollowAsset, XiaoShiLiuNotificationAsset)):
        _apply_xiaoshiliu_asset(client, asset, task_root=task_root)
    elif isinstance(asset, MallSessionAsset):
        _insert_mall_session(client, asset)
    elif isinstance(asset, (MallMemberAsset, MallAddressAsset, MallProductAsset, MallBrandAsset, MallCartItemAsset, MallOrderAsset, MallReviewAsset)):
        _apply_mall_asset(client, asset)
    elif isinstance(asset, MeituanSessionAsset):
        _insert_meituan_session(client, asset)
    elif isinstance(asset, (MeituanUserAsset, MeituanRestaurantAsset, MeituanFoodAsset, MeituanAddressAsset, MeituanCartItemAsset, MeituanOrderAsset, MeituanCollectionAsset, MeituanCommentAsset)):
        _apply_meituan_asset(client, asset)
    elif isinstance(asset, (TravelUserAsset, TravelFlightBookingAsset, TravelHotelBookingAsset, TravelAttractionBookingAsset, TravelFavoriteAsset, TravelReviewAsset)):
        _apply_travel_asset(client, asset)
    elif isinstance(asset, HmdpSessionAsset):
        _insert_hmdp_session(client, asset)
    elif isinstance(asset, (HmdpUserAsset, HmdpShopAsset, HmdpBlogAsset, HmdpBlogCommentAsset, HmdpFollowAsset, HmdpShopFavoriteAsset, HmdpShopReviewAsset, HmdpBlogLikeAsset, HmdpVoucherAsset, HmdpVoucherOrderAsset)):
        _apply_hmdp_asset(client, asset)
    else:
        raise ValueError(f"Unsupported asset type: {type(asset).__name__}")


def _run_bash(client: AndroidController, script: str, timeout: float = 120.0) -> str:
    payload = base64.b64encode(script.encode("utf-8")).decode("ascii")
    command = (
        "cat <<__GMA_ASSET_B64__ | base64 -d > /tmp/gma_asset.sh\n"
        f"{payload}\n"
        "__GMA_ASSET_B64__\n"
        "bash /tmp/gma_asset.sh"
    )
    return client.exec(command, timeout=timeout)



def _repair_mail_storage_permissions(client: AndroidController) -> None:
    # adb push writes as root, but the Mail app updates these files as its
    # package uid. Keep seeded JSON writable so sent history can be persisted
    # by the app itself instead of an external watcher.
    script = f"""
set -e
DEVICE=emulator-5554
PACKAGE={shlex.quote(MAIL_PACKAGE)}
BASE={shlex.quote(MAIL_FILES_DIR)}
uid="$(adb -s "$DEVICE" shell cmd package list packages -U "$PACKAGE" 2>/dev/null | awk -F'uid:' 'NF > 1 {{print $2; exit}}' | tr -cd '0-9')"
adb -s "$DEVICE" shell su 0 mkdir -p "$BASE/attachments"
if [ -n "$uid" ]; then
  adb -s "$DEVICE" shell su 0 chown "$uid:$uid" "$BASE/state.json" "$BASE/sentEmail.json" "$BASE/sentEmailHistory.json" "$BASE/attachments" 2>/dev/null || true
  adb -s "$DEVICE" shell su 0 find "$BASE/attachments" -mindepth 1 -maxdepth 1 -exec chown "$uid:$uid" {{}} + 2>/dev/null || true
fi
adb -s "$DEVICE" shell su 0 chmod 770 "$BASE" "$BASE/attachments"
adb -s "$DEVICE" shell su 0 chmod 660 "$BASE/state.json" "$BASE/sentEmail.json" "$BASE/sentEmailHistory.json" 2>/dev/null || true
"""
    _run_bash(client, script, timeout=30)


def _write_remote_json(client: AndroidController, remote_path: str, payload: dict | list) -> None:
    with NamedTemporaryFile("w", encoding="utf-8", delete=False) as tmp:
        json.dump(payload, tmp, ensure_ascii=False)
        tmp_path = tmp.name
    try:
        client.push_file(tmp_path, remote_path)
        if remote_path in {MAIL_STATE_PATH, MAIL_SENT_PATH, MAIL_SENT_HISTORY_PATH}:
            _repair_mail_storage_permissions(client)
    finally:
        Path(tmp_path).unlink(missing_ok=True)

def _mail_date(timestamp_ms: int | None) -> str:
    dt = datetime.fromtimestamp((timestamp_ms or int(datetime.now(tz=UTC).timestamp() * 1000)) / 1000, tz=UTC)
    return dt.strftime("%b %d, %Y").replace(" 0", " ")


def _escape_sql(text: str | None) -> str:
    return (text or "").replace("'", "''")


def _coerce_epoch_seconds(value_ms: int) -> int:
    return value_ms // 1000 if value_ms > 10_000_000_000 else value_ms


def _normalize_phone(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def _find_sms_thread_id_sql(address: str, normalized_address: str) -> str:
    escaped_address = _escape_sql(address)
    escaped_normalized = _escape_sql(normalized_address)
    return (
        "coalesce((select thread_id from sms where address = '"
        + escaped_address
        + "' order by date desc limit 1), "
        "(select thread_id from sms where replace(replace(replace(replace(replace(replace(replace(ifnull(address, ''), '+', ''), '-', ''), '(', ''), ')', ''), ' ', ''), '.', ''), '/', '') = '"
        + escaped_normalized
        + "' order by date desc limit 1), "
        "(select t._id from threads t join canonical_addresses ca on t.recipient_ids = cast(ca._id as text) where ca.address = '"
        + escaped_address
        + "' order by t.date desc limit 1), "
        "(select t._id from threads t join canonical_addresses ca on t.recipient_ids = cast(ca._id as text) where replace(replace(replace(replace(replace(replace(replace(ifnull(ca.address, ''), '+', ''), '-', ''), '(', ''), ')', ''), ' ', ''), '.', ''), '/', '') = '"
        + escaped_normalized
        + "' order by t.date desc limit 1), "
        "(select _id from threads order by date desc limit 1))"
    )


def _ensure_mail_storage(client: AndroidController) -> None:
    client.launch_app("com.gmailclone")
    client.force_stop("com.gmailclone")
    client.shell(f"mkdir -p {shlex.quote(MAIL_ATTACHMENTS_DIR)}")
    raw = client.shell(f"cat {shlex.quote(MAIL_STATE_PATH)} 2>/dev/null || true")
    if not raw.strip():
        _write_remote_json(
            client,
            MAIL_STATE_PATH,
            {"username": "", "email": "", "mails": [], "sentEmails": [], "activeTab": "Mail"},
        )


def _read_mail_state(client: AndroidController) -> dict:
    _ensure_mail_storage(client)
    raw = client.shell(f"cat {shlex.quote(MAIL_STATE_PATH)} 2>/dev/null || true").replace("\r", "").strip()
    if not raw:
        return {"username": "", "email": "", "mails": [], "sentEmails": [], "activeTab": "Mail"}
    try:
        state = json.loads(raw)
        if not isinstance(state, dict):
            return {"username": "", "email": "", "mails": [], "sentEmails": [], "activeTab": "Mail"}
        state.setdefault("username", "")
        state.setdefault("email", "")
        state.setdefault("mails", [])
        state.setdefault("sentEmails", [])
        state.setdefault("activeTab", "Mail")
        return state
    except json.JSONDecodeError:
        return {"username": "", "email": "", "mails": [], "sentEmails": [], "activeTab": "Mail"}


def _restart_mail_app(client: AndroidController) -> None:
    client.force_stop("com.gmailclone")
    client.launch_app("com.gmailclone")
    client.press_home()


def _write_mail_attachment(client: AndroidController, attachment: MailAttachment | dict) -> str:
    item = attachment.model_dump() if hasattr(attachment, "model_dump") else dict(attachment)
    raw = base64.b64decode(item["content_b64"])
    remote_path = f"{MAIL_ATTACHMENTS_DIR}/{item['filename']}"
    with NamedTemporaryFile(delete=False) as tmp:
        tmp.write(raw)
        tmp_path = tmp.name
    try:
        client.push_file(tmp_path, remote_path)
    finally:
        Path(tmp_path).unlink(missing_ok=True)
    return item["filename"]


def _mail_entry_status(asset: MailMessageAsset) -> str:
    mailbox_status = {
        "inbox": "read" if asset.read else "unread",
        "sent": "read",
        "drafts": "draft",
    }
    return mailbox_status.get(asset.mailbox, "unread")


def _mail_entry_from_asset(asset: MailMessageAsset, attachments: list[str] | None = None) -> dict:
    return {
        "headers": {
            "subject": asset.subject,
            "date": _mail_date(asset.timestamp_ms),
            "from": asset.from_name or asset.from_email,
            "to": ", ".join(asset.to),
            "sender": asset.from_email,
            "senderLogo": "",
        },
        "body": asset.body,
        "status": _mail_entry_status(asset),
        "attachments": attachments or [],
        "mailbox": asset.mailbox,
    }


def _ensure_calendar_db(client: AndroidController) -> None:
    client.launch_app("org.fossify.calendar")
    client.force_stop("org.fossify.calendar")
    _run_bash(client, "adb -s emulator-5554 root >/dev/null 2>&1 || true", timeout=30)


def _mastodon_compose(command: str) -> str:
    return (
        f"cd {MASTODON_PROJECT_DIR} && "
        "docker compose --project-name mastodon-docker -f docker-compose.yml "
        f"{command}"
    )


MASTODON_BASELINE = BackendBaselineSpec(
    label="Mastodon",
    project_dir=MASTODON_PROJECT_DIR,
    compose_up=_mastodon_compose("up -d"),
    compose_down=_mastodon_compose("down --remove-orphans"),
    containers=(
        "mastodon-docker-nginx-1",
        "mastodon-docker-sidekiq-1",
        "mastodon-docker-streaming-1",
        "mastodon-docker-web-1",
        "mastodon-docker-db-1",
        "mastodon-docker-redis-1",
    ),
    volume_prefixes=(MASTODON_PROJECT_NAME,),
    health_urls=(MASTODON_HEALTH_URL,),
    wait_seconds=240,
)


def _mastodon_created_data_seed_exists(client: AndroidController) -> bool:
    script = """
for candidate in \
  /data/zhuyiqi/GMA/src/gma/assets/seed_data/mastodon \
  /app/gma/src/gma/assets/seed_data/mastodon \
  /app/gma/assets/seed_data/mastodon; do
  if [ -f "$candidate/mastodon_seed.sql.gz" ]; then
    echo yes
    exit 0
  fi
done
"""
    try:
        return client.exec(script).strip() == "yes"
    except Exception:
        return False


def _mastodon_created_data_seed_shell() -> str:
    return f"""
seed_root=""
for candidate in \
  /data/zhuyiqi/GMA/src/gma/assets/seed_data/mastodon \
  /app/gma/src/gma/assets/seed_data/mastodon \
  /app/gma/assets/seed_data/mastodon; do
  if [ -f "$candidate/mastodon_seed.sql.gz" ]; then
    seed_root="$candidate"
    break
  fi
done
if [ -n "$seed_root" ]; then
  cd {MASTODON_PROJECT_DIR}
  docker compose --project-name {MASTODON_PROJECT_NAME} -f docker-compose.yml up -d db redis >/dev/null 2>&1
  for _ in $(seq 1 60); do
    if docker compose --project-name {MASTODON_PROJECT_NAME} -f docker-compose.yml exec -T db pg_isready -U postgres -d mastodon >/dev/null 2>&1; then
      break
    fi
    sleep 2
  done
  docker compose --project-name {MASTODON_PROJECT_NAME} -f docker-compose.yml stop nginx sidekiq streaming web >/dev/null 2>&1 || true
  gunzip -c "$seed_root/mastodon_seed.sql.gz" | docker compose --project-name {MASTODON_PROJECT_NAME} -f docker-compose.yml exec -T db psql -v ON_ERROR_STOP=1 -U postgres -d mastodon >/dev/null
  if [ -d "$seed_root/system" ]; then
    docker compose --project-name {MASTODON_PROJECT_NAME} -f docker-compose.yml up -d web >/dev/null 2>&1
    docker cp "$seed_root/system/." mastodon-docker-web-1:/opt/mastodon/public/system/ >/dev/null
    docker compose --project-name {MASTODON_PROJECT_NAME} -f docker-compose.yml exec -T --user root web bash -lc 'chown -R mastodon:mastodon /opt/mastodon/public/system' >/dev/null
  fi
  docker compose --project-name {MASTODON_PROJECT_NAME} -f docker-compose.yml up -d >/dev/null 2>&1
  deadline=$((SECONDS + 180))
  while [ "$SECONDS" -lt "$deadline" ]; do
    if curl -fsS {MASTODON_HEALTH_URL} >/dev/null 2>&1; then
      break
    fi
    sleep 3
  done
  if ! curl -fsS {MASTODON_HEALTH_URL} >/dev/null 2>&1; then
    docker compose --project-name {MASTODON_PROJECT_NAME} -f docker-compose.yml logs --tail=80 web >&2 || true
    exit 1
  fi
fi
"""


def _apply_mastodon_created_data_seed(client: AndroidController) -> bool:
    if not _mastodon_created_data_seed_exists(client):
        return False
    _run_bash(client, _mastodon_created_data_seed_shell(), timeout=420)
    return True


def _ensure_mastodon_backend(client: AndroidController) -> None:
    try:
        if client.exec(f"curl -fsS {MASTODON_HEALTH_URL} >/dev/null 2>&1 && echo ok || true").strip() == "ok":
            return
    except Exception:
        pass

    launch_script = f'''
set -euo pipefail
if curl -fsS {MASTODON_HEALTH_URL} >/dev/null 2>&1; then
  exit 0
fi
docker rm -f mastodon-docker-nginx-1 mastodon-docker-sidekiq-1 mastodon-docker-streaming-1 mastodon-docker-web-1 mastodon-docker-db-1 mastodon-docker-redis-1 >/dev/null 2>&1 || true
for volume in $(docker volume ls --format '{{{{.Name}}}}' | grep -E '^mastodon-docker_' || true); do
  docker volume rm -f "$volume" >/dev/null 2>&1 || true
done
rm -rf {MASTODON_PROJECT_DIR}
mkdir -p {MASTODON_PROJECT_DIR}
cp -a /app/mastodon-docker-bk/. {MASTODON_PROJECT_DIR}/
if [ -d {MASTODON_PROJECT_DIR}/mastodon-docker ] && [ ! -f {MASTODON_PROJECT_DIR}/docker-compose.yml ]; then
  cp -a {MASTODON_PROJECT_DIR}/mastodon-docker/. {MASTODON_PROJECT_DIR}/
  rm -rf {MASTODON_PROJECT_DIR}/mastodon-docker
fi
rm -rf {MASTODON_PROJECT_DIR}/data/pgdata
mkdir -p {MASTODON_PROJECT_DIR}/data/pgdata
{_mastodon_compose('up -d db redis >/dev/null 2>&1')}
for _ in $(seq 1 60); do
  if {_mastodon_compose('exec -T db pg_isready -U postgres -d mastodon >/dev/null 2>&1')}; then
    break
  fi
  sleep 2
done
cd {MASTODON_PROJECT_DIR} && gunzip -c data/mastodon.sql.gz | docker compose --project-name mastodon-docker -f docker-compose.yml exec -T db psql -U postgres -d mastodon >/dev/null
{_mastodon_compose('up -d >/dev/null 2>&1')}
if [ -x {MASTODON_PROJECT_DIR}/scripts/seed.sh ]; then
  cd {MASTODON_PROJECT_DIR} && docker compose --project-name mastodon-docker -f docker-compose.yml exec -T web bash -lc "/app/scripts/seed.sh >/dev/null 2>&1 || true" || true
fi
'''
    payload = base64.b64encode(launch_script.encode('utf-8')).decode('ascii')
    bootstrap_py = (
        "import base64,pathlib; "
        f"pathlib.Path('/tmp/gma_mastodon_boot.sh').write_bytes(base64.b64decode('{payload}'))"
    )
    client.exec(f"python3 -c {json.dumps(bootstrap_py)}")
    client.exec("nohup bash /tmp/gma_mastodon_boot.sh >/tmp/gma_mastodon_boot.log 2>&1 &")
    deadline = time.time() + 240
    while time.time() < deadline:
        try:
            if client.exec(f"curl -fsS {MASTODON_HEALTH_URL} >/dev/null 2>&1 && echo ok || true").strip() == "ok":
                if _apply_mastodon_created_data_seed(client):
                    clear_mastodon_app_cache(client)
                return
        except Exception:
            pass
        time.sleep(3)
    log_tail = client.exec("tail -n 80 /tmp/gma_mastodon_boot.log 2>/dev/null || true")
    raise RuntimeError(f"Mastodon backend did not become ready\n{log_tail}")


def reset_mastodon_backend(client: AndroidController) -> None:
    """Restore the local Mastodon backend to its baseline seed state."""
    if restore_backend_baseline(client, MASTODON_BASELINE):
        clear_mastodon_app_cache(client)
        return
    reset_script = f"""
set -euo pipefail
if [ -f {MASTODON_PROJECT_DIR}/docker-compose.yml ]; then
  cd {MASTODON_PROJECT_DIR}
  docker compose --project-name {MASTODON_PROJECT_NAME} -f docker-compose.yml down >/dev/null 2>&1 || true
fi
docker rm -f mastodon-docker-nginx-1 mastodon-docker-sidekiq-1 mastodon-docker-streaming-1 mastodon-docker-web-1 mastodon-docker-db-1 mastodon-docker-redis-1 >/dev/null 2>&1 || true
for volume in $(docker volume ls --format '{{{{.Name}}}}' | grep -E '^mastodon-docker_' || true); do
  docker volume rm -f "$volume" >/dev/null 2>&1 || true
done
rm -rf {MASTODON_PROJECT_DIR}
mkdir -p {MASTODON_PROJECT_DIR}
cp -a /app/mastodon-docker-bk/. {MASTODON_PROJECT_DIR}/
if [ -d {MASTODON_PROJECT_DIR}/mastodon-docker ] && [ ! -f {MASTODON_PROJECT_DIR}/docker-compose.yml ]; then
  cp -a {MASTODON_PROJECT_DIR}/mastodon-docker/. {MASTODON_PROJECT_DIR}/
  rm -rf {MASTODON_PROJECT_DIR}/mastodon-docker
fi
rm -rf {MASTODON_PROJECT_DIR}/data/pgdata
mkdir -p {MASTODON_PROJECT_DIR}/data/pgdata
{_mastodon_compose('up -d db redis >/dev/null 2>&1')}
for _ in $(seq 1 60); do
  if {_mastodon_compose('exec -T db pg_isready -U postgres -d mastodon >/dev/null 2>&1')}; then
    break
  fi
  sleep 2
done
cd {MASTODON_PROJECT_DIR} && gunzip -c data/mastodon.sql.gz | docker compose --project-name {MASTODON_PROJECT_NAME} -f docker-compose.yml exec -T db psql -U postgres -d mastodon >/dev/null
{_mastodon_compose('up -d >/dev/null 2>&1')}
if [ -x {MASTODON_PROJECT_DIR}/scripts/seed.sh ]; then
  cd {MASTODON_PROJECT_DIR} && docker compose --project-name {MASTODON_PROJECT_NAME} -f docker-compose.yml exec -T web bash -lc "/app/scripts/seed.sh >/dev/null 2>&1 || true" || true
fi
"""
    _run_bash(client, reset_script, timeout=300)
    deadline = time.time() + 180
    while time.time() < deadline:
        try:
            if client.exec(f"curl -fsS {MASTODON_HEALTH_URL} >/dev/null 2>&1 && echo ok || true").strip() == "ok":
                if _apply_mastodon_created_data_seed(client):
                    clear_mastodon_app_cache(client)
                    return
                clear_mastodon_user_state(client)
                return
        except Exception:
            pass
        time.sleep(3)
    raise RuntimeError("Mastodon backend did not become healthy after reset")


def clear_mastodon_user_state(client: AndroidController) -> None:
    """Remove timeline and relationship state while preserving Mastodon accounts."""
    script = f"""
set -euo pipefail
cd {MASTODON_PROJECT_DIR}
docker compose --project-name {MASTODON_PROJECT_NAME} -f docker-compose.yml exec -T db psql -U postgres -d mastodon <<'SQL'
truncate table statuses, follows, follow_requests restart identity cascade;
SQL
"""
    _run_bash(client, script, timeout=120)


def clear_mastodon_app_cache(client: AndroidController) -> None:
    """Clear Android-side Mastodon timeline/relationship cache while preserving accounts.db."""
    script = r"""
set -euo pipefail
DEVICE=emulator-5554
PACKAGE=org.joinmastodon.android.mastodon
adb -s "$DEVICE" shell am force-stop "$PACKAGE" >/dev/null 2>&1 || true
adb -s "$DEVICE" shell run-as "$PACKAGE" sh -lc '
set -e
for f in /data/user/0/org.joinmastodon.android.mastodon/databases/*.db /data/user/0/org.joinmastodon.android.mastodon/databases/*.db-journal /data/user/0/org.joinmastodon.android.mastodon/databases/*.db-wal /data/user/0/org.joinmastodon.android.mastodon/databases/*.db-shm; do
  [ -e "$f" ] || continue
  case "$f" in
    *accounts.db|*accounts.db-journal|*accounts.db-wal|*accounts.db-shm) ;;
    *) rm -f "$f" ;;
  esac
done
rm -rf /data/user/0/org.joinmastodon.android.mastodon/cache/* 2>/dev/null || true
rm -rf /data/user/0/org.joinmastodon.android.mastodon/code_cache/* 2>/dev/null || true
rm -rf /data/user/0/org.joinmastodon.android.mastodon/app_textures/* 2>/dev/null || true
'
"""
    _run_bash(client, script, timeout=60)


def _mastodon_web_exec(client: AndroidController, script: str, timeout: float = 180.0) -> str:
    payload = base64.b64encode(script.encode("utf-8")).decode("ascii")
    inner = f"echo {shlex.quote(payload)} | base64 -d > /tmp/gma_web.sh && bash /tmp/gma_web.sh"
    return _run_bash(
        client,
        _mastodon_compose("exec -T web bash -lc " + json.dumps(inner)),
        timeout=timeout,
    )
def _mastodon_rails_runner(client: AndroidController, ruby: str, timeout: float = 180.0) -> str:
    script = f'''set -euo pipefail
export PATH="/opt/ruby/bin:$PATH"
cd /opt/mastodon
/opt/mastodon/bin/bundle exec rails runner - <<'RUBY'
{ruby}
RUBY
'''
    return _mastodon_web_exec(client, script, timeout=timeout)


def _ensure_mastodon_account_exists(
    client: AndroidController,
    username: str,
    email: str | None = None,
    display_name: str | None = None,
    bio: str | None = None,
    password: str = "password",
) -> None:
    _ensure_mastodon_backend(client)
    safe_email = email or f"{username}@example.com"
    ruby = f'''
username = {json.dumps(username)}
email = {json.dumps(safe_email)}
password = {json.dumps(password)}
display_name = {json.dumps(display_name or "")}
bio = {json.dumps(bio or "")}
account = Account.find_or_initialize_by(username: username, domain: nil)
account.display_name = display_name unless display_name.empty?
account.note = bio unless bio.empty?
account.save!(validate: false)
user = User.find_or_initialize_by(email: email)
user.account = account
user.password = password
user.confirmed_at ||= Time.now
user.approved = true if user.respond_to?(:approved=)
user.sign_in_count ||= 0 if user.respond_to?(:sign_in_count)
user.locale ||= 'en' if user.respond_to?(:locale)
now = Time.now.utc
user.current_sign_in_at = now if user.respond_to?(:current_sign_in_at=)
user.last_sign_in_at ||= now if user.respond_to?(:last_sign_in_at)
user.save!(validate: false)
attrs = {{}}
attrs[:approved] = true if user.has_attribute?(:approved)
attrs[:disabled] = false if user.has_attribute?(:disabled)
attrs[:confirmed_at] = Time.now.utc if user.has_attribute?(:confirmed_at) && user.confirmed_at.nil?
user.update_columns(attrs) unless attrs.empty?
account.reload
puts({{id: account.id, username: account.username, email: user.email}}.to_json)
'''
    _mastodon_rails_runner(client, ruby, timeout=180)


_CONTACT_PHONE_LABEL_TYPES = {
    "custom": 0,
    "home": 1,
    "mobile": 2,
    "work": 3,
    "work fax": 4,
    "home fax": 5,
    "pager": 6,
    "other": 7,
    "callback": 8,
    "car": 9,
    "company main": 10,
    "isdn": 11,
    "main": 12,
    "other fax": 13,
    "radio": 14,
    "telex": 15,
    "tty tdd": 16,
    "work mobile": 17,
    "work pager": 18,
    "assistant": 19,
    "mms": 20,
}
_CONTACT_EMAIL_LABEL_TYPES = {
    "custom": 0,
    "home": 1,
    "work": 2,
    "other": 3,
    "mobile": 4,
}
def _contact_label_values(label: str | None, mapping: dict[str, int], default_label: str) -> tuple[int, str | None]:
    normalized = (label or default_label).strip().lower()
    known_type = mapping.get(normalized)
    if known_type is not None:
        return known_type, None
    return 0, label.strip()


def _contact_label_binds(label: str | None, mapping: dict[str, int], default_label: str) -> list[str]:
    label_type, custom_label = _contact_label_values(label, mapping, default_label)
    binds = [f"data2:i:{label_type}"]
    if custom_label:
        binds.append(f"data3:s:{custom_label}")
    return binds


def _contact_bind_args(*binds: str) -> str:
    return " ".join(f"--bind {shlex.quote(bind)}" for bind in binds)


def _insert_contact(client: AndroidController, asset: ContactAsset) -> None:
    client.shell(
        "content insert --uri content://com.android.contacts/raw_contacts "
        "--bind account_type:s: --bind account_name:s: >/dev/null 2>&1; true"
    )
    raw_contacts = client.shell("content query --uri content://com.android.contacts/raw_contacts")
    lines = [line for line in raw_contacts.splitlines() if line.strip()]
    raw_contact_id = lines[-1].split("_id=", 1)[1].split(",", 1)[0].strip()
    script_lines = []
    if asset.name:
        name_parts = asset.name.split()
        given_name = name_parts[0] if name_parts else asset.name
        family_name = " ".join(name_parts[1:]) if len(name_parts) > 1 else ""
        name_binds = [
            shlex.quote(f"data1:s:{asset.name}"),
            shlex.quote(f"data2:s:{given_name}"),
        ]
        if family_name:
            name_binds.append(shlex.quote(f"data3:s:{family_name}"))
        script_lines.append(
            "content insert --uri content://com.android.contacts/data "
            f"--bind raw_contact_id:i:{raw_contact_id} "
            "--bind mimetype:s:vnd.android.cursor.item/name "
            + " ".join(f"--bind {bind}" for bind in name_binds)
        )
    script_lines.append(
        "content insert --uri content://com.android.contacts/data "
        f"--bind raw_contact_id:i:{raw_contact_id} "
        "--bind mimetype:s:vnd.android.cursor.item/phone_v2 "
        + _contact_bind_args(
            f"data1:s:{asset.phone_number}",
            *_contact_label_binds(asset.phone_label, _CONTACT_PHONE_LABEL_TYPES, "mobile"),
        )
    )
    if asset.email:
        script_lines.append(
            "content insert --uri content://com.android.contacts/data "
            f"--bind raw_contact_id:i:{raw_contact_id} "
            "--bind mimetype:s:vnd.android.cursor.item/email_v2 "
            + _contact_bind_args(
                f"data1:s:{asset.email}",
                *_contact_label_binds(asset.email_label, _CONTACT_EMAIL_LABEL_TYPES, "work"),
            )
        )
    if asset.notes:
        script_lines.append(
            "content insert --uri content://com.android.contacts/data "
            f"--bind raw_contact_id:i:{raw_contact_id} "
            "--bind mimetype:s:vnd.android.cursor.item/note "
            + _contact_bind_args(f"data1:s:{asset.notes}")
        )

    payload = base64.b64encode(("\n".join(script_lines) + "\n").encode("utf-8")).decode("ascii")
    device_cmd = (
        f"echo {payload} | base64 -d > /data/local/tmp/gma_contact_insert.sh "
        "&& sh /data/local/tmp/gma_contact_insert.sh"
    )
    client.shell(shlex.quote(device_cmd))
    db_sql_parts = []
    if asset.website:
        db_sql_parts.append(
            f"""
DELETE FROM data
WHERE raw_contact_id = {raw_contact_id}
  AND mimetype_id = (SELECT _id FROM mimetypes WHERE mimetype = 'vnd.android.cursor.item/website');
INSERT INTO data (mimetype_id, raw_contact_id, data1, data2, data3)
VALUES (
  (SELECT _id FROM mimetypes WHERE mimetype = 'vnd.android.cursor.item/website'),
  {raw_contact_id},
  '{_escape_sql(asset.website)}',
  '7',
  null
);
"""
        )
    if asset.label:
        contact_label = _escape_sql(asset.label.strip())
        db_sql_parts.append(
            f"""
WITH contact_account(account_id) AS (
  SELECT account_id FROM raw_contacts WHERE _id = {raw_contact_id}
)
INSERT INTO groups (account_id, title, group_visible, should_sync)
SELECT contact_account.account_id, '{contact_label}', 1, 1
FROM contact_account
WHERE NOT EXISTS (
  SELECT 1 FROM groups
  WHERE title = '{contact_label}'
    AND deleted = 0
    AND (
      groups.account_id = contact_account.account_id
      OR (groups.account_id IS NULL AND contact_account.account_id IS NULL)
    )
);
WITH contact_account(account_id) AS (
  SELECT account_id FROM raw_contacts WHERE _id = {raw_contact_id}
)
INSERT INTO data (mimetype_id, raw_contact_id, data1)
SELECT
  (SELECT _id FROM mimetypes WHERE mimetype = 'vnd.android.cursor.item/group_membership'),
  {raw_contact_id},
  groups._id
FROM groups
JOIN contact_account ON (
  groups.account_id = contact_account.account_id
  OR (groups.account_id IS NULL AND contact_account.account_id IS NULL)
)
WHERE groups.title = '{contact_label}' AND groups.deleted = 0
  AND NOT EXISTS (
    SELECT 1 FROM data
    WHERE raw_contact_id = {raw_contact_id}
      AND mimetype_id = (SELECT _id FROM mimetypes WHERE mimetype = 'vnd.android.cursor.item/group_membership')
      AND CAST(data1 AS TEXT) = CAST(groups._id AS TEXT)
  );
"""
        )
    if db_sql_parts:
        device = shlex.quote(getattr(client, "device", "emulator-5554"))
        db_sql = "\n".join(db_sql_parts)
        client.exec(
            f"""
adb -s {device} root >/dev/null 2>&1 || true
adb -s {device} shell <<'EOF'
sqlite3 {CONTACTS_DB_PATH} <<'SQL'
{db_sql}
SQL
EOF
""",
            timeout=30.0,
        )
    client.force_stop("com.android.contacts")


def _current_device_time_ms(client: AndroidController) -> int:
    try:
        return int((client.shell("date +%s000") or "").strip())
    except Exception:
        return int(time.time() * 1000)


def _android_utc_date_spec(timestamp_ms: int) -> str:
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC).strftime("%m%d%H%M%Y.%S")


def _set_device_time_ms(client: AndroidController, timestamp_ms: int) -> None:
    device = shlex.quote(getattr(client, "device", "emulator-5554"))
    client.exec(
        f"""
adb -s {device} root >/dev/null 2>&1 || true
adb -s {device} shell settings put global auto_time 0 >/dev/null 2>&1 || true
adb -s {device} shell settings put global auto_time_zone 0 >/dev/null 2>&1 || true
adb -s {device} shell setprop persist.sys.timezone UTC >/dev/null 2>&1 || true
adb -s {device} shell date -u {_android_utc_date_spec(timestamp_ms)} >/dev/null
""",
        timeout=30.0,
    )



def _sms_subscription_id(client: AndroidController) -> int:
    try:
        output = client.shell("content query --uri content://telephony/siminfo --projection _id")
    except Exception:
        return 1
    for line in output.splitlines():
        if "_id=" not in line:
            continue
        try:
            return int(line.split("_id=", 1)[1].split(",", 1)[0].strip())
        except Exception:
            continue
    return 1


def _rebuild_messages_app_cache(client: AndroidController, assets: list[SmsMessageAsset]) -> None:
    """Make Google Messages display the canonical mmssms.db timestamps."""
    device = shlex.quote(getattr(client, "device", "emulator-5554"))
    target_timestamps = [asset.timestamp_ms for asset in assets if asset.timestamp_ms is not None]
    max_seed_time = max(target_timestamps) if target_timestamps else _current_device_time_ms(client)
    original_time = _current_device_time_ms(client)
    bumped_time = max(max_seed_time + 60_000, original_time)

    try:
        if bumped_time > original_time + 1_000:
            _set_device_time_ms(client, bumped_time)

        client.exec(
            f"""
set -e
adb -s {device} shell am force-stop {MESSAGES_PACKAGE} >/dev/null 2>&1 || true
adb -s {device} shell pm clear {MESSAGES_PACKAGE} >/dev/null 2>&1 || true
adb -s {device} shell monkey -p {MESSAGES_PACKAGE} -c android.intent.category.LAUNCHER 1 >/dev/null 2>&1 || true
sleep 6
adb -s {device} shell am force-stop {MESSAGES_PACKAGE} >/dev/null 2>&1 || true
adb -s {device} root >/dev/null 2>&1 || true
adb -s {device} shell <<'EOF'
sqlite3 /data/user/0/{MESSAGES_PACKAGE}/databases/bugle_db <<'SQL'
PRAGMA journal_mode=WAL;
ATTACH DATABASE '{SMS_DB_PATH}' AS telephony;
UPDATE messages
SET
  received_timestamp = COALESCE((SELECT date FROM telephony.sms WHERE 'content://sms/' || telephony.sms._id = messages.sms_message_uri), received_timestamp),
  sent_timestamp = COALESCE((SELECT date FROM telephony.sms WHERE 'content://sms/' || telephony.sms._id = messages.sms_message_uri), sent_timestamp),
  queue_insert_timestamp = COALESCE((SELECT date FROM telephony.sms WHERE 'content://sms/' || telephony.sms._id = messages.sms_message_uri), queue_insert_timestamp)
WHERE sms_message_uri LIKE 'content://sms/%'
  AND EXISTS (SELECT 1 FROM telephony.sms WHERE 'content://sms/' || telephony.sms._id = messages.sms_message_uri);
INSERT INTO messages (
  conversation_id, sender_id, sent_timestamp, queue_insert_timestamp, received_timestamp,
  message_protocol, message_status, seen, read, sms_message_uri, self_id
)
SELECT
  conversations._id,
  CAST(NULLIF(conversations.current_self_id, '') AS INTEGER),
  telephony.sms.date,
  telephony.sms.date,
  telephony.sms.date,
  0,
  CASE WHEN telephony.sms.type = 2 THEN 1 ELSE 100 END,
  COALESCE(telephony.sms.seen, 1),
  COALESCE(telephony.sms.read, 1),
  'content://sms/' || telephony.sms._id,
  CAST(NULLIF(conversations.current_self_id, '') AS INTEGER)
FROM telephony.sms
JOIN conversations ON conversations.sms_thread_id = telephony.sms.thread_id
WHERE telephony.sms.body IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM messages WHERE messages.sms_message_uri = 'content://sms/' || telephony.sms._id);
INSERT INTO parts (message_id, text, timestamp, conversation_id, source)
SELECT messages._id, telephony.sms.body, telephony.sms.date, messages.conversation_id, 2
FROM messages
JOIN telephony.sms ON messages.sms_message_uri = 'content://sms/' || telephony.sms._id
WHERE telephony.sms.body IS NOT NULL
  AND NOT EXISTS (SELECT 1 FROM parts WHERE parts.message_id = messages._id);
UPDATE messages
SET
  received_timestamp = COALESCE((SELECT date FROM telephony.sms WHERE 'content://sms/' || telephony.sms._id = messages.sms_message_uri), received_timestamp),
  sent_timestamp = COALESCE((SELECT date FROM telephony.sms WHERE 'content://sms/' || telephony.sms._id = messages.sms_message_uri), sent_timestamp),
  queue_insert_timestamp = COALESCE((SELECT date FROM telephony.sms WHERE 'content://sms/' || telephony.sms._id = messages.sms_message_uri), queue_insert_timestamp)
WHERE sms_message_uri LIKE 'content://sms/%'
  AND EXISTS (SELECT 1 FROM telephony.sms WHERE 'content://sms/' || telephony.sms._id = messages.sms_message_uri);
UPDATE parts
SET timestamp = COALESCE((SELECT received_timestamp FROM messages WHERE messages._id = parts.message_id), timestamp)
WHERE EXISTS (SELECT 1 FROM messages WHERE messages._id = parts.message_id);
UPDATE conversations
SET
  sort_timestamp = COALESCE((SELECT MAX(received_timestamp) FROM messages WHERE conversation_id = conversations._id), sort_timestamp),
  latest_message_id = COALESCE((SELECT _id FROM messages WHERE conversation_id = conversations._id ORDER BY received_timestamp DESC, _id DESC LIMIT 1), latest_message_id);
UPDATE conversations
SET snippet_text = COALESCE((SELECT text FROM parts WHERE message_id = conversations.latest_message_id ORDER BY _id ASC LIMIT 1), snippet_text);
DETACH DATABASE telephony;
SQL
EOF
adb -s {device} shell am force-stop {MESSAGES_PACKAGE} >/dev/null 2>&1 || true
""",
            timeout=60.0,
        )
    finally:
        if bumped_time > original_time + 1_000:
            try:
                _set_device_time_ms(client, original_time)
            except Exception as exc:
                logger.warning(f"Failed to restore emulator time after SMS cache rebuild: {exc}")



def _wait_for_inbox_sms(client: AndroidController, address: str, body: str, timeout_s: float = 10.0) -> None:
    deadline = time.time() + timeout_s
    normalized_address = _normalize_phone(address)
    body_sql = _escape_sql(body)
    while time.time() < deadline:
        try:
            output = client.exec(
                f"""
adb -s {shlex.quote(getattr(client, "device", "emulator-5554"))} root >/dev/null 2>&1 || true
adb -s {shlex.quote(getattr(client, "device", "emulator-5554"))} shell <<'EOF'
sqlite3 {SMS_DB_PATH} <<'SQL'
SELECT COUNT(*) FROM sms WHERE replace(replace(replace(replace(replace(replace(replace(ifnull(address, ''), '+', ''), '-', ''), '(', ''), ')', ''), ' ' , ''), '.', ''), '/', '') = '{normalized_address}' AND body = '{body_sql}' AND type = 1;
SQL
EOF
""",
                timeout=10.0,
            )
            if output.strip().splitlines() and output.strip().splitlines()[-1].strip() not in {'0', ''}:
                return
        except Exception:
            pass
        time.sleep(0.5)


def _insert_sms(client: AndroidController, asset: SmsMessageAsset) -> None:
    timestamp_ms = asset.timestamp_ms or _current_device_time_ms(client)
    read_value = 1 if asset.read else 0
    address = _escape_sql(asset.address)
    body = _escape_sql(asset.body)
    normalized_address = _normalize_phone(asset.address)
    sub_id = _sms_subscription_id(client)
    device = shlex.quote(getattr(client, "device", "emulator-5554"))

    if asset.box == "inbox":
        client.exec(
            f"adb -s {device} emu sms send {shlex.quote(asset.address)} {shlex.quote(asset.body)}",
            timeout=30.0,
        )
        _wait_for_inbox_sms(client, asset.address, asset.body)
        sql = (
            "UPDATE sms SET "
            f"read = {read_value}, seen = 1, date = {timestamp_ms}, date_sent = 0, sub_id = {sub_id}, protocol = 0, reply_path_present = 0, creator = 'com.google.android.apps.messaging', error_code = 0 "
            "WHERE _id = ("
            "SELECT _id FROM sms WHERE "
            f"replace(replace(replace(replace(replace(replace(replace(ifnull(address, ''), '+', ''), '-', ''), '(', ''), ')', ''), ' ' , ''), '.', ''), '/', '') = '{normalized_address}' "
            f"AND body = '{body}' AND type = 1 ORDER BY _id DESC LIMIT 1);\n"
            "UPDATE threads SET "
            "message_count = (SELECT COUNT(*) FROM sms WHERE thread_id = threads._id), "
            "snippet = COALESCE((SELECT body FROM sms WHERE thread_id = threads._id ORDER BY date DESC, _id DESC LIMIT 1), ''), "
            "date = COALESCE((SELECT date FROM sms WHERE thread_id = threads._id ORDER BY date DESC, _id DESC LIMIT 1), 0), "
            "read = CASE WHEN EXISTS(SELECT 1 FROM sms WHERE thread_id = threads._id AND read = 0) THEN 0 ELSE 1 END, "
            f"sub_id = {sub_id} "
            "WHERE _id = (SELECT thread_id FROM sms WHERE "
            f"replace(replace(replace(replace(replace(replace(replace(ifnull(address, ''), '+', ''), '-', ''), '(', ''), ')', ''), ' ' , ''), '.', ''), '/', '') = '{normalized_address}' "
            f"AND body = '{body}' AND type = 1 ORDER BY _id DESC LIMIT 1);\n"
        )
        client.exec(
            f"""
adb -s {device} root >/dev/null 2>&1 || true
adb -s {device} shell <<'EOF'
sqlite3 {SMS_DB_PATH} <<'SQL'
{sql}
SQL
EOF
""",
            timeout=30.0,
        )
        client.force_stop(MESSAGES_PACKAGE)
        return

    sql = (
        "PRAGMA journal_mode=WAL;\n"
        "INSERT INTO canonical_addresses (address, sub_id) "
        f"SELECT '{address}', {sub_id} WHERE NOT EXISTS (SELECT 1 FROM canonical_addresses WHERE address = '{address}' AND sub_id = {sub_id});\n"
        "INSERT INTO threads (date, message_count, recipient_ids, snippet, snippet_cs, read, archived, type, error, has_attachment, sub_id) "
        f"SELECT {timestamp_ms}, 0, CAST((SELECT _id FROM canonical_addresses WHERE address = '{address}' AND sub_id = {sub_id} ORDER BY _id ASC LIMIT 1) AS TEXT), '', 0, {read_value}, 0, 0, 0, 0, {sub_id} "
        "WHERE NOT EXISTS (SELECT 1 FROM threads WHERE recipient_ids = CAST((SELECT _id FROM canonical_addresses WHERE address = '"
        f"{address}' AND sub_id = {sub_id} ORDER BY _id ASC LIMIT 1) AS TEXT));\n"
        "INSERT INTO sms (thread_id, address, date, date_sent, read, status, type, body, sub_id, seen, creator, protocol, reply_path_present, error_code) VALUES ("
        "(SELECT _id FROM threads WHERE recipient_ids = CAST((SELECT _id FROM canonical_addresses WHERE address = '"
        f"{address}' AND sub_id = {sub_id} ORDER BY _id ASC LIMIT 1) AS TEXT) ORDER BY _id ASC LIMIT 1), "
        f"'{address}', {timestamp_ms}, 0, {read_value}, -1, 2, '{body}', {sub_id}, 1, 'com.google.android.apps.messaging', NULL, NULL, -1);\n"
        "UPDATE threads SET "
        f"date = {timestamp_ms}, message_count = (SELECT COUNT(*) FROM sms WHERE thread_id = threads._id), snippet = '{body}', "
        "read = CASE WHEN EXISTS(SELECT 1 FROM sms WHERE thread_id = threads._id AND read = 0) THEN 0 ELSE 1 END, "
        f"sub_id = {sub_id} "
        "WHERE recipient_ids = CAST((SELECT _id FROM canonical_addresses WHERE address = '"
        f"{address}' AND sub_id = {sub_id} ORDER BY _id ASC LIMIT 1) AS TEXT);\n"
    )
    client.exec(
        f"""
adb -s {device} root >/dev/null 2>&1 || true
adb -s {device} shell <<'EOF'
sqlite3 {SMS_DB_PATH} <<'SQL'
{sql}
SQL
EOF
""",
        timeout=30.0,
    )
    client.force_stop(MESSAGES_PACKAGE)


_CLOCK_WEEKDAY_TO_MASK = {
    "monday": 1,
    "tuesday": 2,
    "wednesday": 4,
    "thursday": 8,
    "friday": 16,
    "saturday": 32,
    "sunday": 64,
}


def _clock_days_mask(days_of_week: tuple[str, ...]) -> int:
    return sum(_CLOCK_WEEKDAY_TO_MASK[day] for day in days_of_week)


def _insert_alarm(client: AndroidController, asset: AlarmAsset) -> None:
    label = _escape_sql(asset.label or "")
    enabled = 1 if asset.enabled else 0
    vibrate = 1 if (asset.vibrate if asset.vibrate is not None else True) else 0
    ringtone = "content://settings/system/alarm_alert"
    daysofweek = _clock_days_mask(asset.days_of_week)
    scheduled_instance_sql = ""
    if (
        asset.scheduled_year is not None
        and asset.scheduled_month is not None
        and asset.scheduled_day is not None
    ):
        if daysofweek:
            raise ValueError("scheduled alarm date is only supported for one-time alarms")
        # DeskClock stores Calendar.MONTH as zero-based in alarm_instances.
        instance_month = int(asset.scheduled_month) - 1
        scheduled_instance_sql = (
            "INSERT INTO alarm_instances ("
            "year, month, day, hour, minutes, vibrate, label, ringtone, alarm_state, wakeup, missed_reason_id, missed_reason_args, alarm_id"
            ") VALUES ("
            f"{int(asset.scheduled_year)}, {instance_month}, {int(asset.scheduled_day)}, "
            f"{asset.hour}, {asset.minute}, {vibrate}, '{label}', '{ringtone}', 0, 0, -1, '[]', "
            "(SELECT _id FROM alarm_templates WHERE hour="
            f"{asset.hour} AND minutes={asset.minute} AND ifnull(label, '')='{label}' "
            "ORDER BY _id DESC LIMIT 1)"
            ");\n"
        )
    sql = (
        "DELETE FROM alarm_instances WHERE alarm_id IN "
        f"(SELECT _id FROM alarm_templates WHERE hour={asset.hour} AND minutes={asset.minute} AND ifnull(label, '')='{label}');\n"
        "DELETE FROM alarm_templates WHERE "
        f"hour={asset.hour} AND minutes={asset.minute} AND ifnull(label, '')='{label}';\n"
        "INSERT INTO alarm_templates ("
        "external_uuid, hour, minutes, daysofweek, blackout_start, blackout_end, enabled, vibrate, label, ringtone, delete_after_use, wakeup, workflow_label, workflow_data"
        ") VALUES ("
        f"NULL, {asset.hour}, {asset.minute}, {daysofweek}, NULL, NULL, {enabled}, {vibrate}, '{label}', '{ringtone}', {0 if daysofweek else 1}, 0, NULL, NULL"
        ");\n"
        + (scheduled_instance_sql if enabled else "")
    )
    device = shlex.quote(getattr(client, "device", "emulator-5554"))
    client.exec(
        f"""
adb -s {device} root >/dev/null 2>&1 || true
adb -s {device} shell <<'EOF'
sqlite3 {ALARMS_DB_PATH} <<'SQL'
{sql}
SQL
EOF
""",
        timeout=30.0,
    )
    client.force_stop("com.google.android.deskclock")


def _insert_calendar_event(client: AndroidController, asset: CalendarEventAsset) -> None:
    _ensure_calendar_db(client)
    start_ts = _coerce_epoch_seconds(asset.start_ms)
    end_ts = _coerce_epoch_seconds(asset.end_ms)
    import_id = f"gma_asset_{random.randint(1000, 9999)}"
    last_updated = int(datetime.now(tz=UTC).timestamp() * 1000)
    reminders = list(asset.reminder_minutes[:3])
    while len(reminders) < 3:
        reminders.append(-1)
    reminder_types = [1 if minutes >= 0 else 0 for minutes in reminders]
    sql = (
        "INSERT INTO events ("
        "start_ts, end_ts, title, location, description, "
        "reminder_1_minutes, reminder_2_minutes, reminder_3_minutes, "
        "reminder_1_type, reminder_2_type, reminder_3_type, "
        "repeat_interval, repeat_rule, repeat_limit, repetition_exceptions, attendees, import_id, time_zone, "
        "flags, event_type, parent_id, last_updated, source, availability, access_level, color, type, status"
        ") VALUES ("
        f"{start_ts}, {end_ts}, '{_escape_sql(asset.title)}', '{_escape_sql(asset.location)}', '{_escape_sql(asset.description)}', "
        f"{reminders[0]}, {reminders[1]}, {reminders[2]}, "
        f"{reminder_types[0]}, {reminder_types[1]}, {reminder_types[2]}, "
        "0, 0, 0, '[]', '[]', "
        f"'{import_id}', '{_escape_sql(asset.timezone or 'UTC')}', "
        f"0, 1, 0, {last_updated}, 'gma_asset', 0, 0, 0, 0, 1"
        ");"
    )
    client.exec("adb -s emulator-5554 root >/dev/null 2>&1 || true")
    shell_cmd = f'sqlite3 {CALENDAR_DB_PATH} "{sql}"'
    client.exec(f"adb -s emulator-5554 shell {shlex.quote(shell_cmd)}")
    client.force_stop("org.fossify.calendar")


def _insert_device_file(
    client: AndroidController,
    asset: DeviceFileAsset,
    task_root: Path | None = None,
) -> None:
    payload = serialize_asset(asset, task_root)
    remote_dir = f"/sdcard/{payload['storage_dir']}"
    remote_path = f"{remote_dir}/{payload['filename']}"
    content_b64 = payload["content_b64"]
    with NamedTemporaryFile(delete=False) as tmp:
        tmp.write(base64.b64decode(content_b64))
        tmp_path = tmp.name
    try:
        client.shell(f"mkdir -p {shlex.quote(remote_dir)}")
        client.push_file(tmp_path, remote_path)
        client.shell(
            "am broadcast -a android.intent.action.MEDIA_SCANNER_SCAN_FILE "
            f"-d file://{remote_path}"
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def _insert_elementx_user(client: AndroidController, asset: ElementXUserAsset) -> None:
    _ensure_elementx_user(
        client,
        asset.username,
        password=asset.password,
        display_name=asset.display_name,
    )


def _insert_elementx_session(client: AndroidController, asset: ElementXSessionAsset) -> None:
    _ensure_elementx_user(client, asset.username, password=asset.password)
    _sync_elementx_app_state(client, username=asset.username, password=asset.password)


def _insert_elementx_room(client: AndroidController, asset: ElementXRoomAsset) -> None:
    with _elementx_clock_override(client, asset.created_at_ms):
        _ensure_elementx_room(
            client,
            name=asset.name,
            room_type=asset.room_type or "group",
            creator_username=asset.creator_username,
            creator_password=asset.creator_password,
            members=asset.members,
            member_passwords=asset.member_passwords,
            alias_localpart=asset.alias_localpart,
            topic=asset.topic,
            encrypted=asset.encrypted,
            parent_space=asset.parent_space,
        )


def _insert_elementx_message(client: AndroidController, asset: ElementXMessageAsset) -> None:
    reply_to_event_id = None
    if asset.reply_to_text is not None:
        reply_to_event_id = _find_elementx_message_event_id(
            client,
            room=asset.room,
            text=asset.reply_to_text,
            sender_username=asset.reply_to_sender_username,
        )
        if reply_to_event_id is None:
            raise RuntimeError(
                f"Could not find ElementX message to reply to in {asset.room!r}: "
                f"{asset.reply_to_text!r}"
            )
    with _elementx_clock_override(client, asset.created_at_ms):
        event_id = _send_elementx_message(
            client,
            room=asset.room,
            sender_username=asset.sender_username,
            sender_password=asset.sender_password,
            text=asset.text,
            reply_to_event_id=reply_to_event_id,
            mentions_room=asset.mentions_room,
        )
    if asset.pinned is True:
        _pin_elementx_event(
            client,
            room=asset.room,
            event_id=event_id,
            pinning_username=asset.pinning_username,
            pinning_password=asset.pinning_password,
        )


def _insert_elementx_file(
    client: AndroidController,
    asset: ElementXFileAsset,
    task_root: Path | None = None,
) -> None:
    payload_asset = serialize_asset(asset, task_root)
    with _elementx_clock_override(client, asset.created_at_ms):
        event_id = _send_elementx_file(
            client,
            room=asset.room,
            sender_username=asset.sender_username,
            sender_password=asset.sender_password,
            filename=asset.filename,
            mime_type=asset.mime_type,
            content_b64=payload_asset["content_b64"],
        )
    if asset.pinned is True:
        _pin_elementx_event(
            client,
            room=asset.room,
            event_id=event_id,
            pinning_username=asset.pinning_username,
            pinning_password=asset.pinning_password,
        )


def _insert_elementx_poll(client: AndroidController, asset: ElementXPollAsset) -> None:
    responses = [item.model_dump() for item in asset.responses]
    poll_event_id = _send_elementx_poll(
        client,
        room=asset.room,
        sender_username=asset.sender_username,
        sender_password=asset.sender_password,
        question=asset.question,
        options=asset.options,
        responses=responses,
        created_at_ms=asset.created_at_ms,
    )


def _insert_mail_account(client: AndroidController, asset: MailAccountAsset) -> None:
    # A MailAccountAsset starts a task-local mailbox. Do not preserve old inbox,
    # sent state, attachments, or ReactNativeJS send logs across task runs.
    client.shell("logcat -c >/dev/null 2>&1 || true")
    _ensure_mail_storage(client)
    client.shell(f"rm -f {shlex.quote(MAIL_ATTACHMENTS_DIR)}/* >/dev/null 2>&1 || true")
    state = {
        "username": asset.display_name,
        "email": asset.email,
        "mails": [],
        "sentEmails": [],
        "activeTab": "Mail",
    }
    _write_remote_json(client, MAIL_STATE_PATH, state)
    _write_remote_json(client, MAIL_SENT_PATH, {})
    _write_remote_json(client, MAIL_SENT_HISTORY_PATH, [])
    _restart_mail_app(client)


def _insert_mail_message(client: AndroidController, asset: MailMessageAsset) -> None:
    state = _read_mail_state(client)
    attachments = [_write_mail_attachment(client, attachment) for attachment in asset.attachments]
    entry = _mail_entry_from_asset(asset, attachments)
    if asset.mailbox == "sent":
        sent_payload = {
            "to": ", ".join(asset.to),
            "subject": asset.subject,
            "body": asset.body,
            "attachments": attachments,
            "from": asset.from_email,
            "date": entry["headers"]["date"],
        }
        _write_remote_json(client, MAIL_SENT_PATH, sent_payload)
        state["sentEmails"] = [entry] + list(state.get("sentEmails") or [])
    else:
        state["mails"] = [entry] + list(state.get("mails") or [])
    if not state.get("username"):
        state["username"] = asset.from_name or asset.from_email
    state["activeTab"] = "Mail"
    _write_remote_json(client, MAIL_STATE_PATH, state)
    _restart_mail_app(client)


def _insert_mattermost_session(client: AndroidController, asset: MattermostSessionAsset) -> None:
    _ensure_mattermost_backend(client)
    # The mobile app can lag briefly after a reset plus freshly-created user.
    # Retry once so per-task session switching is not timing-sensitive.
    last_error: Exception | None = None
    for attempt in range(2):
        try:
            if attempt:
                time.sleep(5)
            _login_mattermost_app(client, username=asset.username, password=asset.password)
            return
        except Exception as exc:
            last_error = exc
    raise RuntimeError(f"Mattermost session login failed for {asset.username}: {last_error}")


def _insert_xiaoshiliu_session(client: AndroidController, asset: XiaoShiLiuSessionAsset) -> None:
    _login_xiaoshiliu_app(
        client,
        user_id=asset.user_id,
        password=asset.password,
        ensure_user=True,
    )


def _insert_mall_session(client: AndroidController, asset: MallSessionAsset) -> None:
    _login_mall_app(
        client,
        username=asset.username,
        password=asset.password,
        ensure_user=True,
    )


def _insert_meituan_session(client: AndroidController, asset: MeituanSessionAsset) -> None:
    _login_meituan_app(
        client,
        username=asset.username,
        password=asset.password,
        ensure_user=True,
    )


def _insert_hmdp_session(client: AndroidController, asset: HmdpSessionAsset) -> None:
    _login_hmdp_app(
        client,
        phone=asset.phone,
        password=asset.password,
        ensure_user=True,
    )


def _insert_mattermost_team(client: AndroidController, asset: MattermostTeamAsset) -> None:
    _ensure_mattermost_backend(client)
    payload = {
        "name": asset.name,
        "display_name": asset.display_name,
        "type": asset.team_type,
        "description": asset.description or "",
        "allow_open_invite": asset.allow_open_invite,
    }
    try:
        _mattermost_api_request(client, "POST", "/api/v4/teams", payload)
    except Exception:
        _mattermost_api_request(client, "GET", f"/api/v4/teams/name/{asset.name}")


def _insert_mattermost_channel(client: AndroidController, asset: MattermostChannelAsset) -> None:
    _ensure_mattermost_backend(client)
    team_info = _mattermost_api_request(client, "GET", f"/api/v4/teams/name/{asset.team}")
    payload = {
        "team_id": team_info["id"],
        "name": asset.name,
        "display_name": asset.display_name or asset.name,
        "type": asset.channel_type or "O",
        "purpose": asset.purpose or "",
        "header": asset.header or "",
    }
    try:
        _mattermost_api_request(client, "POST", "/api/v4/channels", payload)
    except Exception:
        _mattermost_api_request(client, "GET", f"/api/v4/teams/name/{asset.team}/channels/name/{asset.name}")


def _insert_mattermost_user(client: AndroidController, asset: MattermostUserAsset) -> None:
    _ensure_mattermost_backend(client)
    payload = {
        "email": asset.email,
        "username": asset.username,
        "password": "password",
        "first_name": asset.first_name or "",
        "last_name": asset.last_name or "",
        "position": asset.position or "",
    }
    try:
        user_info = _mattermost_api_request(client, "POST", "/api/v4/users", payload)
    except Exception:
        user_info = _mattermost_api_request(client, "GET", f"/api/v4/users/username/{asset.username}")
    user_id = user_info["id"]
    if asset.team:
        team_info = _mattermost_api_request(client, "GET", f"/api/v4/teams/name/{asset.team}")
        try:
            _mattermost_api_request(
                client,
                "POST",
                f"/api/v4/teams/{team_info['id']}/members",
                {"team_id": team_info["id"], "user_id": user_id},
            )
        except Exception:
            pass
        for channel_name in asset.channel_memberships:
            channel_info = _mattermost_api_request(
                client,
                "GET",
                f"/api/v4/teams/name/{asset.team}/channels/name/{channel_name}",
            )
            try:
                _mattermost_api_request(
                    client,
                    "POST",
                    f"/api/v4/channels/{channel_info['id']}/members",
                    {"channel_id": channel_info["id"], "user_id": user_id},
                )
            except Exception:
                pass



def _insert_mattermost_channel_membership(client: AndroidController, asset: MattermostChannelMembershipAsset) -> None:
    _ensure_mattermost_backend(client)
    user_info = _mattermost_user_info(client, asset.username)
    channel_info = _mattermost_channel_info(client, asset.team, asset.channel)
    try:
        _mattermost_api_request(
            client,
            "POST",
            f"/api/v4/channels/{channel_info['id']}/members",
            {"channel_id": channel_info["id"], "user_id": user_info["id"]},
        )
    except Exception:
        pass


def _mattermost_channel_info(client: AndroidController, team: str, channel: str) -> dict:
    return _mattermost_api_request(
        client,
        "GET",
        f"/api/v4/teams/name/{team}/channels/name/{channel}",
    )


def _mattermost_user_info(client: AndroidController, username: str) -> dict:
    return _mattermost_api_request(client, "GET", f"/api/v4/users/username/{username}")



def _mattermost_direct_channel_info(
    client: AndroidController,
    username: str,
    other_username: str,
) -> dict:
    user_info = _mattermost_user_info(client, username)
    other_info = _mattermost_user_info(client, other_username)
    return _mattermost_api_request(
        client,
        "POST",
        "/api/v4/channels/direct",
        [user_info["id"], other_info["id"]],
    )


def _insert_mattermost_direct_channel(client: AndroidController, asset: MattermostDirectChannelAsset) -> None:
    _ensure_mattermost_backend(client)
    _mattermost_direct_channel_info(client, asset.usernames[0], asset.usernames[1])


def _mattermost_find_post(
    client: AndroidController,
    *,
    team: str,
    channel: str,
    message: str,
    username: str | None = None,
    root_id: str | None = None,
) -> dict | None:
    channel_info = _mattermost_channel_info(client, team, channel)
    user_id = None
    if username:
        user_id = _mattermost_user_info(client, username)["id"]
    channel_id = channel_info["id"]
    posts_payload = _mattermost_api_request(
        client,
        "GET",
        f"/api/v4/channels/{channel_id}/posts?page=0&per_page=200",
    )
    posts = list((posts_payload.get("posts") or {}).values())
    posts.sort(key=lambda item: int(item.get("create_at") or 0), reverse=True)
    for post in posts:
        if int(post.get("delete_at") or 0) > 0:
            continue
        if user_id is not None and post.get("user_id") != user_id:
            continue
        post_message = post.get("message") or ""
        if post_message != message and post_message.strip() != message.strip():
            continue
        if root_id is not None and (post.get("root_id") or "") != root_id:
            continue
        return post
    return None



def _mattermost_find_direct_post(
    client: AndroidController,
    *,
    username: str,
    other_username: str,
    message: str,
    author_username: str | None = None,
    root_id: str | None = None,
) -> dict | None:
    channel_info = _mattermost_direct_channel_info(client, username, other_username)
    author_id = None
    if author_username:
        author_id = _mattermost_user_info(client, author_username)["id"]
    channel_id = channel_info["id"]
    posts_payload = _mattermost_api_request(
        client,
        "GET",
        f"/api/v4/channels/{channel_id}/posts?page=0&per_page=200",
    )
    posts = list((posts_payload.get("posts") or {}).values())
    posts.sort(key=lambda item: int(item.get("create_at") or 0), reverse=True)
    for post in posts:
        if int(post.get("delete_at") or 0) > 0:
            continue
        if author_id is not None and post.get("user_id") != author_id:
            continue
        post_message = post.get("message") or ""
        if post_message != message and post_message.strip() != message.strip():
            continue
        if root_id is not None and (post.get("root_id") or "") != root_id:
            continue
        return post
    return None


def _mattermost_direct_root_post_id(client: AndroidController, asset: MattermostDirectPostAsset) -> str | None:
    if not asset.root_message:
        return None
    root_post = _mattermost_find_direct_post(
        client,
        username=asset.username,
        other_username=asset.other_username,
        message=asset.root_message,
        author_username=asset.root_username or asset.username,
    )
    if root_post is None:
        raise RuntimeError(f"Mattermost direct root post not found: {asset.root_message}")
    return root_post["id"]


def _insert_mattermost_direct_post(client: AndroidController, asset: MattermostDirectPostAsset) -> None:
    _ensure_mattermost_backend(client)
    user_info = _mattermost_user_info(client, asset.username)
    channel_info = _mattermost_direct_channel_info(client, asset.username, asset.other_username)
    root_id = _mattermost_direct_root_post_id(client, asset)
    payload = {
        "channel_id": channel_info["id"],
        "message": asset.message,
        "user_id": user_info["id"],
        "create_at": asset.create_at_ms or int(time.time() * 1000),
        "props": asset.props,
    }
    if root_id is not None:
        payload["root_id"] = root_id
    post = _mattermost_api_request(
        client,
        "POST",
        "/api/v4/posts",
        payload,
        login_id=asset.username,
        password="password",
    )
    _set_mattermost_post_timestamp(client, post["id"], asset.create_at_ms)


def _mattermost_root_post_id(client: AndroidController, asset: MattermostPostAsset | MattermostFilePostAsset) -> str | None:
    if not asset.root_message:
        return None
    root_post = _mattermost_find_post(
        client,
        team=asset.team,
        channel=asset.channel,
        message=asset.root_message,
        username=asset.root_username or asset.username,
    )
    if root_post is None:
        raise RuntimeError(f"Mattermost root post not found: {asset.root_message}")
    return root_post["id"]


def _pin_mattermost_post(
    client: AndroidController,
    post_id: str,
    *,
    login_id: str,
    password: str = "password",
) -> None:
    _mattermost_api_request(
        client,
        "POST",
        f"/api/v4/posts/{post_id}/pin",
        {},
        login_id=login_id,
        password=password,
    )


def _set_mattermost_post_timestamp(
    client: AndroidController,
    post_id: str,
    create_at_ms: int | None,
) -> None:
    if create_at_ms is None:
        return
    post_id_sql = _escape_sql(post_id)
    timestamp = int(create_at_ms)
    sql = (
        "update posts set createat = "
        + str(timestamp)
        + ", updateat = "
        + str(timestamp)
        + " where id = '"
        + post_id_sql
        + "';"
    )
    _run_bash(
        client,
        f"""
set -euo pipefail
docker exec gma_mattermost_docker-postgres-1 psql -U mmuser -d mattermost -At -c {shlex.quote(sql)}
""",
        timeout=30,
    )


def _insert_mattermost_post(client: AndroidController, asset: MattermostPostAsset) -> None:
    _ensure_mattermost_backend(client)
    user_info = _mattermost_user_info(client, asset.username)
    channel_info = _mattermost_channel_info(client, asset.team, asset.channel)
    root_id = _mattermost_root_post_id(client, asset)
    payload = {
        "channel_id": channel_info["id"],
        "message": asset.message,
        "user_id": user_info["id"],
        "create_at": asset.create_at_ms or int(time.time() * 1000),
        "props": asset.props,
    }
    if root_id is not None:
        payload["root_id"] = root_id
    post = _mattermost_api_request(
        client,
        "POST",
        "/api/v4/posts",
        payload,
        login_id=asset.username,
        password="password",
    )
    _set_mattermost_post_timestamp(client, post["id"], asset.create_at_ms)
    if asset.pinned is True:
        _pin_mattermost_post(
            client,
            post["id"],
            login_id=asset.pinning_username or "admin",
            password=asset.pinning_password,
        )


def _mattermost_upload_file(
    client: AndroidController,
    *,
    channel_id: str,
    username: str,
    filename: str,
    mime_type: str,
    content_b64: str,
) -> list[str]:
    login_body = shlex.quote(json.dumps({"login_id": username, "password": "password"}))
    channel_arg = shlex.quote(channel_id)
    filename_arg = shlex.quote(filename)
    mime_arg = shlex.quote(mime_type)
    content_arg = shlex.quote(content_b64)
    output = _run_bash(
        client,
        f"""
set -euo pipefail
upload=$(mktemp /tmp/gma_mm_upload.XXXXXX)
headers=$(mktemp)
trap "rm -f \"$upload\" \"$headers\" /tmp/gma_mm_login.json" EXIT
printf "%s" {content_arg} | base64 -d > "$upload"
FILENAME={filename_arg}
MIME_TYPE={mime_arg}

curl -fsS -D "$headers" -o /tmp/gma_mm_login.json -X POST http://localhost:8065/api/v4/users/login \
  -H "Content-Type: application/json" \
  -d {login_body} >/dev/null

token=$(grep -i "^token:" "$headers" | head -n 1 | cut -d" " -f2 | tr -d "\r")
if [ -z "$token" ]; then
  echo "Missing Mattermost auth token" >&2
  exit 1
fi
curl -fsS -X POST http://localhost:8065/api/v4/files \
  -H "Authorization: Bearer $token" \
  -F channel_id={channel_arg} \
  -F "files=@$upload;filename=$FILENAME;type=$MIME_TYPE"
"""
        ,
        timeout=120,
    )
    payload = json.loads(output) if output else {}
    file_infos = payload.get("file_infos") or []
    file_ids = [item["id"] for item in file_infos if item.get("id")]
    if not file_ids:
        raise RuntimeError(f"Mattermost file upload produced no file ids: {payload}")
    return file_ids


def _insert_mattermost_file_post(
    client: AndroidController,
    asset: MattermostFilePostAsset,
    task_root: Path | None = None,
) -> None:
    _ensure_mattermost_backend(client)
    payload_asset = serialize_asset(asset, task_root)
    user_info = _mattermost_user_info(client, asset.username)
    channel_info = _mattermost_channel_info(client, asset.team, asset.channel)
    root_id = _mattermost_root_post_id(client, asset)
    mime_type = asset.mime_type or "application/octet-stream"
    file_ids = _mattermost_upload_file(
        client,
        channel_id=channel_info["id"],
        username=asset.username,
        filename=asset.filename,
        mime_type=mime_type,
        content_b64=payload_asset["content_b64"],
    )
    payload = {
        "channel_id": channel_info["id"],
        "message": asset.message,
        "user_id": user_info["id"],
        "create_at": asset.create_at_ms or int(time.time() * 1000),
        "props": asset.props,
        "file_ids": file_ids,
    }
    if root_id is not None:
        payload["root_id"] = root_id
    post = _mattermost_api_request(
        client,
        "POST",
        "/api/v4/posts",
        payload,
        login_id=asset.username,
        password="password",
    )
    _set_mattermost_post_timestamp(client, post["id"], asset.create_at_ms)
    if asset.pinned is True:
        _pin_mattermost_post(
            client,
            post["id"],
            login_id=asset.pinning_username or "admin",
            password=asset.pinning_password,
        )

def _insert_mattermost_reaction(client: AndroidController, asset: MattermostReactionAsset) -> None:
    _ensure_mattermost_backend(client)
    user_info = _mattermost_user_info(client, asset.username)
    post = _mattermost_find_post(
        client,
        team=asset.team,
        channel=asset.channel,
        message=asset.post_message,
        username=asset.post_username,
    )
    if post is None:
        raise RuntimeError(f"Mattermost post not found for reaction: {asset.post_message}")
    payload = {
        "user_id": user_info["id"],
        "post_id": post["id"],
        "emoji_name": asset.emoji_name,
    }
    try:
        _mattermost_api_request(
            client,
            "POST",
            "/api/v4/reactions",
            payload,
            login_id=asset.username,
            password="password",
        )
    except Exception:
        pass


def _insert_tempus_playlist(client: AndroidController, asset: TempusPlaylistAsset) -> None:
    _ensure_tempus_playlist(
        client,
        name=asset.name,
        owner_username=asset.owner_username,
        comment=asset.comment,
        public=asset.public,
        track_titles=asset.track_titles,
        track_albums=asset.track_albums,
    )


def _insert_tempus_user(client: AndroidController, asset: TempusUserAsset) -> None:
    _ensure_tempus_user(
        client,
        username=asset.username,
        password=asset.password,
        name=asset.name,
        email=asset.email,
        is_admin=asset.is_admin,
    )


def _insert_tempus_session(client: AndroidController, asset: TempusSessionAsset) -> None:
    _sync_tempus_app_state(client, username=asset.username, password=asset.password)


def _insert_tempus_favorite(client: AndroidController, asset: TempusFavoriteAsset) -> None:
    target_name = asset.track_title if asset.item_type == "song" else asset.album_name
    song_album_name = asset.album_name if asset.item_type == "song" else None
    target_table = "media_file" if asset.item_type == "song" else "album"
    target_column = "title" if asset.item_type == "song" else "name"
    target_item_type = "media_file" if asset.item_type == "song" else "album"
    client.exec(
        "python3 - <<'PY'\n"
        "import sqlite3\n"
        "from datetime import UTC, datetime\n"
        f"db_path = {TEMPUS_DB_PATH!r}\n"
        f"owner_username = {asset.owner_username!r}\n"
        f"target_name = {target_name!r}\n"
        f"song_album_name = {song_album_name!r}\n"
        f"target_table = {target_table!r}\n"
        f"target_column = {target_column!r}\n"
        f"target_item_type = {target_item_type!r}\n"
        "conn = sqlite3.connect(db_path)\n"
        "owner_row = conn.execute(\n"
        "    'select id from user where user_name = ? order by created_at limit 1',\n"
        "    (owner_username,),\n"
        ").fetchone()\n"
        "if owner_row is None:\n"
        "    raise RuntimeError(f'Tempus favorite owner not found: {owner_username}')\n"
        "target_query = f'select id from {target_table} where {target_column} = ?'\n"
        "target_params = [target_name]\n"
        "if target_item_type == 'media_file' and song_album_name:\n"
        "    target_query += ' and album = ?'\n"
        "    target_params.append(song_album_name)\n"
        "target_query += ' order by id limit 1'\n"
        "target_row = conn.execute(target_query, tuple(target_params)).fetchone()\n"
        "if target_row is None:\n"
        "    suffix = f' on album {song_album_name}' if song_album_name else ''\n"
        "    raise RuntimeError(f'Tempus {target_item_type} not found: {target_name}{suffix}')\n"
        "now = datetime.now(tz=UTC).isoformat(sep=' ')\n"
        "conn.execute(\n"
        "    'delete from annotation where user_id = ? and item_id = ? and item_type = ?',\n"
        "    (owner_row[0], target_row[0], target_item_type),\n"
        ")\n"
        "conn.execute(\n"
        "    'insert into annotation (user_id, item_id, item_type, play_count, rating, starred, starred_at) '\n"
        "    'values (?, ?, ?, 0, 0, 1, ?)',\n"
        "    (owner_row[0], target_row[0], target_item_type, now),\n"
        ")\n"
        "conn.commit()\n"
        "conn.close()\n"
        "PY",
        timeout=120,
    )


def _insert_mastodon_account(client: AndroidController, asset: MastodonAccountAsset) -> None:
    _ensure_mastodon_account_exists(
        client,
        username=asset.username,
        email=asset.email,
        display_name=asset.display_name,
        bio=asset.bio,
        password=asset.password or "password",
    )


def _insert_mastodon_session(client: AndroidController, asset: MastodonSessionAsset) -> None:
    sync_mastodon_app_state(client, active_username=asset.username)


def _insert_mastodon_status(
    client: AndroidController,
    asset: MastodonStatusAsset,
    task_root: Path | None = None,
) -> None:
    _ensure_mastodon_account_exists(client, username=asset.username)
    payload = serialize_asset(asset, task_root)
    ruby = f'''
require "base64"
require "json"
require "securerandom"
require "tempfile"
require "time"

payload = JSON.parse({json.dumps(json.dumps(payload))})

def find_local_status(username, text)
  account = Account.find_by!(username: username, domain: nil)
  Status.where(account: account, text: text, reblog_of_id: nil, deleted_at: nil).order(created_at: :desc).first
end

account = Account.find_by!(username: payload["username"], domain: nil)
created_at_override = payload["created_at_ms"] ? Time.at(payload["created_at_ms"].to_f / 1000).utc : nil
thread = nil
if payload["reply_to_id"]
  thread = Status.find_by(id: payload["reply_to_id"])
elsif payload["reply_to_username"] && payload["reply_to_text"]
  thread = find_local_status(payload["reply_to_username"], payload["reply_to_text"])
end

scope = Status.where(account: account, text: payload["text"], reblog_of_id: nil, deleted_at: nil)
scope = scope.where(in_reply_to_id: thread.id) if thread
expected_media_count = (payload["media_attachments"] || []).length
needs_poll = !payload["poll"].nil?
status = scope.order(created_at: :desc).to_a.find do |candidate|
  (!needs_poll || candidate.poll.present?) && (expected_media_count.zero? || candidate.media_attachments.count >= expected_media_count)
end

poll_expires_at_override = nil
poll_service_expires_at = nil
if payload["poll"]
  poll_payload = payload["poll"]
  poll_expires_in = poll_payload.fetch("expires_in_seconds", 86_400).to_i
  desired_expires_at = if poll_payload["expires_at_ms"]
    Time.at(poll_payload["expires_at_ms"].to_f / 1000).utc
  else
    (created_at_override || Time.now.utc) + poll_expires_in
  end
  poll_expires_at_override = desired_expires_at if created_at_override || poll_payload["expires_at_ms"]
  poll_service_expires_at = poll_expires_at_override ? Time.now.utc + poll_expires_in : desired_expires_at
end

unless status
  media_ids = []
  (payload["media_attachments"] || []).each do |item|
    content_b64 = item["content_b64"]
    raise "Mastodon media insertion requires content_b64" if content_b64.nil? || content_b64.empty?
    filename = item["filename"] || "gma-mastodon-media-#{{SecureRandom.hex(4)}}.png"
    basename = File.basename(filename, File.extname(filename))
    extension = File.extname(filename)
    tempfile = Tempfile.new([basename, extension])
    tempfile.binmode
    tempfile.write(Base64.decode64(content_b64))
    tempfile.flush
    file = File.open(tempfile.path, "rb")
    media = account.media_attachments.create!(
      file: file,
      description: item["description"].to_s,
      processing: :complete
    )
    media.update!(file_content_type: item["mime_type"]) if item["mime_type"] && !item["mime_type"].empty?
    media_ids << media.id
  ensure
    file.close if defined?(file) && file && !file.closed?
    tempfile.close! if defined?(tempfile) && tempfile
  end

  options = {{
    text: payload["text"],
    visibility: payload["visibility"].to_sym,
    sensitive: !!payload["sensitive"],
    spoiler_text: payload["spoiler_text"].to_s,
  }}
  options[:thread] = thread if thread
  options[:media_ids] = media_ids if media_ids.any?
  if payload["poll"]
    poll_payload = payload["poll"]
    options[:poll] = {{
      options: poll_payload["options"],
      multiple: !!poll_payload["multiple"],
      hide_totals: !!poll_payload["hide_totals"],
      expires_at: poll_service_expires_at,
    }}
  end
  status = PostStatusService.new.call(account, options)
end

if created_at_override
  created_at = created_at_override
  status.update!(created_at: created_at, updated_at: created_at)
end
if poll_expires_at_override && status.poll
  status.poll.update_columns(expires_at: poll_expires_at_override, updated_at: Time.now.utc)
end

begin
  FeedManager.instance.push_to_home(account, status)
  account.followers.includes(:user).find_each do |follower|
    FeedManager.instance.push_to_home(follower, status)
  end
rescue => e
  warn "Could not push Mastodon status into home feeds: #{{e.message}}"
end

puts({{ id: status.id, text: status.text }}.to_json)
'''
    _mastodon_rails_runner(client, ruby, timeout=180)


def _insert_mastodon_follow(client: AndroidController, asset: MastodonFollowAsset) -> None:
    _ensure_mastodon_account_exists(client, username=asset.follower_username)
    _ensure_mastodon_account_exists(client, username=asset.followed_username)
    ruby = f'''
follower = Account.find_by!(username: {json.dumps(asset.follower_username)}, domain: nil)
followed = Account.find_by!(username: {json.dumps(asset.followed_username)}, domain: nil)
if follower.respond_to?(:follow!)
  follower.follow!(followed)
else
  Follow.find_or_create_by!(account_id: follower.id, target_account_id: followed.id)
end
if follower.user
  now = Time.now.utc
  follower.user.update_columns(current_sign_in_at: now, last_sign_in_at: follower.user.last_sign_in_at || now)
end
begin
  FeedManager.instance.merge_into_home(followed, follower)
rescue => e
  warn "Could not merge Mastodon home feed: #{{e.message}}"
end
puts({{follower: follower.username, followed: followed.username}}.to_json)
'''
    _mastodon_rails_runner(client, ruby, timeout=180)


def _insert_mastodon_status_interaction(client: AndroidController, asset, *, interaction: str) -> None:
    _ensure_mastodon_account_exists(client, username=asset.actor_username)
    ruby = f'''
require "json"
actor = Account.find_by!(username: {json.dumps(asset.actor_username)}, domain: nil)
target_account = Account.find_by!(username: {json.dumps(asset.target_username)}, domain: nil)
target = Status.where(account: target_account, text: {json.dumps(asset.target_text)}, reblog_of_id: nil, deleted_at: nil).order(created_at: :desc).first
raise "Target Mastodon status not found" if target.nil?
interaction = {json.dumps(interaction)}
case interaction
when "favorite"
  FavouriteService.new.call(actor, target)
when "reblog"
  ReblogService.new.call(actor, target, visibility: target.visibility.to_sym)
when "bookmark"
  Bookmark.find_or_create_by!(account: actor, status: target)
else
  raise "Unsupported Mastodon interaction: #{{interaction}}"
end
puts({{interaction: interaction, actor: actor.username, target: target.id}}.to_json)
'''
    _mastodon_rails_runner(client, ruby, timeout=180)


def _insert_mastodon_poll_vote(client: AndroidController, asset: MastodonPollVoteAsset) -> None:
    _ensure_mastodon_account_exists(client, username=asset.voter_username)
    payload = asset.model_dump()
    ruby = f'''
require "json"
payload = JSON.parse({json.dumps(json.dumps(payload))})

def recalc_poll!(poll)
  tallies = Array.new(poll.options.length, 0)
  poll.votes.find_each do |vote|
    tallies[vote.choice] = tallies[vote.choice].to_i + 1 if vote.choice && vote.choice < tallies.length
  end
  poll.update!(cached_tallies: tallies, votes_count: tallies.sum, voters_count: poll.votes.select(:account_id).distinct.count)
end

voter = Account.find_by!(username: payload["voter_username"], domain: nil)
poll_account = Account.find_by!(username: payload["poll_username"], domain: nil)
status = Status.where(account: poll_account, text: payload["poll_text"], reblog_of_id: nil, deleted_at: nil).order(created_at: :desc).first
raise "Target Mastodon poll status not found" if status.nil? || status.poll.nil?
poll = status.poll
choices = payload["choices"].map do |choice|
  index = poll.options.index(choice)
  raise "Poll option not found: #{{choice}}" if index.nil?
  index
end
PollVote.where(account: voter, poll: poll).delete_all
choices.each do |choice|
  PollVote.create!(account: voter, poll: poll, choice: choice)
end
recalc_poll!(poll.reload)
puts({{voter: voter.username, poll: poll.id, choices: choices}}.to_json)
'''
    _mastodon_rails_runner(client, ruby, timeout=180)


def sync_mastodon_app_state(client: AndroidController, active_username: str = "owner") -> None:
    _ensure_mastodon_backend(client)
    client.shell("am force-stop org.joinmastodon.android.mastodon")
    clear_mastodon_app_cache(client)

    # Host-side reset uses GMAClient, so use docker cp around the running
    # gma_env_* container to patch accounts.db reliably.
    if hasattr(client, "base_url"):
        parsed = urlparse(getattr(client, "base_url"))
        backend_port = parsed.port or 8000
        result = subprocess.run(
            ["docker", "ps", "--format", "{{.Names}}	{{.Ports}}"],
            check=True,
            capture_output=True,
            text=True,
        )
        container_name = None
        for line in result.stdout.splitlines():
            if f":{backend_port}->8000/tcp" in line:
                container_name = line.split("	", 1)[0]
                break
        if not container_name:
            raise RuntimeError(f"Could not resolve GMA container for backend port {backend_port}")

        mastodon_usernames = list(dict.fromkeys(["owner", "test", active_username]))
        ruby = """
require "json"
usernames = __USERNAMES__
app = Doorkeeper::Application.where(name: "Mastodon for Android", redirect_uri: "mastodon-android-auth://callback").order(:id).last
app ||= Doorkeeper::Application.create!(
  name: "Mastodon for Android",
  redirect_uri: "mastodon-android-auth://callback",
  website: "https://app.joinmastodon.org/android",
  scopes: "read write follow push"
)
payload = {}
usernames.each do |username|
  account = Account.find_by!(username: username, domain: nil)
  user = account.user
  now = Time.now.utc
  user.update_columns(current_sign_in_at: now, last_sign_in_at: user.last_sign_in_at || now) if user
  token = Doorkeeper::AccessToken.create!(application: app, resource_owner_id: user.id, scopes: "read write follow push")
  payload[username] = {
    access_token: token.token,
    created_at: token.created_at.to_i,
    client_id: app.uid,
    client_secret: app.secret,
    name: app.name,
    vapid_key: ENV["VAPID_PUBLIC_KEY"] || "dev_vapid_public_change_me",
    website: "https://app.joinmastodon.org/android",
    account: REST::AccountSerializer.new(account).as_json,
  }
end
puts payload.to_json
""".replace("__USERNAMES__", json.dumps(mastodon_usernames))
        token_map = json.loads(_mastodon_rails_runner(client, ruby, timeout=180))

        subprocess.run(
            [
                "docker",
                "exec",
                "-u",
                "0",
                container_name,
                "sh",
                "-lc",
                "rm -f /tmp/manual_masto_accounts.db; adb -s emulator-5554 shell am force-stop org.joinmastodon.android.mastodon >/dev/null 2>&1 || true; "
                "adb -s emulator-5554 exec-out run-as org.joinmastodon.android.mastodon cat "
                "/data/user/0/org.joinmastodon.android.mastodon/databases/accounts.db > /tmp/manual_masto_accounts.db",
            ],
            check=True,
        )
        subprocess.run(
            ["docker", "cp", f"{container_name}:/tmp/manual_masto_accounts.db", "/tmp/manual_masto_accounts.db"],
            check=True,
        )
        conn = sqlite3.connect('/tmp/manual_masto_accounts.db')
        rows = list(conn.execute("select id, domain, account_obj from accounts"))
        domain = next((row[1] for row in rows if row[1]), "10.0.2.2")
        existing_by_username: dict[str, str] = {}
        for account_id, _domain, account_obj_json in rows:
            obj = json.loads(account_obj_json)
            username = obj.get('username')
            if username:
                existing_by_username[username] = account_id
        template = conn.execute(
            "select flags, push_keys, push_subscription, legacy_filters, push_id, activation_info, preferences "
            "from accounts limit 1"
        ).fetchone()
        if template is None:
            template = (
                1,
                "{}",
                "{}",
                json.dumps({"filters": [], "updated": int(time.time() * 1000)}, separators=(",", ":")),
                "",
                "null",
                json.dumps(
                    {
                        "posting:default:language": "en",
                        "posting:default:sensitive": False,
                        "posting:default:visibility": "public",
                        "reading:expand:media": "default",
                        "reading:expand:spoilers": False,
                    },
                    separators=(",", ":"),
                ),
            )
        active_account_id = None
        for username, details in token_map.items():
            account = details["account"]
            account_id = existing_by_username.get(username) or f"{domain}_{account['id']}"
            if username == active_username:
                active_account_id = account_id
            token_payload = {
                'access_token': details['access_token'],
                'created_at': details['created_at'],
                'scope': 'read write follow push',
                'token_type': 'Bearer',
            }
            app_payload = {
                'client_id': details['client_id'],
                'client_secret': details['client_secret'],
                'name': details['name'],
                'vapid_key': details['vapid_key'],
                'website': details['website'],
            }
            serialized_token = json.dumps(token_payload, separators=(",", ":"))
            serialized_app = json.dumps(app_payload, separators=(",", ":"))
            serialized_account = json.dumps(account, separators=(",", ":"))
            if username in existing_by_username:
                conn.execute(
                    'update accounts set token=?, application=?, account_obj=? where id=?',
                    (serialized_token, serialized_app, serialized_account, account_id),
                )
            else:
                conn.execute(
                    'insert or replace into accounts '
                    '(id, domain, account_obj, token, application, info_last_updated, flags, push_keys, '
                    'push_subscription, legacy_filters, push_id, activation_info, preferences) '
                    'values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)',
                    (
                        account_id,
                        domain,
                        serialized_account,
                        serialized_token,
                        serialized_app,
                        int(time.time() * 1000),
                        *template,
                    ),
                )
        conn.commit()
        conn.close()
        account_manager_xml = None
        if active_account_id:
            account_manager_xml = (
                "<?xml version='1.0' encoding='utf-8' standalone='yes' ?>\n"
                "<map>\n"
                f"    <string name=\"lastActiveAccount\">{active_account_id}</string>\n"
                "</map>\n"
            )
            Path("/tmp/manual_masto_account_manager.xml").write_text(account_manager_xml)
            subprocess.run(
                ["docker", "cp", "/tmp/manual_masto_account_manager.xml", f"{container_name}:/tmp/manual_masto_account_manager.xml"],
                check=True,
            )
        else:
            logger.warning(f"Mastodon active account {active_username!r} not found in Android account database")
        subprocess.run(["docker", "cp", "/tmp/manual_masto_accounts.db", f"{container_name}:/tmp/manual_masto_accounts.db"], check=True)
        subprocess.run(
            [
                "docker",
                "exec",
                "-u",
                "0",
                container_name,
                "sh",
                "-lc",
                "adb -s emulator-5554 push /tmp/manual_masto_accounts.db /data/local/tmp/manual_masto_accounts.db >/dev/null && "
                "adb -s emulator-5554 shell run-as org.joinmastodon.android.mastodon cp /data/local/tmp/manual_masto_accounts.db /data/user/0/org.joinmastodon.android.mastodon/databases/accounts.db && "
                "adb -s emulator-5554 shell rm -f /data/local/tmp/manual_masto_accounts.db && "
                "adb -s emulator-5554 shell am force-stop org.joinmastodon.android.mastodon",
            ],
            check=True,
        )
        if account_manager_xml is not None:
            subprocess.run(
                [
                    "docker",
                    "exec",
                    "-u",
                    "0",
                    container_name,
                    "sh",
                    "-lc",
                    "adb -s emulator-5554 push /tmp/manual_masto_account_manager.xml /data/local/tmp/manual_masto_account_manager.xml >/dev/null && "
                    "adb -s emulator-5554 shell run-as org.joinmastodon.android.mastodon cp /data/local/tmp/manual_masto_account_manager.xml /data/data/org.joinmastodon.android.mastodon/shared_prefs/account_manager.xml && "
                    "adb -s emulator-5554 shell rm -f /data/local/tmp/manual_masto_account_manager.xml && "
                    "adb -s emulator-5554 shell am force-stop org.joinmastodon.android.mastodon",
                ],
                check=True,
            )
        return

    # Fallback path for controller-local usage.
    query_cmd = (
        "adb -s emulator-5554 shell run-as org.joinmastodon.android.mastodon sh -lc "
        + json.dumps(
            "sqlite3 /data/user/0/org.joinmastodon.android.mastodon/databases/accounts.db \"select id, account_obj from accounts;\""
        )
    )
    output = client.exec(query_cmd).strip()
    rows: list[dict[str, str]] = []
    for line in output.splitlines():
        parts = line.split("|", 1)
        if len(parts) != 2:
            continue
        account_id, account_obj_json = parts
        try:
            account_obj = json.loads(account_obj_json)
        except json.JSONDecodeError:
            continue
        username = account_obj.get("username")
        if username:
            rows.append({"id": account_id, "username": username})
    if not rows:
        return
    active_account_id = next((row["id"] for row in rows if row["username"] == active_username), None)
    if active_account_id:
        xml = (
            "<?xml version='1.0' encoding='utf-8' standalone='yes' ?>\n"
            "<map>\n"
            f"    <string name=\"lastActiveAccount\">{active_account_id}</string>\n"
            "</map>\n"
        )
        script = (
            "cat > /tmp/manual_masto_account_manager.xml <<EOF\n"
            + xml
            + "EOF\n"
            + "adb -s emulator-5554 push /tmp/manual_masto_account_manager.xml /data/local/tmp/manual_masto_account_manager.xml >/dev/null && "
            + "adb -s emulator-5554 shell run-as org.joinmastodon.android.mastodon cp /data/local/tmp/manual_masto_account_manager.xml /data/data/org.joinmastodon.android.mastodon/shared_prefs/account_manager.xml && "
            + "adb -s emulator-5554 shell rm -f /data/local/tmp/manual_masto_account_manager.xml && "
            + "adb -s emulator-5554 shell am force-stop org.joinmastodon.android.mastodon"
        )
        client.exec(script)
    else:
        logger.warning(f"Mastodon active account {active_username!r} not found in Android account database")
