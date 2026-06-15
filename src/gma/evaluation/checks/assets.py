from __future__ import annotations

import base64
import hashlib
import io
import json
import re
import shlex
import sqlite3
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import requests
from PIL import Image, ImageOps

from gma.apps._shell import run_bash
from gma.apps.elementx import (
    ELEMENTX_BASE_URL,
    ELEMENTX_COMPOSE_PROJECT,
    ELEMENTX_PROJECT_DIR,
    _fetch_existing_access_token,
    _login,
    _token_is_valid,
    elementx_room_alias,
    elementx_server_name,
    elementx_user_id,
    resolve_elementx_room_id,
    slugify_room_alias,
)
from gma.apps.mattermost import (
    MATTERMOST_ADMIN_EMAIL,
    MATTERMOST_ADMIN_PASSWORD,
    mattermost_api_request,
)
from gma.apps.mall import probe_mall_asset as _probe_mall_asset_remote
from gma.apps.meituan import probe_meituan_asset as _probe_meituan_asset_remote
from gma.apps.travel import probe_travel_asset as _probe_travel_asset_remote
from gma.apps.xiaoshiliu import probe_xiaoshiliu_asset as _probe_xiaoshiliu_asset_remote
from gma.apps.hmdp import probe_hmdp_asset as _probe_hmdp_asset_remote
from gma.apps.tempus import TEMPUS_ANDROID_DB_PATH, TEMPUS_DB_PATH
from gma.assets.apply import (
    CALENDAR_DB_PATH,
    MAIL_SENT_PATH,
    MAIL_SENT_HISTORY_PATH,
    MAIL_STATE_PATH,
    _mail_date,
    _mastodon_rails_runner,
)
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
    ElementXUserAsset,
    HmdpBlogAsset,
    HmdpBlogCommentAsset,
    HmdpBlogLikeAsset,
    HmdpFollowAsset,
    HmdpShopAsset,
    HmdpShopFavoriteAsset,
    HmdpShopReviewAsset,
    HmdpUserAsset,
    HmdpVoucherAsset,
    HmdpVoucherOrderAsset,
    MailAccountAsset,
    MailMessageAsset,
    MallAddressAsset,
    MallBrandAsset,
    MallCartItemAsset,
    MallMemberAsset,
    MallOrderAsset,
    MallProductAsset,
    MallReviewAsset,
    MastodonAccountAsset,
    MastodonBookmarkAsset,
    MastodonFavoriteAsset,
    MastodonFollowAsset,
    MastodonMediaStatusAsset,
    MastodonPollStatusAsset,
    MastodonPollVoteAsset,
    MastodonReblogAsset,
    MastodonStatusAsset,
    MeituanAddressAsset,
    MeituanCartItemAsset,
    MeituanCollectionAsset,
    MeituanCommentAsset,
    MeituanFoodAsset,
    MeituanOrderAsset,
    MeituanRestaurantAsset,
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
    XiaoShiLiuCollectionAsset,
    XiaoShiLiuCommentAsset,
    XiaoShiLiuFollowAsset,
    XiaoShiLiuLikeAsset,
    XiaoShiLiuNotificationAsset,
    XiaoShiLiuPostAsset,
    XiaoShiLiuUserAsset,
    parse_asset,
    serialize_asset,
)
from gma.evaluation.criteria import Criterion
from gma.evaluation.result import CriterionResult

if TYPE_CHECKING:
    from gma.tasks.base import BaseTask


ALARMS_DB_PATH = "/data/user_de/0/com.google.android.deskclock/databases/alarms.db"
CONTACTS_DB_PATH = "/data/user/0/com.android.providers.contacts/databases/contacts2.db"
SMS_DB_PATH = "/data/user/0/com.android.providers.telephony/databases/mmssms.db"

SMS_TYPE_BY_BOX = {
    "inbox": 1,
    "sent": 2,
}


@dataclass(slots=True)
class AssetProbe:
    label: str
    identity_exists: bool
    exact_match: bool
    current: dict[str, Any] | None = None


def _task_root(task: BaseTask | None) -> Path | None:
    if task is None:
        return None
    module = __import__(task.__class__.__module__, fromlist=[task.__class__.__name__])
    module_file = getattr(module, "__file__", None)
    return Path(module_file).resolve().parent if module_file else None


def _serialize_for_eval(asset: Asset, task: BaseTask | None = None) -> dict[str, Any]:
    return serialize_asset(parse_asset(asset), task_root=_task_root(task))


def _as_json(value: Any) -> str:
    if value is None:
        return "null"
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _normalize_phone(value: str) -> str:
    return "".join(ch for ch in value if ch.isdigit())


def _text_equal(actual: object, expected: object) -> bool:
    return ("" if actual is None else str(actual)).strip() == ("" if expected is None else str(expected)).strip()


def _optional_text_equal(actual: object, expected: object | None) -> bool:
    return expected is None or _text_equal(actual, expected)


def _text_contains(actual: object, expected: object) -> bool:
    return ("" if expected is None else str(expected)).strip() in ("" if actual is None else str(actual)).strip()


def _text_tuple(values: Any) -> tuple[str, ...]:
    return tuple(("" if value is None else str(value)).strip() for value in (values or ()))


def _coerce_epoch_seconds(value_ms: int) -> int:
    return value_ms // 1000 if value_ms > 10_000_000_000 else value_ms


def _sql_escape(value: str) -> str:
    return value.replace("'", "''")


def _mail_status(asset: MailMessageAsset) -> str:
    mailbox_status = {
        "inbox": "read" if asset.read else "unread",
        "sent": "read",
        "drafts": "draft",
    }
    return mailbox_status.get(asset.mailbox, "unread")


def _normalize_mail_subject_base(subject: str | None) -> str:
    value = (subject or "").strip()
    while value:
        normalized = re.sub(r"^\s*(?:re|fw|fwd)\s*:\s*", "", value, flags=re.IGNORECASE).strip()
        if normalized == value:
            break
        value = normalized
    return value.casefold()


def _mail_attachment_names(asset: MailMessageAsset) -> list[str]:
    return [attachment.filename for attachment in asset.attachments]


def _mail_sent_attachment_names(sent_payload: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for item in sent_payload.get("attachments") or []:
        if isinstance(item, str):
            names.append(item.rstrip("/").rsplit("/", 1)[-1])
        elif isinstance(item, dict):
            name = item.get("name") or item.get("filename")
            if name:
                names.append(str(name))
    return names


def _mail_current_from_sent_payload(sent_payload: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(sent_payload, dict) or not sent_payload:
        return None
    return {
        "mailbox": "sent",
        "from_email": sent_payload.get("from") or sent_payload.get("from_email"),
        "to": sent_payload.get("to"),
        "subject": sent_payload.get("subject"),
        "body": sent_payload.get("body"),
        "attachments": _mail_sent_attachment_names(sent_payload),
        "date": sent_payload.get("date"),
    }


def _mail_current_from_state_entry(entry: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(entry, dict) or not entry:
        return None
    headers = entry.get("headers")
    if isinstance(headers, dict):
        return {
            "mailbox": entry.get("mailbox") or "sent",
            "from_email": headers.get("sender") or entry.get("from") or entry.get("from_email"),
            "to": headers.get("to") or entry.get("to"),
            "subject": headers.get("subject") or entry.get("subject"),
            "body": entry.get("body"),
            "attachments": _mail_sent_attachment_names(entry),
            "date": headers.get("date") or entry.get("date"),
            "status": entry.get("status"),
        }
    return _mail_current_from_sent_payload(entry)


def _current_sent_mail(client) -> dict[str, Any] | None:
    return _mail_current_from_sent_payload(_read_mail_json(client, MAIL_SENT_PATH))


def _mail_sent_history(client) -> list[dict[str, Any]]:
    raw = _read_mail_json(client, MAIL_SENT_HISTORY_PATH) or []
    if not isinstance(raw, list):
        return []
    history: list[dict[str, Any]] = []
    for entry in raw:
        current = _mail_current_from_sent_payload(entry)
        if current:
            history.append(current)
    return history


def _unescape_mail_log_value(value: str) -> str:
    return value.replace("\\'", "'").replace("\\\\", "\\")


def _mail_sent_logcat_candidates(client) -> list[dict[str, Any]]:
    # The Mail app keeps the complete sent list in React state but only writes
    # the latest message to sentEmail.json. Its ReactNativeJS send log contains
    # the same payload synchronously, so use it as an evaluation-time source
    # without running a background watcher.
    raw = client.shell("logcat -d -v threadtime ReactNativeJS:I '*:S' 2>/dev/null || true").replace("\r", "")
    entries: list[dict[str, Any]] = []
    current: dict[str, Any] | None = None

    for line in raw.splitlines():
        if "Dispatching ADD_SENT_EMAIL with:" in line:
            current = {"mailbox": "sent", "from_email": "test@gmail.com", "attachments": []}
            continue
        if current is None:
            continue

        for key, value in re.findall(r"\b(subject|date|from|to|body): '((?:\\'|[^'])*)'", line):
            value = _unescape_mail_log_value(value)
            if key == "from":
                current["from_email"] = "test@gmail.com" if value == "Me" else value
            else:
                current[key] = value

        if "attachments:" in line:
            match = re.search(r"attachments:\s*\[(.*?)\]", line)
            if match:
                current["attachments"] = [
                    _unescape_mail_log_value(item)
                    for item in re.findall(r"'((?:\\'|[^'])*)'", match.group(1))
                ]
            if current.get("subject") and current.get("to") and "body" in current:
                entries.append(current)
            current = None

    return entries


def _mail_sent_candidates(client) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    candidates.extend(_mail_sent_history(client))
    candidates.extend(_mail_sent_logcat_candidates(client))
    state = _read_mail_json(client, MAIL_STATE_PATH) or {}
    if isinstance(state, dict):
        for entry in state.get("sentEmails") or []:
            current = _mail_current_from_state_entry(entry)
            if current:
                candidates.append(current)
    latest = _current_sent_mail(client)
    if latest:
        candidates.insert(0, latest)

    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = json.dumps(candidate, ensure_ascii=False, sort_keys=True)
        if key not in seen:
            seen.add(key)
            unique.append(candidate)
    return unique


def _mail_sent_current_matches(current: dict[str, Any], asset: MailMessageAsset) -> bool:
    return (
        current.get("from_email") == asset.from_email
        and current.get("to") == ", ".join(asset.to)
        and _text_equal(current.get("subject"), asset.subject)
        and _text_equal(current.get("body"), asset.body)
        and current.get("attachments") == _mail_attachment_names(asset)
    )


def _mail_reply_current_matches(current: dict[str, Any], asset: MailMessageAsset) -> bool:
    reply_to = asset.reply_to
    if reply_to is None:
        return False
    expected_subject = f"RE: {reply_to.subject}"
    return (
        current.get("from_email") == asset.from_email
        and current.get("to") == ", ".join(asset.to)
        and reply_to.from_email in asset.to
        and _text_equal(current.get("subject"), expected_subject)
        and _text_equal(asset.subject, expected_subject)
        and _text_contains(current.get("body"), asset.body)
        and all(filename in list(current.get("attachments") or []) for filename in _mail_attachment_names(asset))
    )


def _mail_expected_sender(asset: MailMessageAsset) -> str:
    return asset.from_name or asset.from_email


def _mail_expected_date(asset: MailMessageAsset) -> str | None:
    if asset.timestamp_ms is None:
        return None
    return _mail_date(asset.timestamp_ms)


def _device_file_path(asset: DeviceFileAsset) -> str:
    return f"/sdcard/{asset.storage_dir}/{asset.filename}"


def _sha256_b64(content_b64: str) -> str:
    raw = base64.b64decode(content_b64)
    return hashlib.sha256(raw).hexdigest()


def _image_fingerprint_b64(content_b64: str | None) -> dict[str, Any] | None:
    if not content_b64:
        return None
    try:
        raw = base64.b64decode(content_b64)
        image = Image.open(io.BytesIO(raw))
        image = ImageOps.exif_transpose(image).convert("RGBA")
    except Exception:
        return None
    return {
        "size": list(image.size),
        "mode": "RGBA",
        "pixel_sha256": hashlib.sha256(image.tobytes()).hexdigest(),
    }


def _image_expectations_match(
    expected_images: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    actual_images: list[dict[str, Any]] | tuple[dict[str, Any], ...],
) -> tuple[bool, dict[str, Any]]:
    expected_fingerprints = []
    for item in expected_images or []:
        fingerprint = _image_fingerprint_b64(item.get("content_b64"))
        expected_fingerprints.append({
            "filename": item.get("filename"),
            "fingerprint": fingerprint,
        })

    actual_fingerprints = []
    for item in actual_images or []:
        fingerprint = _image_fingerprint_b64(item.get("content_b64"))
        actual_fingerprints.append({
            "url": item.get("url"),
            "filename": item.get("filename"),
            "byte_sha256": item.get("byte_sha256"),
            "error": item.get("error"),
            "fingerprint": fingerprint,
        })

    used: set[int] = set()
    matched = 0
    for expected in expected_fingerprints:
        expected_fp = expected.get("fingerprint")
        if expected_fp is None:
            continue
        for index, actual in enumerate(actual_fingerprints):
            if index in used:
                continue
            if actual.get("fingerprint") == expected_fp:
                used.add(index)
                matched += 1
                break

    passed = matched == len(expected_fingerprints) and all(
        item.get("fingerprint") is not None for item in expected_fingerprints
    )
    return passed, {
        "expected_count": len(expected_fingerprints),
        "actual_count": len(actual_fingerprints),
        "matched_count": matched,
        "expected": expected_fingerprints,
        "actual": actual_fingerprints,
    }


def _sanitize_image_content_items(items: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    sanitized = []
    for item in items or []:
        clean = {key: value for key, value in item.items() if key != "content_b64"}
        if item.get("content_b64"):
            clean["byte_sha256"] = _sha256_b64(item["content_b64"])
            clean["fingerprint"] = _image_fingerprint_b64(item["content_b64"])
        sanitized.append(clean)
    return sanitized


def _probe_with_expected_images(probe: AssetProbe, expected_images: list[dict[str, Any]]) -> AssetProbe:
    current = dict(probe.current or {})
    actual_images = current.get("image_contents") or []
    images_match, summary = _image_expectations_match(expected_images, actual_images)
    current["image_contents"] = _sanitize_image_content_items(actual_images)
    current["expected_image_match"] = summary
    return AssetProbe(
        label=probe.label,
        identity_exists=probe.identity_exists,
        exact_match=probe.exact_match and images_match,
        current=current,
    )


def _run_elementx_sql(query: str) -> list[str]:
    cmd = (
        f"cd {ELEMENTX_PROJECT_DIR} && "
        f"docker compose --project-name {ELEMENTX_COMPOSE_PROJECT} exec -T db "
        "psql -U synapse -d synapse -At -F '\t' -c "
        + shlex.quote(query)
    )
    out = subprocess.check_output(["sh", "-lc", cmd], text=True)
    return [line for line in out.splitlines() if line.strip()]


def _elementx_admin_token() -> str:
    token = _fetch_existing_access_token("testuser")
    if token and _token_is_valid(token):
        return token
    token = _login("testuser", "testpass123")
    if token and _token_is_valid(token):
        return token
    raise RuntimeError("Could not obtain a read token for the default ElementX user")


def _elementx_get_json(path: str, *, token: str, expected: tuple[int, ...] = (200,)) -> dict[str, Any] | None:
    response = requests.get(
        f"{ELEMENTX_BASE_URL}{path}",
        headers={"Authorization": f"Bearer {token}"},
        timeout=30,
    )
    if response.status_code not in expected:
        raise RuntimeError(
            f"ElementX GET {path} failed: {response.status_code} {response.text}"
        )
    if response.status_code == 404:
        return None
    if not response.text:
        return {}
    return response.json()


def _elementx_room_reference(asset: ElementXRoomAsset | ElementXMessageAsset | ElementXPollAsset) -> str:
    if isinstance(asset, ElementXRoomAsset):
        if asset.alias_localpart:
            return elementx_room_alias(asset.alias_localpart)
        return elementx_room_alias(slugify_room_alias(asset.name))
    return asset.room


def _elementx_room_id(reference: str) -> str | None:
    try:
        return resolve_elementx_room_id(reference)
    except Exception:
        return None


def _elementx_room_members(room_id: str, token: str) -> list[str]:
    payload = _elementx_get_json(
        f"/_matrix/client/v3/rooms/{requests.utils.quote(room_id, safe='')}/joined_members",
        token=token,
        expected=(200,),
    )
    joined = payload.get("joined", {}) if payload else {}
    return sorted(joined.keys())


def _elementx_state(
    room_id: str,
    event_type: str,
    *,
    token: str,
    state_key: str = "",
    expected: tuple[int, ...] = (200, 404),
) -> dict[str, Any] | None:
    encoded_room = requests.utils.quote(room_id, safe="")
    encoded_type = requests.utils.quote(event_type, safe="")
    encoded_key = requests.utils.quote(state_key, safe="")
    return _elementx_get_json(
        f"/_matrix/client/v3/rooms/{encoded_room}/state/{encoded_type}/{encoded_key}",
        token=token,
        expected=expected,
    )


def _probe_contact(client, asset: ContactAsset, task: BaseTask | None) -> AssetProbe:
    result = _exec_json(
        client,
        f"""
import json
import sqlite3
import subprocess

device = {getattr(client, "device", "emulator-5554")!r}
target_phone = {_normalize_phone(asset.phone_number)!r}
target_name = {asset.name!r}
target_email = {asset.email!r}
target_website = {asset.website!r}
target_notes = {asset.notes!r}
target_label = {asset.label!r}
target_phone_label = {asset.phone_label!r}
target_email_label = {asset.email_label!r}
db_path = "/tmp/gma_contacts_eval.db"
for suffix in ("", "-wal", "-shm"):
    subprocess.run(["rm", "-f", db_path + suffix], check=False)
subprocess.run(["adb", "-s", device, "root"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
subprocess.run(
    ["adb", "-s", device, "pull", {CONTACTS_DB_PATH!r}, db_path],
    check=True,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
for suffix in ("-wal", "-shm"):
    subprocess.run(
        ["adb", "-s", device, "pull", {CONTACTS_DB_PATH!r} + suffix, db_path + suffix],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

def normalize_phone(value: str | None) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())

def text_equal(actual, expected):
    return ("" if actual is None else str(actual)).strip() == ("" if expected is None else str(expected)).strip()

PHONE_LABELS = {{
    0: "custom",
    1: "home",
    2: "mobile",
    3: "work",
    4: "work fax",
    5: "home fax",
    6: "pager",
    7: "other",
    8: "callback",
    9: "car",
    10: "company main",
    11: "isdn",
    12: "main",
    13: "other fax",
    14: "radio",
    15: "telex",
    16: "tty tdd",
    17: "work mobile",
    18: "work pager",
    19: "assistant",
    20: "mms",
}}
EMAIL_LABELS = {{
    0: "custom",
    1: "home",
    2: "work",
    3: "other",
    4: "mobile",
}}
def normalize_target_label(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip().lower()

def current_label(type_value, custom_value, labels: dict[int, str]) -> str | None:
    try:
        type_id = int(type_value or 0)
    except (TypeError, ValueError):
        type_id = 0
    custom = str(custom_value).strip().lower() if custom_value else None
    if type_id == 0 and custom:
        return custom
    return labels.get(type_id, custom)

target_phone_label = normalize_target_label(target_phone_label)
target_email_label = normalize_target_label(target_email_label)

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
rows = conn.execute(
    "select "
    "rc._id as raw_contact_id, "
    "max(case when m.mimetype = 'vnd.android.cursor.item/name' then d.data1 end) as name, "
    "max(case when m.mimetype = 'vnd.android.cursor.item/phone_v2' then d.data1 end) as phone, "
    "max(case when m.mimetype = 'vnd.android.cursor.item/phone_v2' then d.data2 end) as phone_type, "
    "max(case when m.mimetype = 'vnd.android.cursor.item/phone_v2' then d.data3 end) as phone_custom_label, "
    "max(case when m.mimetype = 'vnd.android.cursor.item/email_v2' then d.data1 end) as email, "
    "max(case when m.mimetype = 'vnd.android.cursor.item/email_v2' then d.data2 end) as email_type, "
    "max(case when m.mimetype = 'vnd.android.cursor.item/email_v2' then d.data3 end) as email_custom_label, "
    "max(case when m.mimetype = 'vnd.android.cursor.item/website' then d.data1 end) as website, "
    "max(case when m.mimetype = 'vnd.android.cursor.item/note' then d.data1 end) as notes "
    "from raw_contacts rc "
    "join data d on d.raw_contact_id = rc._id "
    "join mimetypes m on m._id = d.mimetype_id "
    "group by rc._id "
    "order by rc._id desc"
).fetchall()
current = None
for row in rows:
    phone = normalize_phone(row["phone"])
    if phone == target_phone:
        label_rows = conn.execute(
            "select groups.title from data "
            "join mimetypes on mimetypes._id = data.mimetype_id "
            "join groups on CAST(groups._id AS TEXT) = CAST(data.data1 AS TEXT) "
            "where data.raw_contact_id = ? and mimetypes.mimetype = 'vnd.android.cursor.item/group_membership' "
            "and groups.deleted = 0 order by groups.title",
            (row["raw_contact_id"],),
        ).fetchall()
        labels = [label_row["title"] for label_row in label_rows]
        current = {{
            "raw_contact_id": row["raw_contact_id"],
            "name": row["name"] or "",
            "phone_number": phone,
            "phone_label": current_label(row["phone_type"], row["phone_custom_label"], PHONE_LABELS),
            "email": row["email"] or None,
            "email_label": current_label(row["email_type"], row["email_custom_label"], EMAIL_LABELS) if row["email"] else None,
            "website": row["website"] or None,
            "notes": row["notes"] or None,
            "label": target_label if target_label in labels else (labels[0] if labels else None),
            "labels": labels,
        }}
        break

identity_exists = current is not None
exact_match = bool(
    current
    and (target_name is None or text_equal(current["name"], target_name))
    and current["phone_number"] == target_phone
    and (target_phone_label is None or current["phone_label"] == target_phone_label)
    and (target_email is None or current["email"] == target_email)
    and (target_email_label is None or current["email_label"] == target_email_label)
    and (target_website is None or text_equal(current["website"], target_website))
    and (target_notes is None or text_equal(current["notes"], target_notes))
    and (target_label is None or target_label in current["labels"])
)
print(json.dumps({{
    "identity_exists": identity_exists,
    "exact_match": exact_match,
    "current": current,
}}))
""",
    )
    return AssetProbe(
        label=f"contact:{asset.phone_number}",
        identity_exists=result["identity_exists"],
        exact_match=result["exact_match"],
        current=result["current"],
    )


def _probe_sms(client, asset: SmsMessageAsset, task: BaseTask | None) -> AssetProbe:
    result = _exec_json(
        client,
        f"""
import json
import sqlite3
import subprocess

device = {getattr(client, "device", "emulator-5554")!r}
target_address = {_normalize_phone(asset.address)!r}
target_body = {asset.body!r}
target_type = {SMS_TYPE_BY_BOX[asset.box]}
target_read = {1 if asset.read else 0}
target_timestamp = {asset.timestamp_ms!r}
db_path = "/tmp/gma_sms_eval.db"
for suffix in ("", "-wal", "-shm"):
    subprocess.run(["rm", "-f", db_path + suffix], check=False)
subprocess.run(["adb", "-s", device, "root"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
subprocess.run(
    ["adb", "-s", device, "pull", {SMS_DB_PATH!r}, db_path],
    check=True,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)
for suffix in ("-wal", "-shm"):
    subprocess.run(
        ["adb", "-s", device, "pull", {SMS_DB_PATH!r} + suffix, db_path + suffix],
        check=False,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

bugle_db_path = "/tmp/gma_bugle_sms_eval.db"
for suffix in ("", "-wal", "-shm"):
    subprocess.run(["rm", "-f", bugle_db_path + suffix], check=False)
bugle_base = "/data/user/0/com.google.android.apps.messaging/databases/bugle_db"
bugle_available = subprocess.run(
    ["adb", "-s", device, "pull", bugle_base, bugle_db_path],
    check=False,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
).returncode == 0
if bugle_available:
    for suffix in ("-wal", "-shm"):
        subprocess.run(
            ["adb", "-s", device, "pull", bugle_base + suffix, bugle_db_path + suffix],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

def normalize_phone(value: str | None) -> str:
    return "".join(ch for ch in (value or "") if ch.isdigit())

def text_equal(actual, expected):
    return ("" if actual is None else str(actual)).strip() == ("" if expected is None else str(expected)).strip()

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
rows = conn.execute(
    "select _id, address, body, date, read, type from sms order by date desc"
).fetchall()
current = None
for row in rows:
    address = normalize_phone(row["address"])
    if address == target_address and text_equal(row["body"], target_body) and int(row["type"] or 0) == target_type:
        current = {{
            "address": address,
            "body": row["body"] or "",
            "timestamp_ms": int(row["date"] or 0),
            "read": bool(row["read"]),
            "box": "sent" if int(row["type"] or 0) == 2 else "inbox",
        }}
        if current["box"] == "inbox" and bugle_available:
            try:
                bugle_conn = sqlite3.connect(bugle_db_path)
                bugle_conn.row_factory = sqlite3.Row
                cached = bugle_conn.execute(
                    "select read from messages where sms_message_uri = ? order by _id desc limit 1",
                    ("content://sms/" + str(row["_id"]),),
                ).fetchone()
                if cached is not None:
                    current["provider_read"] = current["read"]
                    current["messages_cache_read"] = bool(cached["read"])
                    current["read"] = bool(cached["read"])
            except sqlite3.Error:
                pass
        break

identity_exists = current is not None
exact_match = bool(
    current
    and current["read"] == bool(target_read)
    and (target_timestamp is None or abs(current["timestamp_ms"] - int(target_timestamp)) <= 1000)
)
print(json.dumps({{
    "identity_exists": identity_exists,
    "exact_match": exact_match,
    "current": current,
}}))
""",
    )
    return AssetProbe(
        label=f"sms:{asset.box}:{asset.address}:{asset.body}",
        identity_exists=result["identity_exists"],
        exact_match=result["exact_match"],
        current=result["current"],
    )


_CLOCK_MASK_TO_WEEKDAY = (
    (1, "monday"),
    (2, "tuesday"),
    (4, "wednesday"),
    (8, "thursday"),
    (16, "friday"),
    (32, "saturday"),
    (64, "sunday"),
)


def _clock_days_from_mask(mask: int) -> tuple[str, ...]:
    return tuple(day for bit, day in _CLOCK_MASK_TO_WEEKDAY if mask & bit)


def _probe_alarm(client, asset: AlarmAsset, task: BaseTask | None) -> AssetProbe:
    device = shlex.quote(getattr(client, "device", "emulator-5554"))
    expected_date = None
    if (
        asset.scheduled_year is not None
        and asset.scheduled_month is not None
        and asset.scheduled_day is not None
    ):
        expected_date = (
            int(asset.scheduled_year),
            int(asset.scheduled_month),
            int(asset.scheduled_day),
        )
    output = client.exec(
        f"""
adb -s {device} root >/dev/null 2>&1 || true
adb -s {device} shell <<'EOF'
sqlite3 {ALARMS_DB_PATH} <<'SQL'
select
  alarm_templates._id,
  alarm_templates.hour,
  alarm_templates.minutes,
  alarm_templates.label,
  alarm_templates.enabled,
  alarm_templates.daysofweek,
  alarm_templates.vibrate,
  alarm_instances.year,
  alarm_instances.month,
  alarm_instances.day,
  alarm_instances.hour,
  alarm_instances.minutes,
  alarm_instances.alarm_state
from alarm_templates
left join alarm_instances on alarm_instances.alarm_id = alarm_templates._id
order by alarm_templates._id desc;
SQL
EOF
""",
        timeout=30.0,
    )

    current = None
    for line in output.splitlines():
        parts = line.split("|")
        if len(parts) != 13:
            continue
        daysofweek = int(parts[5] or 0)
        scheduled_date = None
        if parts[7] and parts[8] and parts[9]:
            # DeskClock stores Calendar.MONTH as zero-based in alarm_instances.
            scheduled_date = (int(parts[7]), int(parts[8]) + 1, int(parts[9]))
        row = {
            "id": int(parts[0] or 0),
            "hour": int(parts[1] or 0),
            "minute": int(parts[2] or 0),
            "label": parts[3] or "",
            "enabled": bool(int(parts[4] or 0)),
            "days_of_week": _clock_days_from_mask(daysofweek),
            "vibrate": bool(int(parts[6] or 0)),
            "scheduled_date": scheduled_date,
            "scheduled_time": (
                int(parts[10]),
                int(parts[11]),
            ) if parts[10] and parts[11] else None,
            "alarm_state": int(parts[12]) if parts[12] else None,
        }
        if row["hour"] != asset.hour or row["minute"] != asset.minute:
            continue
        if asset.label is not None and not _text_equal(row["label"], asset.label):
            continue
        current = row
        break

    return AssetProbe(
        label=f"alarm:{asset.hour:02d}:{asset.minute:02d}",
        identity_exists=current is not None,
        exact_match=bool(
            current
            and _optional_text_equal(current["label"], asset.label)
            and current["enabled"] == bool(asset.enabled)
            and current["days_of_week"] == tuple(asset.days_of_week)
            and (asset.vibrate is None or current["vibrate"] == bool(asset.vibrate))
            and (expected_date is None or current["scheduled_date"] == expected_date)
            and (expected_date is None or current["scheduled_time"] == (asset.hour, asset.minute))
        ),
        current=current,
    )


def _probe_calendar_event(client, asset: CalendarEventAsset, task: BaseTask | None) -> AssetProbe:
    start_ts = _coerce_epoch_seconds(asset.start_ms)
    end_ts = _coerce_epoch_seconds(asset.end_ms)
    device = shlex.quote(getattr(client, "device", "emulator-5554"))
    sql = (
        "select rowid, title, start_ts, end_ts, location, description, time_zone, "
        "reminder_1_minutes, reminder_2_minutes, reminder_3_minutes, "
        "reminder_1_type, reminder_2_type, reminder_3_type "
        "from events where trim(title) = '"
        + asset.title.strip().replace("'", "''")
        + "' order by rowid desc;"
    )
    output = client.exec(
        f"""
adb -s {device} root >/dev/null 2>&1 || true
adb -s {device} shell <<'EOF'
sqlite3 {CALENDAR_DB_PATH} <<'SQL'
{sql}
SQL
EOF
""",
        timeout=30.0,
    )

    current = None
    for line in output.splitlines():
        parts = line.split("|")
        if len(parts) != 13:
            continue
        reminders = [int(value or -1) for value in parts[7:10]]
        reminder_types = [int(value or 0) for value in parts[10:13]]
        row = {
            "event_id": int(parts[0] or 0),
            "title": parts[1] or "",
            "start_ts": int(parts[2] or 0),
            "end_ts": int(parts[3] or 0),
            "location": parts[4] or None,
            "description": parts[5] or None,
            "timezone": parts[6] or None,
            "reminder_minutes": [minutes for minutes in reminders if minutes >= 0],
            "reminder_types": reminder_types,
        }
        if abs(int(row["start_ts"] or 0) - start_ts) > 600:
            continue
        if abs(int(row["end_ts"] or 0) - end_ts) > 600:
            continue
        current = row
        break

    return AssetProbe(
        label=f"calendar_event:{asset.title}",
        identity_exists=current is not None,
        exact_match=bool(
            current
            and _optional_text_equal(current["location"], asset.location)
            and _optional_text_equal(current["description"], asset.description)
            and (asset.timezone is None or current["timezone"] == asset.timezone)
            and (not asset.reminder_minutes or current["reminder_minutes"] == list(asset.reminder_minutes))
        ),
        current=current,
    )


def _probe_device_file(client, asset: DeviceFileAsset, task: BaseTask | None) -> AssetProbe:
    payload = _serialize_for_eval(asset, task=task)
    expected_hash = _sha256_b64(payload["content_b64"])
    remote_path = _device_file_path(asset)
    storage_dir = f"/sdcard/{asset.storage_dir}"
    result = _exec_json(
        client,
        f"""
import hashlib
import json
import shlex
import subprocess

remote_path = {remote_path!r}
storage_dir = {storage_dir!r}
match_filename = {asset.match_filename!r}
expected_hash = {expected_hash!r}

def file_hash(path: str):
    quoted = shlex.quote(path)
    try:
        raw = subprocess.check_output(
            ["sh", "-lc", f"adb -s emulator-5554 exec-out cat {{quoted}}"],
            stderr=subprocess.DEVNULL,
        )
    except subprocess.CalledProcessError:
        return None
    return {{"path": path, "size": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}}

current = None
candidates = []
if match_filename:
    current = file_hash(remote_path)
else:
    quoted_dir = shlex.quote(storage_dir)
    out = subprocess.check_output(
        ["sh", "-lc", f"adb -s emulator-5554 shell find {{quoted_dir}} -maxdepth 1 -type f 2>/dev/null || true"],
        text=True,
        stderr=subprocess.DEVNULL,
    )
    for raw_path in out.splitlines():
        path = raw_path.strip().replace(chr(13), "")
        if not path:
            continue
        item = file_hash(path)
        if item is None:
            continue
        candidates.append(item)
        if item["sha256"] == expected_hash:
            current = item
            break

print(json.dumps({{
    "identity_exists": current is not None,
    "exact_match": bool(current and current["sha256"] == expected_hash),
    "current": current,
    "candidates": candidates[:20],
}}))
""",
        timeout=120,
    )
    return AssetProbe(
        label=f"device_file:{remote_path}",
        identity_exists=result["identity_exists"],
        exact_match=result["exact_match"],
        current=result["current"] or {"candidates": result.get("candidates", [])},
    )


def _probe_elementx_user(client, asset: ElementXUserAsset, task: BaseTask | None) -> AssetProbe:
    result = _exec_json(
        client,
        f"""
import hashlib
import html
import json
import shlex
import subprocess
import time
import xml.etree.ElementTree as ET
import requests
from urllib.parse import quote

base = {ELEMENTX_BASE_URL!r}
server_name = {elementx_server_name()!r}
username = {asset.username!r}
display_name = {asset.display_name!r}

def sql_literal(value: str) -> str:
    return value.replace("'", "''")

def read_token(user: str) -> str:
    user_id = f"@{{user}}:{{server_name}}"
    cmd = (
        "cd /tmp/gma_elementx_export/WhatsApp/synapse-docker && "
        "docker compose --project-name gma-elementx exec -T db "
        "psql -U synapse -d synapse -At -c "
        + shlex.quote(
            "select token from access_tokens where user_id = '"
            + sql_literal(user_id)
            + "' order by id desc limit 1;"
        )
    )
    token = subprocess.check_output(["sh", "-lc", cmd], text=True).strip()
    if not token:
        raise RuntimeError(f"Could not read ElementX token for {{user}}")
    return token

token = read_token("testuser")
user_id = f"@{{username}}:{{server_name}}"
resp = requests.get(
    base + "/_matrix/client/v3/profile/" + quote(user_id, safe="") + "/displayname",
    headers={{"Authorization": "Bearer " + token}},
    timeout=30,
)
current = None
if resp.status_code == 200:
    payload = resp.json()
    current = {{
        "user_id": user_id,
        "username": username,
        "display_name": payload.get("displayname"),
    }}
elif resp.status_code != 404:
    resp.raise_for_status()
exact_match = bool(current and (display_name is None or current["display_name"] == display_name))
print(json.dumps({{
    "identity_exists": current is not None,
    "exact_match": exact_match,
    "current": current,
}}))
""",
    )
    return AssetProbe(
        label=f"elementx_user:{asset.username}",
        identity_exists=result["identity_exists"],
        exact_match=result["exact_match"],
        current=result["current"],
    )


def _probe_elementx_room(client, asset: ElementXRoomAsset, task: BaseTask | None) -> AssetProbe:
    room_reference = _elementx_room_reference(asset)
    fields_set = getattr(asset, "model_fields_set", set())
    check_members = (
        asset.room_type == "dm"
        or bool(asset.members)
        or "members" in fields_set
        or "creator_username" in fields_set
    )
    expected_members = (
        sorted({
            elementx_user_id(asset.creator_username),
            *(elementx_user_id(member) for member in asset.members),
        })
        if check_members
        else []
    )
    result = _exec_json(
        client,
        f"""
import hashlib
import html
import json
import shlex
import subprocess
import time
import xml.etree.ElementTree as ET
import requests
from urllib.parse import quote

base = {ELEMENTX_BASE_URL!r}
server_name = {elementx_server_name()!r}
room_reference = {room_reference!r}
room_name = {asset.name!r}
topic = {asset.topic!r}
room_type = {asset.room_type!r}
parent_space = {asset.parent_space!r}
expected_members = {expected_members!r}
check_members = {check_members!r}

def sql_literal(value: str) -> str:
    return value.replace("'", "''")

def read_token(user: str) -> str:
    user_id = f"@{{user}}:{{server_name}}"
    cmd = (
        "cd /tmp/gma_elementx_export/WhatsApp/synapse-docker && "
        "docker compose --project-name gma-elementx exec -T db "
        "psql -U synapse -d synapse -At -c "
        + shlex.quote(
            "select token from access_tokens where user_id = '"
            + sql_literal(user_id)
            + "' order by id desc limit 1;"
        )
    )
    token = subprocess.check_output(["sh", "-lc", cmd], text=True).strip()
    if not token:
        raise RuntimeError(f"Could not read ElementX token for {{user}}")
    return token

def resolve(reference: str, token: str) -> str | None:
    alias = reference
    if not alias.startswith("!") and not alias.startswith("#"):
        alias = f"#{{reference}}:{{server_name}}"
    if alias.startswith("#"):
        resp = requests.get(base + "/_matrix/client/v3/directory/room/" + quote(alias, safe=""), timeout=30)
        if resp.status_code == 200:
            return resp.json()["room_id"]
        if resp.status_code != 404:
            resp.raise_for_status()
    elif alias.startswith("!"):
        return alias

    joined = requests.get(
        base + "/_matrix/client/v3/joined_rooms",
        headers={{"Authorization": "Bearer " + token}},
        timeout=30,
    )
    joined.raise_for_status()
    for room_id in joined.json().get("joined_rooms", []):
        state = requests.get(
            base + f"/_matrix/client/v3/rooms/{{quote(room_id, safe='')}}/state/m.room.name",
            headers={{"Authorization": "Bearer " + token}},
            timeout=30,
        )
        if state.status_code == 200 and state.json().get("name") == room_name:
            return room_id
    return None

token = read_token("testuser")
joined_resp = requests.get(
    base + "/_matrix/client/v3/joined_rooms",
    headers={{"Authorization": "Bearer " + token}},
    timeout=30,
)
joined_resp.raise_for_status()
joined_room_ids = joined_resp.json().get("joined_rooms", [])

def room_state(room_id: str):
    def state_get(event_type: str, state_key: str = ""):
        resp = requests.get(
            base + f"/_matrix/client/v3/rooms/{{quote(room_id, safe='')}}/state/{{quote(event_type, safe='')}}/{{quote(state_key, safe='')}}",
            headers={{"Authorization": "Bearer " + token}},
            timeout=30,
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    members_resp = requests.get(
        base + f"/_matrix/client/v3/rooms/{{quote(room_id, safe='')}}/joined_members",
        headers={{"Authorization": "Bearer " + token}},
        timeout=30,
    )
    members_resp.raise_for_status()
    joined_members = sorted(members_resp.json().get("joined", {{}}).keys())

    def members_with_state(membership: str):
        resp = requests.get(
            base + f"/_matrix/client/v3/rooms/{{quote(room_id, safe='')}}/members",
            params={{"membership": membership}},
            headers={{"Authorization": "Bearer " + token}},
            timeout=30,
        )
        if resp.status_code == 404:
            return []
        resp.raise_for_status()
        result = []
        for event in resp.json().get("chunk", []):
            content = event.get("content") or {{}}
            if content.get("membership") == membership and event.get("state_key"):
                result.append(event["state_key"])
        return sorted(set(result))

    invited_members = members_with_state("invite")
    present_members = sorted(set(joined_members) | set(invited_members))
    parent_room_id = resolve(parent_space, token) if parent_space else None
    parent_state = state_get("m.space.parent", parent_room_id or "") if parent_room_id else None
    return {{
        "room_id": room_id,
        "name": (state_get("m.room.name") or {{}}).get("name"),
        "topic": (state_get("m.room.topic") or {{}}).get("topic"),
        "joined_members": joined_members,
        "invited_members": invited_members,
        "present_members": present_members,
        "create_type": (state_get("m.room.create") or {{}}).get("type"),
        "parent_space": parent_room_id if parent_state else None,
    }}

def text_equal(actual, expected):
    return ("" if actual is None else str(actual)).strip() == ("" if expected is None else str(expected)).strip()

current = None
if room_type == "dm":
    expected_member_set = set(expected_members)
    for candidate_room_id in joined_room_ids:
        candidate = room_state(candidate_room_id)
        if set(candidate["present_members"]) == expected_member_set:
            current = candidate
            break
else:
    room_id = resolve(room_reference, token)
    if room_id is not None:
        current = room_state(room_id)

exact_match = bool(
    current
    and (room_type == "dm" or text_equal(current["name"], room_name))
    and (topic is None or text_equal(current["topic"], topic))
    and (
        not check_members
        or (
            set(expected_members) == set(current["present_members"])
            if room_type == "dm"
            else set(expected_members).issubset(set(current["present_members"]))
        )
    )
    and (room_type != "space" or current["create_type"] == "m.space")
    and (parent_space is None or current["parent_space"] is not None)
)
print(json.dumps({{
    "identity_exists": current is not None,
    "exact_match": exact_match,
    "current": current,
}}))
""",
        timeout=180,
    )
    return AssetProbe(
        label=f"elementx_room:{room_reference}",
        identity_exists=result["identity_exists"],
        exact_match=result["exact_match"],
        current=result["current"],
    )


def _probe_elementx_message(client, asset: ElementXMessageAsset, task: BaseTask | None) -> AssetProbe:
    reply_to_sender = (
        elementx_user_id(asset.reply_to_sender_username)
        if asset.reply_to_sender_username
        else None
    )
    result = _exec_json(
        client,
        f"""
import html
import json
import re
import shlex
import subprocess
import time
import xml.etree.ElementTree as ET
import requests
from urllib.parse import quote

base = {ELEMENTX_BASE_URL!r}
server_name = {elementx_server_name()!r}
room_reference = {asset.room!r}
sender = {elementx_user_id(asset.sender_username)!r}
body = {asset.text!r}
reply_to_text = {asset.reply_to_text!r}
reply_to_sender = {reply_to_sender!r}
expected_pinned = {asset.pinned!r}
expected_created_at_ms = {asset.created_at_ms!r}
expected_mentions_room = {asset.mentions_room!r}

def sql_literal(value: str) -> str:
    return value.replace("'", "''")

def read_token(user: str) -> str:
    user_id = f"@{{user}}:{{server_name}}"
    cmd = (
        "cd /tmp/gma_elementx_export/WhatsApp/synapse-docker && "
        "docker compose --project-name gma-elementx exec -T db "
        "psql -U synapse -d synapse -At -c "
        + shlex.quote(
            "select token from access_tokens where user_id = '"
            + sql_literal(user_id)
            + "' order by id desc limit 1;"
        )
    )
    token = subprocess.check_output(["sh", "-lc", cmd], text=True).strip()
    if not token:
        raise RuntimeError(f"Could not read ElementX token for {{user}}")
    return token

def resolve_room(reference: str, token: str) -> str | None:
    if reference.startswith("@"):
        joined = requests.get(
            base + "/_matrix/client/v3/joined_rooms",
            headers={{"Authorization": "Bearer " + token}},
            timeout=30,
        )
        joined.raise_for_status()
        for room_id in joined.json().get("joined_rooms", []):
            state = requests.get(
                base + f"/_matrix/client/v3/rooms/{{quote(room_id, safe='')}}/state",
                headers={{"Authorization": "Bearer " + token}},
                timeout=30,
            )
            state.raise_for_status()
            present_members = sorted({{
                event.get("state_key")
                for event in state.json()
                if event.get("type") == "m.room.member"
                and event.get("state_key")
                and event.get("content", {{}}).get("membership") in ("join", "invite")
            }})
            if reference in present_members and sender in present_members and len(present_members) <= 2:
                return room_id
        return None
    alias = reference
    if not alias.startswith("!") and not alias.startswith("#"):
        alias = f"#{{reference}}:{{server_name}}"
    if alias.startswith("#"):
        resp = requests.get(base + "/_matrix/client/v3/directory/room/" + quote(alias, safe=""), timeout=30)
        if resp.status_code == 200:
            return resp.json()["room_id"]
        if resp.status_code != 404:
            resp.raise_for_status()
    elif alias.startswith("!"):
        return alias
    joined = requests.get(
        base + "/_matrix/client/v3/joined_rooms",
        headers={{"Authorization": "Bearer " + token}},
        timeout=30,
    )
    joined.raise_for_status()
    for room_id in joined.json().get("joined_rooms", []):
        state = requests.get(
            base + f"/_matrix/client/v3/rooms/{{quote(room_id, safe='')}}/state/m.room.name",
            headers={{"Authorization": "Bearer " + token}},
            timeout=30,
        )
        if state.status_code == 200 and state.json().get("name") == reference:
            return room_id
    return None

def run_sql_lines(sql: str) -> list[str]:
    cmd = (
        "cd /tmp/gma_elementx_export/WhatsApp/synapse-docker && "
        "docker compose --project-name gma-elementx exec -T db "
        "psql -U synapse -d synapse -At -F '\t' -c " + shlex.quote(sql)
    )
    return [line.strip() for line in subprocess.check_output(["sh", "-lc", cmd], text=True).splitlines() if line.strip()]

def normalize_matrix_mentions(value: str) -> str:
    return re.sub(
        r"\\[[^\\]]+\\]\\(https://matrix\\.to/#/(@[^:)]+)(?::[^)]+)?\\)",
        r"\\1",
        value,
    )

def reply_event_id(content: dict) -> str | None:
    return ((content.get("m.relates_to") or {{}}).get("m.in_reply_to") or {{}}).get("event_id")

def find_prompt_event_id(room_id: str) -> str | None:
    if reply_to_text is None:
        return None
    sender_clause = ""
    if reply_to_sender:
        sender_clause = " and ej.json::json->>'sender' = '" + sql_literal(reply_to_sender) + "'"
    rows = run_sql_lines(
        "select e.event_id from events e join event_json ej on e.event_id = ej.event_id "
        + "where e.room_id = '" + sql_literal(room_id) + "' "
        + "and e.type = 'm.room.message' "
        + sender_clause
        + " and ej.json::json->'content'->>'body' = '" + sql_literal(reply_to_text) + "' "
        + "order by e.stream_ordering desc limit 1"
    )
    return rows[0] if rows else None

def room_name(room_id: str) -> str | None:
    state = requests.get(
        base + f"/_matrix/client/v3/rooms/{{quote(room_id, safe='')}}/state/m.room.name",
        headers={{"Authorization": "Bearer " + token}},
        timeout=30,
    )
    if state.status_code == 200:
        return state.json().get("name")
    if state.status_code != 404:
        state.raise_for_status()
    return None

def pinned_event_ids(room_id: str) -> set[str]:
    state = requests.get(
        base + f"/_matrix/client/v3/rooms/{{quote(room_id, safe='')}}/state/m.room.pinned_events",
        headers={{"Authorization": "Bearer " + token}},
        timeout=30,
    )
    if state.status_code == 200:
        return set(state.json().get("pinned", []))
    if state.status_code == 404:
        return set()
    state.raise_for_status()
    return set()

def visible_elementx_texts() -> list[str]:
    subprocess.run(
        ["sh", "-lc", "adb -s emulator-5554 shell uiautomator dump /sdcard/elementx_eval.xml >/dev/null 2>&1"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    try:
        xml = subprocess.check_output(
            ["sh", "-lc", "adb -s emulator-5554 shell cat /sdcard/elementx_eval.xml"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return []
    texts = []
    try:
        root = ET.fromstring(xml)
        for node in root.iter("node"):
            for attr in ("text", "content-desc"):
                value = html.unescape(node.attrib.get(attr, "")).strip()
                if value:
                    texts.append(value)
    except Exception:
        texts = [html.unescape(xml)]
    return texts

def open_elementx_room(room_id: str) -> bool:
    url = "element://room/" + quote(room_id, safe="")
    cmd = (
        "adb -s emulator-5554 shell am start -a android.intent.action.VIEW -d "
        + shlex.quote(url)
        + " io.element.android.x >/dev/null 2>&1"
    )
    try:
        subprocess.run(
            ["sh", "-lc", cmd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
        )
    except Exception:
        return False
    return True

def relation_matches(content: dict, prompt_event_id: str | None) -> bool:
    if reply_to_text is None:
        return True
    return prompt_event_id is not None and reply_event_id(content) == prompt_event_id

def pin_matches(event_id: str, pinned_ids: set[str]) -> bool:
    if expected_pinned is None:
        return True
    return (event_id in pinned_ids) == expected_pinned

def room_mention_matches(content: dict) -> bool:
    if expected_mentions_room is None:
        return True
    return bool((content.get("m.mentions") or {{}}).get("room")) == bool(expected_mentions_room)

token = read_token("testuser")
room_id = resolve_room(room_reference, token)
current = None
exact_match = False
identity_exists = False
if room_id:
    prompt_event_id = find_prompt_event_id(room_id) if reply_to_text is not None else None
    pinned_ids = pinned_event_ids(room_id)
    plaintext_identity_count = 0
    plaintext_count = 0
    normalized_plaintext_count = 0
    normalized_plaintext_body = None
    normalized_identity_count = 0
    matching_event_ids = []
    matching_pinned_event_ids = []
    matching_unpinned_event_ids = []
    room_mention_mismatch_event_ids = []
    body_rows = run_sql_lines(
        "select e.event_id, e.origin_server_ts, ej.json from events e join event_json ej on e.event_id = ej.event_id "
        + "where e.room_id = '" + sql_literal(room_id) + "' "
        + "and e.type = 'm.room.message' "
        + "and ej.json::json->>'sender' = '" + sql_literal(sender) + "' "
        + "order by e.stream_ordering"
    )
    for candidate_raw in body_rows:
        parts = candidate_raw.split(chr(9), 2)
        if len(parts) != 3:
            continue
        event_id, origin_server_ts_raw, payload = parts
        origin_server_ts = int(origin_server_ts_raw or 0)
        event = json.loads(payload)
        content = event.get("content") or {{}}
        candidate = content.get("body") or ""
        is_exact_body = candidate == body
        is_normalized_body = normalize_matrix_mentions(candidate).strip() == body.strip()
        if is_exact_body:
            plaintext_identity_count += 1
        elif is_normalized_body:
            normalized_identity_count += 1
        else:
            continue
        if not relation_matches(content, prompt_event_id):
            continue
        if expected_created_at_ms is not None and abs(origin_server_ts - int(expected_created_at_ms)) > 1000:
            continue
        if not room_mention_matches(content):
            room_mention_mismatch_event_ids.append(event_id)
            continue
        matching_event_ids.append(event_id)
        if event_id in pinned_ids:
            matching_pinned_event_ids.append(event_id)
        else:
            matching_unpinned_event_ids.append(event_id)
        if not pin_matches(event_id, pinned_ids):
            continue
        if is_exact_body:
            plaintext_count += 1
        else:
            normalized_plaintext_count += 1
            normalized_plaintext_body = candidate
    encrypted_sql = (
        "select count(*) from event_json "
        + "where room_id = '" + sql_literal(room_id) + "' "
        + "and json::json->>'type' = 'm.room.encrypted' "
        + "and json::json->>'sender' = '" + sql_literal(sender) + "'"
    )
    encrypted_rows = run_sql_lines(encrypted_sql)
    encrypted_count = int(encrypted_rows[0]) if encrypted_rows else 0
    expected_room_name = room_name(room_id)
    can_use_encrypted_ui = reply_to_text is None and expected_pinned is None
    should_check_encrypted_ui = plaintext_count == 0 and normalized_plaintext_count == 0 and encrypted_count > 0 and can_use_encrypted_ui
    ui_opened_room = False
    ui_texts = visible_elementx_texts() if should_check_encrypted_ui else []
    ui_body_visible = any(text.strip() == body.strip() for text in ui_texts)
    ui_room_visible = expected_room_name is None or any(text.strip() == expected_room_name.strip() for text in ui_texts)
    if should_check_encrypted_ui and not (ui_body_visible and ui_room_visible):
        ui_opened_room = open_elementx_room(room_id)
        if ui_opened_room:
            time.sleep(3)
            ui_texts = visible_elementx_texts()
            ui_body_visible = any(text.strip() == body.strip() for text in ui_texts)
            ui_room_visible = expected_room_name is None or any(text.strip() == expected_room_name.strip() for text in ui_texts)
    identity_exists = plaintext_identity_count > 0 or normalized_identity_count > 0 or (encrypted_count > 0 and can_use_encrypted_ui)
    exact_match = plaintext_count > 0 or normalized_plaintext_count > 0 or (encrypted_count > 0 and can_use_encrypted_ui and ui_body_visible and ui_room_visible)
    current = {{
        "room_id": room_id,
        "room_name": expected_room_name,
        "sender": sender,
        "body": body,
        "count": plaintext_count,
        "identity_count": plaintext_identity_count,
        "normalized_count": normalized_plaintext_count,
        "normalized_identity_count": normalized_identity_count,
        "normalized_body": normalized_plaintext_body,
        "reply_to_text": reply_to_text,
        "reply_to_sender": reply_to_sender,
        "reply_to_event_id": prompt_event_id,
        "expected_pinned": expected_pinned,
        "pinned_event_ids": sorted(pinned_ids),
        "matching_event_ids": matching_event_ids,
        "matching_pinned_event_ids": matching_pinned_event_ids,
        "matching_unpinned_event_ids": matching_unpinned_event_ids,
        "expected_mentions_room": expected_mentions_room,
        "room_mention_mismatch_event_ids": room_mention_mismatch_event_ids,
        "expected_created_at_ms": expected_created_at_ms,
        "encrypted_count": encrypted_count,
        "ui_opened_room": ui_opened_room,
        "ui_body_visible": ui_body_visible,
        "ui_room_visible": ui_room_visible,
        "ui_texts_sample": ui_texts[:20],
    }}

print(json.dumps({{
    "identity_exists": identity_exists,
    "exact_match": exact_match,
    "current": current,
}}))
""",
        timeout=180,
    )
    return AssetProbe(
        label=f"elementx_message:{asset.room}:{asset.sender_username}",
        identity_exists=result["identity_exists"],
        exact_match=result["exact_match"],
        current=result["current"],
    )


def _probe_elementx_file(client, asset: ElementXFileAsset, task: BaseTask | None) -> AssetProbe:
    payload_asset = _serialize_for_eval(asset, task=task)
    expected_sha256 = _sha256_b64(payload_asset["content_b64"])
    expected_size = len(base64.b64decode(payload_asset["content_b64"]))
    result = _exec_json(
        client,
        f"""
import hashlib
import html
import json
import re
import shlex
import subprocess
import time
import xml.etree.ElementTree as ET
import requests
from urllib.parse import quote

base = {ELEMENTX_BASE_URL!r}
server_name = {elementx_server_name()!r}
room_reference = {asset.room!r}
sender_username = {asset.sender_username!r}
sender_password = {asset.sender_password!r}
sender = {elementx_user_id(asset.sender_username)!r}
filename = {asset.filename!r}
expected_mime = {asset.mime_type!r}
expected_sha256 = {expected_sha256!r}
expected_size = {expected_size!r}
expected_pinned = {asset.pinned!r}
expected_created_at_ms = {asset.created_at_ms!r}

def sql_literal(value: str) -> str:
    return value.replace("'", "''")

def slugify_room_alias(name: str) -> str:
    normalized = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-") or "room"
    digest = hashlib.sha1(name.encode("utf-8")).hexdigest()[:8]
    return f"gma-{{normalized[:40]}}-{{digest}}"

def login(username: str, password: str) -> str:
    response = requests.post(
        base + "/_matrix/client/v3/login",
        json={{
            "type": "m.login.password",
            "identifier": {{"type": "m.id.user", "user": username}},
            "password": password,
        }},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()["access_token"]

def resolve_room(reference: str, token: str) -> str | None:
    if reference.startswith("@"):
        joined = requests.get(
            base + "/_matrix/client/v3/joined_rooms",
            headers={{"Authorization": "Bearer " + token}},
            timeout=30,
        )
        joined.raise_for_status()
        for room_id in joined.json().get("joined_rooms", []):
            state = requests.get(
                base + f"/_matrix/client/v3/rooms/{{quote(room_id, safe='')}}/state",
                headers={{"Authorization": "Bearer " + token}},
                timeout=30,
            )
            state.raise_for_status()
            present_members = sorted({{
                event.get("state_key")
                for event in state.json()
                if event.get("type") == "m.room.member"
                and event.get("state_key")
                and event.get("content", {{}}).get("membership") in ("join", "invite")
            }})
            if reference in present_members and sender in present_members and len(present_members) <= 2:
                return room_id
        return None
    if reference.startswith("!"):
        return reference
    aliases = []
    if reference.startswith("#"):
        aliases.append(reference)
    else:
        aliases.append(f"#{{reference}}:{{server_name}}")
        generated = f"#{{slugify_room_alias(reference)}}:{{server_name}}"
        if generated not in aliases:
            aliases.append(generated)
    for alias in aliases:
        response = requests.get(
            base + "/_matrix/client/v3/directory/room/" + quote(alias, safe=""),
            timeout=30,
        )
        if response.status_code == 200:
            return response.json()["room_id"]
        if response.status_code != 404:
            response.raise_for_status()
    joined = requests.get(
        base + "/_matrix/client/v3/joined_rooms",
        headers={{"Authorization": "Bearer " + token}},
        timeout=30,
    )
    joined.raise_for_status()
    for room_id in joined.json().get("joined_rooms", []):
        state = requests.get(
            base + f"/_matrix/client/v3/rooms/{{quote(room_id, safe='')}}/state/m.room.name",
            headers={{"Authorization": "Bearer " + token}},
            timeout=30,
        )
        if state.status_code == 200 and state.json().get("name") == reference:
            return room_id
    return None

def run_sql_lines(sql: str) -> list[str]:
    cmd = (
        "cd /tmp/gma_elementx_export/WhatsApp/synapse-docker && "
        "docker compose --project-name gma-elementx exec -T db "
        "psql -U synapse -d synapse -At -F '\\t' -c " + shlex.quote(sql)
    )
    return [line.strip() for line in subprocess.check_output(["sh", "-lc", cmd], text=True).splitlines() if line.strip()]

def pinned_event_ids(room_id: str, token: str) -> set[str]:
    state = requests.get(
        base + f"/_matrix/client/v3/rooms/{{quote(room_id, safe='')}}/state/m.room.pinned_events",
        headers={{"Authorization": "Bearer " + token}},
        timeout=30,
    )
    if state.status_code == 200:
        return set(state.json().get("pinned", []))
    if state.status_code == 404:
        return set()
    state.raise_for_status()
    return set()

def room_name(room_id: str, token: str) -> str | None:
    state = requests.get(
        base + f"/_matrix/client/v3/rooms/{{quote(room_id, safe='')}}/state/m.room.name",
        headers={{"Authorization": "Bearer " + token}},
        timeout=30,
    )
    if state.status_code == 200:
        return state.json().get("name")
    if state.status_code != 404:
        state.raise_for_status()
    return None

def visible_elementx_texts() -> list[str]:
    subprocess.run(
        ["sh", "-lc", "adb -s emulator-5554 shell uiautomator dump /sdcard/elementx_file_eval.xml >/dev/null 2>&1"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    try:
        xml = subprocess.check_output(
            ["sh", "-lc", "adb -s emulator-5554 shell cat /sdcard/elementx_file_eval.xml"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return []
    texts = []
    try:
        root = ET.fromstring(xml)
        for node in root.iter("node"):
            for attr in ("text", "content-desc"):
                value = html.unescape(node.attrib.get(attr, "")).strip()
                if value:
                    texts.append(value)
    except Exception:
        texts = [html.unescape(xml)]
    return texts

def open_elementx_room(room_id: str) -> bool:
    url = "element://room/" + quote(room_id, safe="")
    cmd = (
        "adb -s emulator-5554 shell am start -a android.intent.action.VIEW -d "
        + shlex.quote(url)
        + " io.element.android.x >/dev/null 2>&1"
    )
    try:
        subprocess.run(
            ["sh", "-lc", cmd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
        )
    except Exception:
        return False
    return True

def scan_elementx_room_for_file(room_id: str, expected_room_name: str | None, filename: str, max_swipes: int = 6):
    opened = open_elementx_room(room_id)
    if opened:
        time.sleep(3)
    all_texts = []
    seen_snapshots = set()
    filename_visible = False
    room_visible = False
    filename_pinned_visible = False

    def absorb_current():
        nonlocal filename_visible, room_visible, filename_pinned_visible
        texts = visible_elementx_texts()
        snapshot = "\\n".join(texts)
        if snapshot not in seen_snapshots:
            seen_snapshots.add(snapshot)
            for text in texts:
                if text not in all_texts:
                    all_texts.append(text)
        current_filename_visible = any(filename == text.strip() or filename in text for text in texts)
        current_room_visible = expected_room_name is None or any(text.strip() == expected_room_name.strip() for text in texts)
        current_pinned_visible = any(text.strip() == "Pinned" for text in texts)
        filename_visible = filename_visible or current_filename_visible
        room_visible = room_visible or current_room_visible
        filename_pinned_visible = filename_pinned_visible or (current_filename_visible and current_pinned_visible)
        return current_filename_visible, current_room_visible, current_pinned_visible

    for index in range(max_swipes + 1):
        current_filename_visible, current_room_visible, current_pinned_visible = absorb_current()
        if current_filename_visible and current_room_visible and (expected_pinned is not True or current_pinned_visible):
            break
        if index == max_swipes:
            break
        subprocess.run(
            ["sh", "-lc", "adb -s emulator-5554 shell input swipe 540 850 540 1700 350"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
        time.sleep(0.8)
    return all_texts, opened, filename_visible, room_visible, filename_pinned_visible

def pin_matches(event_id: str, pinned_ids: set[str]) -> bool:
    if expected_pinned is None:
        return True
    return (event_id in pinned_ids) == expected_pinned

def mime_matches(actual: str | None) -> bool:
    if expected_mime is None:
        return True
    aliases = {{
        "audio/x-wav": "audio/wav",
        "audio/wave": "audio/wav",
        "audio/vnd.wave": "audio/wav",
    }}
    expected = aliases.get(expected_mime.split(";", 1)[0].lower(), expected_mime.split(";", 1)[0].lower())
    observed = (actual or "").split(";", 1)[0].lower()
    observed = aliases.get(observed, observed)
    return observed == expected

def msgtype_matches(actual: str | None) -> bool:
    if actual == "m.file":
        return True
    if actual == "m.audio" and (expected_mime or "").split(";", 1)[0].lower().startswith("audio/"):
        return True
    return False

def media_sha256(content_uri: str | None, token: str) -> str | None:
    if not content_uri or not content_uri.startswith("mxc://"):
        return None
    rest = content_uri[len("mxc://"):]
    if "/" not in rest:
        return None
    server, media_id = rest.split("/", 1)
    headers = {{"Authorization": "Bearer " + token}}
    paths = (
        f"/_matrix/media/v3/download/{{quote(server, safe='')}}/{{quote(media_id, safe='')}}",
        f"/_matrix/media/r0/download/{{quote(server, safe='')}}/{{quote(media_id, safe='')}}",
    )
    for path in paths:
        response = requests.get(base + path, headers=headers, timeout=30)
        if response.status_code == 200:
            return hashlib.sha256(response.content).hexdigest()
        if response.status_code != 404:
            response.raise_for_status()
    return None

token = login(sender_username, sender_password)
room_id = resolve_room(room_reference, token)
current = None
identity_exists = False
exact_match = False
if room_id:
    pinned_ids = pinned_event_ids(room_id, token)
    candidates = []
    encrypted_event_ids = []
    encrypted_pinned_event_ids = []
    expected_room_name = room_name(room_id, token)
    ui_opened_room = False
    ui_texts = []
    ui_filename_visible = False
    ui_room_visible = False
    ui_pinned_visible = False
    encrypted_ui_match = False
    rows = run_sql_lines(
        "select e.event_id, e.origin_server_ts, ej.json from events e join event_json ej on e.event_id = ej.event_id "
        + "where e.room_id = '" + sql_literal(room_id) + "' "
        + "and e.type = 'm.room.message' "
        + "and ej.json::json->>'sender' = '" + sql_literal(sender) + "' "
        + "order by e.stream_ordering"
    )
    for row in rows:
        parts = row.split(chr(9), 2)
        if len(parts) != 3:
            continue
        event_id, origin_server_ts_raw, payload = parts
        origin_server_ts = int(origin_server_ts_raw or 0)
        event = json.loads(payload)
        content = event.get("content") or {{}}
        info = content.get("info") or {{}}
        if not msgtype_matches(content.get("msgtype")):
            continue
        if content.get("body") != filename and content.get("filename") != filename:
            continue
        sha256 = media_sha256(content.get("url"), token)
        item = {{
            "event_id": event_id,
            "origin_server_ts": origin_server_ts,
            "sender": event.get("sender"),
            "body": content.get("body"),
            "filename": content.get("filename"),
            "msgtype": content.get("msgtype"),
            "mime_type": info.get("mimetype"),
            "size": info.get("size"),
            "sha256": sha256,
            "is_pinned": event_id in pinned_ids,
        }}
        candidates.append(item)
        identity_exists = True
        if expected_created_at_ms is not None and abs(origin_server_ts - int(expected_created_at_ms)) > 1000:
            continue
        if not mime_matches(info.get("mimetype")):
            continue
        if info.get("size") not in (None, expected_size):
            continue
        if sha256 is not None and sha256 != expected_sha256:
            continue
        if not pin_matches(event_id, pinned_ids):
            continue
        exact_match = True
    encrypted_event_ids = run_sql_lines(
        "select e.event_id from events e join event_json ej on e.event_id = ej.event_id "
        + "where e.room_id = '" + sql_literal(room_id) + "' "
        + "and e.type = 'm.room.encrypted' "
        + "and ej.json::json->>'sender' = '" + sql_literal(sender) + "' "
        + "order by e.stream_ordering"
    )
    encrypted_pinned_event_ids = sorted(set(encrypted_event_ids).intersection(pinned_ids))
    should_check_encrypted_ui = (
        not exact_match
        and expected_created_at_ms is None
        and bool(encrypted_event_ids)
    )
    if should_check_encrypted_ui:
        ui_texts, ui_opened_room, ui_filename_visible, ui_room_visible, ui_pinned_visible = scan_elementx_room_for_file(
            room_id,
            expected_room_name,
            filename,
        )
        encrypted_pin_match = True
        if expected_pinned is True:
            encrypted_pin_match = bool(encrypted_pinned_event_ids) and ui_pinned_visible
        elif expected_pinned is False:
            encrypted_pin_match = not encrypted_pinned_event_ids and not ui_pinned_visible
        encrypted_ui_match = ui_filename_visible and ui_room_visible and encrypted_pin_match
        identity_exists = identity_exists or ui_filename_visible
        exact_match = exact_match or encrypted_ui_match
    current = {{
        "room_id": room_id,
        "room_name": expected_room_name,
        "sender": sender,
        "filename": filename,
        "expected_mime_type": expected_mime,
        "expected_sha256": expected_sha256,
        "expected_size": expected_size,
        "expected_pinned": expected_pinned,
        "pinned_event_ids": sorted(pinned_ids),
        "candidates": candidates,
        "encrypted_count": len(encrypted_event_ids),
        "encrypted_pinned_event_ids": encrypted_pinned_event_ids,
        "encrypted_ui_match": encrypted_ui_match,
        "ui_opened_room": ui_opened_room,
        "ui_filename_visible": ui_filename_visible,
        "ui_room_visible": ui_room_visible,
        "ui_pinned_visible": ui_pinned_visible,
        "ui_texts_sample": ui_texts[:20],
    }}

print(json.dumps({{
    "identity_exists": identity_exists,
    "exact_match": exact_match,
    "current": current,
}}))
""",
        timeout=180,
    )
    return AssetProbe(
        label=f"elementx_file:{asset.room}:{asset.sender_username}:{asset.filename}",
        identity_exists=result["identity_exists"],
        exact_match=result["exact_match"],
        current=result["current"],
    )


def _probe_elementx_poll(client, asset: ElementXPollAsset, task: BaseTask | None) -> AssetProbe:
    expected_responses = sorted({
        "username": elementx_user_id(response.username),
        "option": response.option,
        "created_at_ms": response.created_at_ms,
    } for response in asset.responses)
    result = _exec_json(
        client,
        f"""
import hashlib
import html
import json
import shlex
import subprocess
import time
import xml.etree.ElementTree as ET
import requests
from urllib.parse import quote

base = {ELEMENTX_BASE_URL!r}
server_name = {elementx_server_name()!r}
room_reference = {asset.room!r}
sender = {elementx_user_id(asset.sender_username)!r}
question = {asset.question!r}
options = {asset.options!r}
expected_responses = {expected_responses!r}
expected_created_at_ms = {asset.created_at_ms!r}

def sql_literal(value: str) -> str:
    return value.replace("'", "''")

def read_token(user: str) -> str:
    user_id = f"@{{user}}:{{server_name}}"
    cmd = (
        "cd /tmp/gma_elementx_export/WhatsApp/synapse-docker && "
        "docker compose --project-name gma-elementx exec -T db "
        "psql -U synapse -d synapse -At -c "
        + shlex.quote(
            "select token from access_tokens where user_id = '"
            + sql_literal(user_id)
            + "' order by id desc limit 1;"
        )
    )
    token = subprocess.check_output(["sh", "-lc", cmd], text=True).strip()
    if not token:
        raise RuntimeError(f"Could not read ElementX token for {{user}}")
    return token

def resolve_room(reference: str, token: str) -> str | None:
    alias = reference
    if not alias.startswith("!") and not alias.startswith("#"):
        alias = f"#{{reference}}:{{server_name}}"
    if alias.startswith("#"):
        resp = requests.get(base + "/_matrix/client/v3/directory/room/" + quote(alias, safe=""), timeout=30)
        if resp.status_code == 200:
            return resp.json()["room_id"]
        if resp.status_code != 404:
            resp.raise_for_status()
    elif alias.startswith("!"):
        return alias
    joined = requests.get(
        base + "/_matrix/client/v3/joined_rooms",
        headers={{"Authorization": "Bearer " + token}},
        timeout=30,
    )
    joined.raise_for_status()
    for room_id in joined.json().get("joined_rooms", []):
        state = requests.get(
            base + f"/_matrix/client/v3/rooms/{{quote(room_id, safe='')}}/state/m.room.name",
            headers={{"Authorization": "Bearer " + token}},
            timeout=30,
        )
        if state.status_code == 200 and state.json().get("name") == reference:
            return room_id
    return None

def run_sql_lines(sql: str) -> list[str]:
    cmd = (
        "cd /tmp/gma_elementx_export/WhatsApp/synapse-docker && "
        "docker compose --project-name gma-elementx exec -T db "
        "psql -U synapse -d synapse -At -F '\\t' -c " + shlex.quote(sql)
    )
    return [line for line in subprocess.check_output(["sh", "-lc", cmd], text=True).splitlines() if line.strip()]

def visible_elementx_texts() -> list[str]:
    subprocess.run(
        ["sh", "-lc", "adb -s emulator-5554 shell uiautomator dump /sdcard/elementx_poll_eval.xml >/dev/null 2>&1"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        check=False,
    )
    try:
        xml = subprocess.check_output(
            ["sh", "-lc", "adb -s emulator-5554 shell cat /sdcard/elementx_poll_eval.xml"],
            text=True,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        return []
    texts = []
    try:
        root = ET.fromstring(xml)
        for node in root.iter("node"):
            for attr in ("text", "content-desc"):
                value = html.unescape(node.attrib.get(attr, "")).strip()
                if value:
                    texts.append(value)
    except Exception:
        texts = [html.unescape(xml)]
    return texts

def open_elementx_room(room_id: str) -> bool:
    url = "element://room/" + quote(room_id, safe="")
    cmd = (
        "adb -s emulator-5554 shell am start -a android.intent.action.VIEW -d "
        + shlex.quote(url)
        + " io.element.android.x >/dev/null 2>&1"
    )
    try:
        subprocess.run(
            ["sh", "-lc", cmd],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False,
        )
    except Exception:
        return False
    return True

def ui_option_visible(texts: list[str], option: str) -> bool:
    expected = option.strip()
    return any(
        text.strip() == expected
        or text.strip().startswith(expected + ".")
        or text.strip().startswith(expected + " ")
        for text in texts
    )

token = read_token("testuser")
room_id = resolve_room(room_reference, token)
current = None
if room_id:
    rows = run_sql_lines(
        "select e.event_id, e.stream_ordering, e.origin_server_ts, ej.json "
        + "from events e join event_json ej on e.event_id = ej.event_id "
        + "where e.room_id = '" + sql_literal(room_id) + "' "
        + "and e.type in ('org.matrix.msc3381.poll.start','org.matrix.msc3381.poll.response','m.poll.start','m.poll.response') "
        + "order by e.stream_ordering"
    )
    encrypted_rows = run_sql_lines(
        "select count(*) from event_json "
        + "where room_id = '" + sql_literal(room_id) + "' "
        + "and json::json->>'type' = 'm.room.encrypted' "
        + "and json::json->>'sender' = '" + sql_literal(sender) + "'"
    )
    encrypted_count = int(encrypted_rows[0]) if encrypted_rows else 0
    poll_event = None
    option_map = {{}}
    poll_candidates = []
    for raw in rows:
        row_event_id, stream_ordering_raw, origin_server_ts_raw, payload = raw.split("\\t", 3)
        origin_server_ts = int(origin_server_ts_raw or 0)
        event = json.loads(payload)
        if event.get("type") not in {{"org.matrix.msc3381.poll.start", "m.poll.start"}} or event.get("sender") != sender:
            continue
        raw_content = event.get("content", {{}})
        poll_start = raw_content.get("m.poll.start", raw_content.get("org.matrix.msc3381.poll.start", raw_content))
        question_content = poll_start.get("question", {{}})
        event_question = (
            question_content.get("m.text")
            or question_content.get("org.matrix.msc1767.text")
            or raw_content.get("m.text", "").split("\\n", 1)[0]
            or raw_content.get("org.matrix.msc1767.text", "").split("\\n", 1)[0]
        )
        if event_question.strip() != question.strip():
            continue
        candidate_option_map = {{
            item.get("m.text") or item.get("org.matrix.msc1767.text"): item.get("id")
            for item in poll_start.get("answers", [])
        }}
        poll_candidates.append({{
            "event_id": row_event_id,
            "sender": sender,
            "question": event_question,
            "created_at_ms": origin_server_ts,
            "options": [
                item.get("m.text") or item.get("org.matrix.msc1767.text")
                for item in poll_start.get("answers", [])
            ],
            "option_map": candidate_option_map,
        }})

    def text_list(values):
        return [("" if value is None else str(value)).strip() for value in (values or [])]

    def poll_candidate_matches(candidate: dict) -> bool:
        return (
            text_list(candidate["options"]) == text_list(options)
            and (
                expected_created_at_ms is None
                or abs(int(candidate.get("created_at_ms") or 0) - int(expected_created_at_ms)) <= 1000
            )
        )

    if poll_candidates:
        poll_event = next((item for item in poll_candidates if poll_candidate_matches(item)), None)
        if poll_event is None:
            poll_event = next((item for item in poll_candidates if text_list(item["options"]) == text_list(options)), poll_candidates[0])
        option_map = poll_event.pop("option_map", {{}})

    response_history = []
    latest_response_by_user = {{}}
    if poll_event is not None:
        for raw in rows:
            row_event_id, stream_ordering_raw, origin_server_ts_raw, payload = raw.split("\\t", 3)
            stream_ordering = int(stream_ordering_raw or 0)
            origin_server_ts = int(origin_server_ts_raw or 0)
            event = json.loads(payload)
            if event.get("type") not in {{"org.matrix.msc3381.poll.response", "m.poll.response"}}:
                continue
            content = event.get("content", {{}})
            relates = content.get("m.relates_to", {{}})
            if relates.get("event_id") != poll_event["event_id"]:
                continue
            answers = (
                content.get("m.poll.response", {{}}).get("answers")
                or content.get("org.matrix.msc3381.poll.response", {{}}).get("answers")
                or content.get("org.matrix.msc3381.answers", [])
            )
            matched_options = sorted(name for name, option_id in option_map.items() if option_id in answers)
            response_event = {{
                "username": event.get("sender"),
                "options": matched_options,
                "event_id": row_event_id,
                "stream_ordering": stream_ordering,
                "created_at_ms": origin_server_ts,
            }}
            response_history.append(response_event)
            previous = latest_response_by_user.get(event.get("sender"))
            if previous is None or stream_ordering > previous["stream_ordering"]:
                latest_response_by_user[event.get("sender")] = response_event

    responses = []
    for response_event in latest_response_by_user.values():
        for option in response_event["options"]:
            responses.append({{"username": response_event["username"], "option": option, "created_at_ms": response_event["created_at_ms"]}})

    current = {{
        "room_id": room_id,
        "poll": poll_event,
        "responses": sorted(responses, key=lambda item: (item["username"], item["option"])),
        "response_history": sorted(response_history, key=lambda item: item["stream_ordering"]),
        "encrypted_count": encrypted_count,
    }}
    if poll_event is None and encrypted_count > 0 and not expected_responses:
        ui_opened_room = False
        ui_texts = visible_elementx_texts()
        ui_question_visible = any(text.strip() == question.strip() for text in ui_texts)
        ui_options_visible = all(ui_option_visible(ui_texts, option) for option in options)
        if not (ui_question_visible and ui_options_visible):
            ui_opened_room = open_elementx_room(room_id)
            if ui_opened_room:
                time.sleep(3)
                ui_texts = visible_elementx_texts()
                ui_question_visible = any(text.strip() == question.strip() for text in ui_texts)
                ui_options_visible = all(ui_option_visible(ui_texts, option) for option in options)
        if ui_question_visible and ui_options_visible:
            current["poll"] = {{
                "event_id": None,
                "sender": sender,
                "question": question,
                "created_at_ms": None,
                "options": options,
                "encrypted_ui_match": True,
                "ui_opened_room": ui_opened_room,
                "ui_texts_sample": ui_texts[:20],
            }}

def text_equal(actual, expected):
    return ("" if actual is None else str(actual)).strip() == ("" if expected is None else str(expected)).strip()

def response_matches(expected: dict, actual: dict) -> bool:
    return (
        expected["username"] == actual["username"]
        and text_equal(expected["option"], actual["option"])
        and (
            expected.get("created_at_ms") is None
            or abs(int(actual.get("created_at_ms") or 0) - int(expected["created_at_ms"])) <= 1000
        )
    )

exact_match = bool(
    current
    and current["poll"] is not None
    and text_list(current["poll"]["options"]) == text_list(options)
    and (expected_created_at_ms is None or abs(int(current["poll"].get("created_at_ms") or 0) - int(expected_created_at_ms)) <= 1000)
    and all(any(response_matches(response, actual) for actual in current["responses"]) for response in expected_responses)
)
print(json.dumps({{
    "identity_exists": bool(current and current["poll"] is not None),
    "exact_match": exact_match,
    "current": current,
}}))
""",
        timeout=180,
    )
    return AssetProbe(
        label=f"elementx_poll:{asset.room}:{asset.question}",
        identity_exists=result["identity_exists"],
        exact_match=result["exact_match"],
        current=result["current"],
    )


def _probe_elementx_message_edit(
    client,
    before: ElementXMessageAsset,
    after: ElementXMessageAsset,
    task: BaseTask | None,
) -> AssetProbe:
    result = _exec_json(
        client,
        f"""
import hashlib
import json
import shlex
import subprocess
import requests
from urllib.parse import quote

base = {ELEMENTX_BASE_URL!r}
server_name = {elementx_server_name()!r}
room_reference = {before.room!r}
sender = {elementx_user_id(before.sender_username)!r}
original_body = {before.text!r}
edited_body = {after.text!r}

def sql_literal(value: str) -> str:
    return value.replace("'", "''")

def read_token(user: str) -> str:
    user_id = f"@{{user}}:{{server_name}}"
    cmd = (
        "cd /tmp/gma_elementx_export/WhatsApp/synapse-docker && "
        "docker compose --project-name gma-elementx exec -T db "
        "psql -U synapse -d synapse -At -c "
        + shlex.quote(
            "select token from access_tokens where user_id = '"
            + sql_literal(user_id)
            + "' order by id desc limit 1;"
        )
    )
    token = subprocess.check_output(["sh", "-lc", cmd], text=True).strip()
    if not token:
        raise RuntimeError(f"Could not read ElementX token for {{user}}")
    return token

def resolve_room(reference: str, token: str) -> str | None:
    alias = reference
    if not alias.startswith("!") and not alias.startswith("#"):
        alias = f"#{{reference}}:{{server_name}}"
    if alias.startswith("#"):
        resp = requests.get(base + "/_matrix/client/v3/directory/room/" + quote(alias, safe=""), timeout=30)
        if resp.status_code == 200:
            return resp.json()["room_id"]
        if resp.status_code != 404:
            resp.raise_for_status()
    elif alias.startswith("!"):
        return alias
    joined = requests.get(
        base + "/_matrix/client/v3/joined_rooms",
        headers={{"Authorization": "Bearer " + token}},
        timeout=30,
    )
    joined.raise_for_status()
    for room_id in joined.json().get("joined_rooms", []):
        state = requests.get(
            base + f"/_matrix/client/v3/rooms/{{quote(room_id, safe='')}}/state/m.room.name",
            headers={{"Authorization": "Bearer " + token}},
            timeout=30,
        )
        if state.status_code == 200 and state.json().get("name") == reference:
            return room_id
    return None

token = read_token("testuser")
room_id = resolve_room(room_reference, token)
current = None
if room_id:
    cmd = (
        "cd /tmp/gma_elementx_export/WhatsApp/synapse-docker && "
        "docker compose --project-name gma-elementx exec -T db "
        "psql -U synapse -d synapse -At -F '\\t' -c "
        + shlex.quote(
            "select event_id, json from event_json "
            + "where room_id = '" + sql_literal(room_id) + "' "
            + "and json::json->>'type' = 'm.room.message' "
            + "and json::json->>'sender' = '" + sql_literal(sender) + "'"
        )
    )
    rows = [line for line in subprocess.check_output(["sh", "-lc", cmd], text=True).splitlines() if line.strip()]
    original_ids = []
    edited_event_id = None
    for raw in rows:
        row_event_id, payload = raw.split("\\t", 1)
        event = json.loads(payload)
        if (event.get("content") or {{}}).get("body") == original_body:
            original_ids.append(row_event_id)
    for raw in rows:
        row_event_id, payload = raw.split("\\t", 1)
        event = json.loads(payload)
        content = event.get("content", {{}})
        relates = content.get("m.relates_to", {{}})
        new_content = content.get("m.new_content", {{}})
        if (
            relates.get("rel_type") == "m.replace"
            and relates.get("event_id") in original_ids
            and new_content.get("body") == edited_body
        ):
            edited_event_id = row_event_id
            break
    current = {{
        "room_id": room_id,
        "sender": sender,
        "original_ids": original_ids,
        "edited_event_id": edited_event_id,
        "edited_body": edited_body if edited_event_id else None,
    }}

print(json.dumps({{
    "identity_exists": bool(current and current["original_ids"]),
    "exact_match": bool(current and current["edited_event_id"]),
    "current": current,
}}))
""",
        timeout=180,
    )
    return AssetProbe(
        label=f"elementx_message_edit:{before.room}:{before.sender_username}",
        identity_exists=result["identity_exists"],
        exact_match=result["exact_match"],
        current=result["current"],
    )


def _read_mail_json(client, path: str) -> dict[str, Any] | list[Any] | None:
    raw = client.shell(f"cat {shlex.quote(path)} 2>/dev/null || true").replace("\r", "").strip()
    if not raw:
        return None
    return json.loads(raw)


def _probe_mail_account(client, asset: MailAccountAsset, task: BaseTask | None) -> AssetProbe:
    state = _read_mail_json(client, MAIL_STATE_PATH) or {}
    current = {
        "display_name": state.get("username", ""),
        "email": state.get("email", ""),
    }
    exact_match = _text_equal(current["display_name"], asset.display_name) and current["email"] == asset.email
    return AssetProbe(
        label=f"mail_account:{asset.display_name}",
        identity_exists=bool(current["display_name"] or current["email"]),
        exact_match=exact_match,
        current=current,
    )


def _probe_mail_reply_message(client, asset: MailMessageAsset) -> AssetProbe:
    candidates = _mail_sent_candidates(client)
    current = next((item for item in candidates if _mail_reply_current_matches(item, asset)), None)
    exact_match = current is not None
    if current is None and candidates:
        current = candidates[0]
    reply_to = asset.reply_to
    return AssetProbe(
        label=f"mail_reply:{reply_to.subject if reply_to else asset.subject}->{asset.subject}",
        identity_exists=bool(candidates),
        exact_match=exact_match,
        current=current,
    )


def _mail_entry_matches(entry: dict[str, Any], asset: MailMessageAsset) -> bool:
    headers = entry.get("headers", {})
    return (
        _text_equal(headers.get("subject"), asset.subject)
        and headers.get("sender") == asset.from_email
        and headers.get("from") == _mail_expected_sender(asset)
        and headers.get("to") == ", ".join(asset.to)
        and _text_equal(entry.get("body"), asset.body)
        and entry.get("mailbox") == asset.mailbox
    )


def _probe_mail_message(client, asset: MailMessageAsset, task: BaseTask | None) -> AssetProbe:
    if asset.mailbox == "sent" and asset.reply_to is not None:
        return _probe_mail_reply_message(client, asset)

    current = None
    if asset.mailbox == "sent":
        candidates = _mail_sent_candidates(client)
        current = next((item for item in candidates if _mail_sent_current_matches(item, asset)), None)
        if current is None and candidates:
            current = candidates[0]
    else:
        state = _read_mail_json(client, MAIL_STATE_PATH) or {}
        for entry in state.get("mails", []) or []:
            if _mail_entry_matches(entry, asset):
                headers = entry.get("headers", {})
                current = {
                    "mailbox": entry.get("mailbox"),
                    "from_email": headers.get("sender"),
                    "to": headers.get("to"),
                    "subject": headers.get("subject"),
                    "body": entry.get("body"),
                    "attachments": list(entry.get("attachments") or []),
                    "date": headers.get("date"),
                    "status": entry.get("status"),
                }
                break
    expected_attachment_names = _mail_attachment_names(asset)
    if asset.mailbox == "sent":
        exact_match = bool(current and _mail_sent_current_matches(current, asset))
    else:
        exact_match = bool(
            current
            and current["attachments"] == expected_attachment_names
            and current["status"] == _mail_status(asset)
            and (_mail_expected_date(asset) is None or current["date"] == _mail_expected_date(asset))
        )
    return AssetProbe(
        label=f"mail_message:{asset.mailbox}:{asset.subject}",
        identity_exists=current is not None,
        exact_match=exact_match,
        current=current,
    )



def _probe_mattermost_session(client, asset: MattermostSessionAsset, task: BaseTask | None) -> AssetProbe:
    # This confirms the intended session user exists. The actual mobile login
    # side effect is performed by MattermostSessionAsset insertion.
    current = None
    try:
        user = mattermost_api_request(client, "GET", f"/api/v4/users/username/{asset.username}")
        if int(user.get("delete_at") or 0) == 0:
            current = {"username": user.get("username"), "email": user.get("email")}
    except Exception:
        current = None
    return AssetProbe(
        label=f"mattermost_session:{asset.username}",
        identity_exists=current is not None,
        exact_match=current is not None,
        current=current,
    )


def _probe_mattermost_team(client, asset: MattermostTeamAsset, task: BaseTask | None) -> AssetProbe:
    current = None
    try:
        team = mattermost_api_request(client, "GET", f"/api/v4/teams/name/{asset.name}")
        if int(team.get("delete_at") or 0) == 0:
            current = {
                "name": team.get("name"),
                "display_name": team.get("display_name"),
                "team_type": team.get("type"),
                "description": team.get("description") or "",
                "allow_open_invite": bool(team.get("allow_open_invite")),
            }
    except Exception:
        current = None
    exact_match = bool(
        current
        and _text_equal(current["display_name"], asset.display_name)
        and current["team_type"] == asset.team_type
        and _text_equal(current["description"], asset.description or "")
        and current["allow_open_invite"] == asset.allow_open_invite
    )
    return AssetProbe(
        label=f"mattermost_team:{asset.name}",
        identity_exists=current is not None,
        exact_match=exact_match,
        current=current,
    )


def _probe_mattermost_channel(client, asset: MattermostChannelAsset, task: BaseTask | None) -> AssetProbe:
    current = None
    try:
        channel = mattermost_api_request(
            client,
            "GET",
            f"/api/v4/teams/name/{asset.team}/channels/name/{asset.name}",
        )
        if int(channel.get("delete_at") or 0) == 0:
            current = {
                "team": asset.team,
                "name": channel.get("name"),
                "display_name": channel.get("display_name"),
                "channel_type": channel.get("type"),
                "header": channel.get("header") or "",
                "purpose": channel.get("purpose") or "",
            }
    except Exception:
        current = None
    exact_match = bool(
        current
        and _optional_text_equal(current["display_name"], asset.display_name)
        and (asset.channel_type is None or current["channel_type"] == asset.channel_type)
        and _optional_text_equal(current["header"], asset.header)
        and _optional_text_equal(current["purpose"], asset.purpose)
    )
    return AssetProbe(
        label=f"mattermost_channel:{asset.team}:{asset.name}",
        identity_exists=current is not None,
        exact_match=exact_match,
        current=current,
    )


def _probe_mattermost_user(client, asset: MattermostUserAsset, task: BaseTask | None) -> AssetProbe:
    current = None
    try:
        user = mattermost_api_request(client, "GET", f"/api/v4/users/username/{asset.username}")
        if int(user.get("delete_at") or 0) == 0:
            user_id = user["id"]
            teams = mattermost_api_request(client, "GET", f"/api/v4/users/{user_id}/teams")
            team_names = {team["name"] for team in teams if int(team.get("delete_at") or 0) == 0}
            channel_names: list[str] = []
            if asset.team and asset.team in team_names:
                team = mattermost_api_request(client, "GET", f"/api/v4/teams/name/{asset.team}")
                team_id = team["id"]
                channels = mattermost_api_request(
                    client,
                    "GET",
                    f"/api/v4/users/{user_id}/teams/{team_id}/channels",
                )
                channel_names = sorted(
                    channel["name"] for channel in channels if int(channel.get("delete_at") or 0) == 0
                )
            current = {
                "username": user.get("username"),
                "email": user.get("email"),
                "first_name": user.get("first_name") or "",
                "last_name": user.get("last_name") or "",
                "position": user.get("position") or "",
                "teams": sorted(team_names),
                "channels": channel_names,
            }
    except Exception:
        current = None
    exact_match = bool(
        current
        and current["email"] == asset.email
        and _text_equal(current["first_name"], asset.first_name or "")
        and _text_equal(current["last_name"], asset.last_name or "")
        and _text_equal(current["position"], asset.position or "")
        and (asset.team is None or asset.team in current["teams"])
        and all(channel in current["channels"] for channel in asset.channel_memberships)
    )
    return AssetProbe(
        label=f"mattermost_user:{asset.username}",
        identity_exists=current is not None,
        exact_match=exact_match,
        current=current,
    )



def _probe_mattermost_channel_membership(
    client, asset: MattermostChannelMembershipAsset, task: BaseTask | None
) -> AssetProbe:
    current = None
    try:
        user = mattermost_api_request(client, "GET", f"/api/v4/users/username/{asset.username}")
        channel = mattermost_api_request(
            client,
            "GET",
            f"/api/v4/teams/name/{asset.team}/channels/name/{asset.channel}",
        )
        member = mattermost_api_request(
            client,
            "GET",
            f"/api/v4/channels/{channel['id']}/members/{user['id']}",
        )
        if int(member.get("delete_at") or 0) == 0:
            current = {
                "team": asset.team,
                "channel": asset.channel,
                "username": asset.username,
                "user_id": user.get("id"),
                "channel_id": channel.get("id"),
            }
    except Exception:
        current = None
    return AssetProbe(
        label=f"mattermost_channel_membership:{asset.team}:{asset.channel}:{asset.username}",
        identity_exists=current is not None,
        exact_match=current is not None,
        current=current,
    )


def _mattermost_direct_channel_info_existing(
    client,
    username: str,
    other_username: str,
) -> dict[str, Any] | None:
    user = mattermost_api_request(client, "GET", f"/api/v4/users/username/{username}")
    other = mattermost_api_request(client, "GET", f"/api/v4/users/username/{other_username}")
    expected_names = {f"{user['id']}__{other['id']}", f"{other['id']}__{user['id']}"}
    channels = mattermost_api_request(client, "GET", f"/api/v4/users/{user['id']}/channels")
    for channel in channels:
        if channel.get("type") != "D":
            continue
        if int(channel.get("delete_at") or 0) > 0:
            continue
        if channel.get("name") in expected_names or channel.get("teammate_id") == other["id"]:
            return channel
    return None


def _probe_mattermost_direct_channel(client, asset: MattermostDirectChannelAsset, task: BaseTask | None) -> AssetProbe:
    current = None
    try:
        channel = _mattermost_direct_channel_info_existing(client, asset.usernames[0], asset.usernames[1])
        if channel is not None:
            current = {
                "channel_id": channel.get("id"),
                "usernames": sorted(asset.usernames),
                "channel_type": channel.get("type"),
            }
    except Exception:
        current = None
    return AssetProbe(
        label=f"mattermost_direct_channel:{asset.usernames[0]}:{asset.usernames[1]}",
        identity_exists=current is not None,
        exact_match=current is not None,
        current=current,
    )


def _mattermost_find_post(
    client,
    *,
    team: str,
    channel: str,
    message: str,
    username: str | None = None,
    root_id: str | None = None,
) -> dict[str, Any] | None:
    channel_info = mattermost_api_request(
        client,
        "GET",
        f"/api/v4/teams/name/{team}/channels/name/{channel}",
    )
    user_id = None
    if username:
        user = mattermost_api_request(client, "GET", f"/api/v4/users/username/{username}")
        user_id = user["id"]
    channel_id = channel_info["id"]
    posts_payload = mattermost_api_request(
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



def _mattermost_find_direct_post_existing(
    client,
    *,
    username: str,
    other_username: str,
    message: str,
    author_username: str | None = None,
    root_id: str | None = None,
) -> dict[str, Any] | None:
    channel = _mattermost_direct_channel_info_existing(client, username, other_username)
    if channel is None:
        return None
    author_id = None
    if author_username:
        author = mattermost_api_request(client, "GET", f"/api/v4/users/username/{author_username}")
        author_id = author["id"]
    posts_payload = mattermost_api_request(
        client,
        "GET",
        f"/api/v4/channels/{channel['id']}/posts?page=0&per_page=200",
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


def _mattermost_direct_root_post_id_existing(client, asset: MattermostDirectPostAsset) -> str | None:
    if not asset.root_message:
        return None
    root_post = _mattermost_find_direct_post_existing(
        client,
        username=asset.username,
        other_username=asset.other_username,
        message=asset.root_message,
        author_username=asset.root_username or asset.username,
    )
    return root_post["id"] if root_post else None


def _probe_mattermost_direct_post(client, asset: MattermostDirectPostAsset, task: BaseTask | None) -> AssetProbe:
    current = None
    try:
        user = mattermost_api_request(client, "GET", f"/api/v4/users/username/{asset.username}")
        root_id = _mattermost_direct_root_post_id_existing(client, asset)
        post = _mattermost_find_direct_post_existing(
            client,
            username=asset.username,
            other_username=asset.other_username,
            message=asset.message,
            author_username=asset.username,
            root_id=root_id,
        )
        if post is not None:
            current = {
                "post_id": post.get("id"),
                "user_id": user["id"],
                "message": post.get("message"),
                "root_id": post.get("root_id") or "",
                "create_at_ms": int(post.get("create_at") or 0),
                "props": post.get("props") or {},
            }
    except Exception:
        current = None
    exact_match = bool(
        current
        and (asset.create_at_ms is None or current["create_at_ms"] == asset.create_at_ms)
        and current["props"] == asset.props
    )
    return AssetProbe(
        label=f"mattermost_direct_post:{asset.username}:{asset.other_username}",
        identity_exists=current is not None,
        exact_match=exact_match,
        current=current,
    )


def _mattermost_root_post_id(client, asset: MattermostPostAsset | MattermostFilePostAsset) -> str | None:
    if not asset.root_message:
        return None
    root_post = _mattermost_find_post(
        client,
        team=asset.team,
        channel=asset.channel,
        message=asset.root_message,
        username=asset.root_username or asset.username,
    )
    return root_post["id"] if root_post else None


def _probe_mattermost_post(client, asset: MattermostPostAsset, task: BaseTask | None) -> AssetProbe:
    current = None
    try:
        user = mattermost_api_request(client, "GET", f"/api/v4/users/username/{asset.username}")
        root_id = _mattermost_root_post_id(client, asset)
        post = _mattermost_find_post(
            client,
            team=asset.team,
            channel=asset.channel,
            message=asset.message,
            username=asset.username,
            root_id=root_id,
        )
        if post is not None:
            current = {
                "post_id": post.get("id"),
                "user_id": user["id"],
                "message": post.get("message"),
                "root_id": post.get("root_id") or "",
                "create_at_ms": int(post.get("create_at") or 0),
                "props": post.get("props") or {},
                "is_pinned": bool(post.get("is_pinned")),
            }
    except Exception:
        current = None
    exact_match = bool(
        current
        and (asset.create_at_ms is None or current["create_at_ms"] == asset.create_at_ms)
        and current["props"] == asset.props
        and (asset.pinned is None or current["is_pinned"] == asset.pinned)
    )
    return AssetProbe(
        label=f"mattermost_post:{asset.team}:{asset.channel}:{asset.username}",
        identity_exists=current is not None,
        exact_match=exact_match,
        current=current,
    )



def _mattermost_file_sha256(client, file_id: str) -> str:
    login_body = shlex.quote(json.dumps({
        "login_id": MATTERMOST_ADMIN_EMAIL,
        "password": MATTERMOST_ADMIN_PASSWORD,
    }))
    file_url = shlex.quote(f"http://localhost:8065/api/v4/files/{file_id}")
    return run_bash(
        client,
        f"""
set -euo pipefail
headers=$(mktemp)
trap "rm -f \"$headers\" /tmp/gma_mm_login.json" EXIT
curl -fsS -D "$headers" -o /tmp/gma_mm_login.json -X POST http://localhost:8065/api/v4/users/login \
  -H "Content-Type: application/json" \
  -d {login_body} >/dev/null

token=$(grep -i "^token:" "$headers" | head -n 1 | cut -d" " -f2 | tr -d "\r")
if [ -z "$token" ]; then
  echo "Missing Mattermost auth token" >&2
  exit 1
fi
curl -fsS {file_url} -H "Authorization: Bearer $token" | sha256sum | cut -d" " -f1
"""
        ,
        timeout=120,
    ).strip()


def _mattermost_mime_matches(actual: str | None, expected: str | None) -> bool:
    if expected is None:
        return True
    return (actual or "").split(";", 1)[0] == expected


def _mattermost_filename_matches(actual: str | None, expected: str, mime_type: str | None) -> bool:
    # The Android image picker can copy selected images to rn_image_picker_lib_temp_*.
    # For image uploads, content hash + MIME type is the stable identity.
    if (mime_type or "").startswith("image/"):
        return True
    return actual == expected


def _probe_mattermost_file_post(client, asset: MattermostFilePostAsset, task: BaseTask | None) -> AssetProbe:
    current = None
    try:
        payload_asset = _serialize_for_eval(asset, task=task)
        expected_sha256 = _sha256_b64(payload_asset["content_b64"])
        user = mattermost_api_request(client, "GET", f"/api/v4/users/username/{asset.username}")
        root_id = _mattermost_root_post_id(client, asset)
        post = _mattermost_find_post(
            client,
            team=asset.team,
            channel=asset.channel,
            message=asset.message,
            username=asset.username,
            root_id=root_id,
        )
        if post is not None:
            file_matches = []
            for file_id in post.get("file_ids") or []:
                info = mattermost_api_request(client, "GET", f"/api/v4/files/{file_id}/info")
                sha256 = _mattermost_file_sha256(client, file_id)
                file_matches.append({
                    "file_id": file_id,
                    "filename": info.get("name"),
                    "mime_type": info.get("mime_type"),
                    "sha256": sha256,
                })
            current = {
                "post_id": post.get("id"),
                "user_id": user["id"],
                "message": post.get("message"),
                "root_id": post.get("root_id") or "",
                "create_at_ms": int(post.get("create_at") or 0),
                "props": post.get("props") or {},
                "is_pinned": bool(post.get("is_pinned")),
                "files": file_matches,
            }
    except Exception:
        current = None
    exact_match = bool(
        current
        and (asset.create_at_ms is None or current["create_at_ms"] == asset.create_at_ms)
        and current["props"] == asset.props
        and (asset.pinned is None or current["is_pinned"] == asset.pinned)
        and any(
            _mattermost_filename_matches(item["filename"], asset.filename, asset.mime_type)
            and _mattermost_mime_matches(item["mime_type"], asset.mime_type)
            and item["sha256"] == expected_sha256
            for item in current["files"]
        )
    )
    return AssetProbe(
        label=f"mattermost_file_post:{asset.team}:{asset.channel}:{asset.username}:{asset.filename}",
        identity_exists=current is not None,
        exact_match=exact_match,
        current=current,
    )

def _normalize_mattermost_emoji_name(value: str | None) -> str:
    aliases = {
        "+1": "thumbsup",
        "thumbsup": "thumbsup",
        "-1": "thumbsdown",
        "thumbsdown": "thumbsdown",
    }
    normalized = (value or "").strip().strip(":")
    return aliases.get(normalized, normalized)

def _probe_mattermost_reaction(client, asset: MattermostReactionAsset, task: BaseTask | None) -> AssetProbe:
    current = None
    try:
        user = mattermost_api_request(client, "GET", f"/api/v4/users/username/{asset.username}")
        post = _mattermost_find_post(
            client,
            team=asset.team,
            channel=asset.channel,
            message=asset.post_message,
            username=asset.post_username,
        )
        if post is not None:
            post_id = post["id"]
            reactions = mattermost_api_request(client, "GET", f"/api/v4/posts/{post_id}/reactions")
            for reaction in reactions:
                if (
                    reaction.get("user_id") == user["id"]
                    and _normalize_mattermost_emoji_name(reaction.get("emoji_name"))
                    == _normalize_mattermost_emoji_name(asset.emoji_name)
                ):
                    current = {
                        "post_id": post["id"],
                        "username": asset.username,
                        "emoji_name": reaction.get("emoji_name"),
                    }
                    break
    except Exception:
        current = None
    return AssetProbe(
        label=f"mattermost_reaction:{asset.team}:{asset.channel}:{asset.emoji_name}",
        identity_exists=current is not None,
        exact_match=current is not None,
        current=current,
    )


def _probe_tempus_playlist(client, asset: TempusPlaylistAsset, task: BaseTask | None) -> AssetProbe:
    result = _exec_json(
        client,
        f"""
import json
import sqlite3

db_path = {TEMPUS_DB_PATH!r}
owner_username = {asset.owner_username!r}
playlist_name = {asset.name!r}
expected_comment = {asset.comment!r}
expected_visibility = {asset.visibility!r}
expected_public = None if expected_visibility is None else expected_visibility == "public"
expected_tracks = {asset.track_titles!r}
expected_track_albums = {asset.track_albums!r}
expected_track_match = {asset.track_match!r}

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
owner_row = conn.execute(
    "select id from user where user_name = ? order by created_at limit 1",
    (owner_username,),
).fetchone()
current = None
if owner_row is not None:
    playlist_row = conn.execute(
        "select id, comment, public, song_count from playlist where owner_id = ? and name = ? "
        "order by updated_at desc, id desc limit 1",
        (owner_row["id"], playlist_name),
    ).fetchone()
    if playlist_row is not None:
        track_rows = conn.execute(
            "select media_file.title, media_file.album from playlist_tracks "
            "join media_file on media_file.id = playlist_tracks.media_file_id "
            "where playlist_tracks.playlist_id = ? order by playlist_tracks.id",
            (playlist_row["id"],),
        ).fetchall()
        track_items = [
            {{"title": row["title"], "album": row["album"] or ""}}
            for row in track_rows
        ]
        current = {{
            "playlist_id": playlist_row["id"],
            "comment": playlist_row["comment"] or "",
            "public": bool(playlist_row["public"]),
            "visibility": "public" if playlist_row["public"] else "private",
            "song_count": int(playlist_row["song_count"] or 0),
            "track_titles": [item["title"] for item in track_items],
            "tracks": track_items,
        }}
conn.close()
def track_matches(expected_title):
    expected_album = expected_track_albums.get(expected_title)
    for item in current["tracks"]:
        if item["title"] != expected_title:
            continue
        if expected_album is None or item["album"] == expected_album:
            return True
    return False

def text_equal(actual, expected):
    return ("" if actual is None else str(actual)).strip() == ("" if expected is None else str(expected)).strip()

exact_match = bool(
    current
    and text_equal(current["comment"], expected_comment or "")
    and (expected_public is None or current["public"] == bool(expected_public))
    and (
        len(current["tracks"]) == len(expected_tracks)
        and all(track_matches(track) for track in expected_tracks)
        if expected_track_match == "exact"
        else all(track_matches(track) for track in expected_tracks)
    )
)
print(json.dumps({{
    "identity_exists": current is not None,
    "exact_match": exact_match,
    "current": current,
}}))
""",
        timeout=120,
    )
    return AssetProbe(
        label=f"tempus_playlist:{asset.owner_username}:{asset.name}",
        identity_exists=result["identity_exists"],
        exact_match=result["exact_match"],
        current=result["current"],
    )


def _probe_tempus_favorite(client, asset: TempusFavoriteAsset, task: BaseTask | None) -> AssetProbe:
    target_name = asset.track_title if asset.item_type == "song" else asset.album_name
    song_album_name = asset.album_name if asset.item_type == "song" else None
    target_table = "media_file" if asset.item_type == "song" else "album"
    target_column = "title" if asset.item_type == "song" else "name"
    target_item_type = "media_file" if asset.item_type == "song" else "album"
    device = getattr(client, "device", "emulator-5554")
    result = _exec_json(
        client,
        f"""
import json
import os
import sqlite3
import subprocess

db_path = {TEMPUS_DB_PATH!r}
android_db_path = {TEMPUS_ANDROID_DB_PATH!r}
device = {device!r}
owner_username = {asset.owner_username!r}
target_name = {target_name!r}
song_album_name = {song_album_name!r}
target_table = {target_table!r}
target_column = {target_column!r}
target_item_type = {target_item_type!r}

conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row
owner_row = conn.execute(
    "select id from user where user_name = ? order by created_at limit 1",
    (owner_username,),
).fetchone()
target_select_extra = ", album" if target_item_type == "media_file" else ""
target_query = f"select id, {{target_column}} as item_name{{target_select_extra}} from {{target_table}} where {{target_column}} = ?"
target_params = [target_name]
if target_item_type == "media_file" and song_album_name:
    target_query += " and album = ?"
    target_params.append(song_album_name)
target_query += " order by id"
target_rows = conn.execute(target_query, tuple(target_params)).fetchall()
current = None
candidates = []
local_conn = None
local_checked = False
local_error = None
if owner_row is not None and target_rows:
    try:
        tmp_db = "/tmp/gma_tempus_eval.db"
        for suffix in ("", "-wal", "-shm"):
            try:
                os.remove(tmp_db + suffix)
            except FileNotFoundError:
                pass
        subprocess.run(["adb", "-s", device, "root"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        pulled = False
        for suffix in ("", "-wal", "-shm"):
            remote = android_db_path + suffix
            local_path = tmp_db + suffix
            pull = subprocess.run(
                ["adb", "-s", device, "pull", remote, local_path],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
            pulled = pulled or (suffix == "" and pull.returncode == 0)
        local_checked = pulled
        if pulled:
            local_conn = sqlite3.connect(tmp_db)
            local_conn.row_factory = sqlite3.Row
    except Exception as exc:
        local_error = repr(exc)

    for target_row in target_rows:
        rows = conn.execute(
            "select item_type, starred, starred_at from annotation where user_id = ? and item_id = ?",
            (owner_row["id"], target_row["id"]),
        ).fetchall()
        backend_starred = any(bool(row["starred"]) and row["item_type"] == target_item_type for row in rows)
        local = {{"checked": local_checked, "starred": False, "rows": [], "error": local_error}}
        if local_conn is not None:
            favorite_column = "songId" if target_item_type == "media_file" else "albumId"
            local_rows = local_conn.execute(
                f"select timestamp, songId, albumId, artistId, toStar from favorite where {{favorite_column}} = ? order by timestamp desc",
                (target_row["id"],),
            ).fetchall()
            local["rows"] = [
                {{
                    "timestamp": row["timestamp"],
                    "songId": row["songId"],
                    "albumId": row["albumId"],
                    "artistId": row["artistId"],
                    "toStar": row["toStar"],
                }}
                for row in local_rows
            ]
            local["starred"] = bool(local_rows and local_rows[0]["toStar"])
        local_has_state = bool(local["rows"])
        starred = local["starred"] if local_has_state else backend_starred
        candidate_album = target_row["album"] if target_item_type == "media_file" else song_album_name
        candidate = {{
            "user_id": owner_row["id"],
            "item_id": target_row["id"],
            "item_type": target_item_type,
            "item_name": target_name,
            "album_name": candidate_album,
            "starred": starred,
            "backend_starred": backend_starred,
            "state_source": "local" if local_has_state else "backend",
            "backend_rows": [
                {{
                    "item_type": row["item_type"],
                    "starred": bool(row["starred"]),
                    "starred_at": row["starred_at"],
                }}
                for row in rows
            ],
            "local": local,
        }}
        candidates.append(candidate)
        if starred and current is None:
            current = candidate
    if local_conn is not None:
        local_conn.close()
if current is None and candidates:
    current = candidates[0]
if current is not None:
    current = dict(current)
    current["candidates"] = candidates
conn.close()
print(json.dumps({{
    "identity_exists": bool(current and current["starred"]),
    "exact_match": bool(current and current["starred"]),
    "current": current,
}}))
""",
        timeout=120,
    )
    label_target = f"{target_name} ({asset.album_name})" if asset.item_type == "song" and asset.album_name else target_name
    return AssetProbe(
        label=f"tempus_favorite:{asset.owner_username}:{asset.item_type}:{label_target}",
        identity_exists=result["identity_exists"],
        exact_match=result["exact_match"],
        current=result["current"],
    )


def _probe_mastodon_account(client, asset: MastodonAccountAsset, task: BaseTask | None) -> AssetProbe:
    output = _mastodon_rails_runner(
        client,
        f"""
username = {json.dumps(asset.username)}
account = Account.find_by(username: username, domain: nil)
if account.nil?
  puts({{exists: false}}.to_json)
else
  user = account.user
  puts({{
    exists: true,
    username: account.username,
    email: user&.email,
    display_name: account.display_name,
    bio: account.note
  }}.to_json)
end
""",
        timeout=180,
    )
    payload = json.loads(output)
    current = None
    if payload.get("exists"):
        current = {
            "username": payload.get("username"),
            "email": payload.get("email"),
            "display_name": payload.get("display_name") or "",
            "bio": payload.get("bio") or "",
        }
    exact_match = bool(
        current
        and current["email"] == asset.email
        and _text_equal(current["display_name"], asset.display_name or "")
        and _text_equal(current["bio"], asset.bio or "")
    )
    return AssetProbe(
        label=f"mastodon_account:{asset.username}",
        identity_exists=current is not None,
        exact_match=exact_match,
        current=current,
    )


def _probe_mastodon_status(client, asset: MastodonStatusAsset, task: BaseTask | None) -> AssetProbe:
    payload = _serialize_for_eval(asset, task)
    output = _mastodon_rails_runner(
        client,
        f'''
require "base64"
require "json"
payload = JSON.parse({json.dumps(json.dumps(payload))})

def text_matches?(actual, expected)
  actual.to_s.strip == expected.to_s.strip
end

def find_local_status(username, text)
  account = Account.find_by(username: username, domain: nil)
  return nil if account.nil?
  Status.where(account: account, reblog_of_id: nil, deleted_at: nil).order(created_at: :desc).to_a.find {{ |status| text_matches?(status.text, text) }}
end

def reply_text_matches?(actual, expected)
  return true if text_matches?(actual, expected)
  text_matches?(actual.to_s.sub(/\\A(?:@\\S+\\s+)+/, ""), expected)
end

def media_original_content_b64(item)
  path = item.file.path(:original) rescue nil
  return nil if path.nil? || !File.file?(path)
  Base64.strict_encode64(File.binread(path))
rescue
  nil
end

account = Account.find_by(username: payload["username"], domain: nil)
expected_reply = nil
if payload["reply_to_id"]
  expected_reply = Status.find_by(id: payload["reply_to_id"])
elsif payload["reply_to_username"] && payload["reply_to_text"]
  expected_reply = find_local_status(payload["reply_to_username"], payload["reply_to_text"])
end

if account.nil?
  puts({{exists: false, expected_reply_id: expected_reply&.id}}.to_json)
  exit
end

scope = Status.where(account: account, reblog_of_id: nil, deleted_at: nil).order(created_at: :desc)
if expected_reply
  scope = scope.where(in_reply_to_id: expected_reply.id)
end
expected_media_count = (payload["media_attachments"] || []).length
needs_poll = !payload["poll"].nil?
status = scope.to_a.find do |candidate|
  text_ok = expected_reply ? reply_text_matches?(candidate.text, payload["text"]) : text_matches?(candidate.text, payload["text"])
  text_ok && (!needs_poll || candidate.poll.present?) && (expected_media_count.zero? || candidate.media_attachments.count >= expected_media_count)
end

if status.nil?
  puts({{exists: false, expected_reply_id: expected_reply&.id}}.to_json)
else
  media = status.media_attachments.order(:id).map do |item|
    {{
      filename: item.file_file_name,
      mime_type: item.file_content_type,
      description: item.description.to_s,
      type: item.type,
      content_b64: media_original_content_b64(item),
    }}
  end
  poll = if status.poll
    {{
      options: status.poll.options,
      multiple: !!status.poll.multiple,
      hide_totals: !!status.poll.hide_totals,
      votes_count: status.poll.votes_count,
    }}
  end
  puts({{
    exists: true,
    text: status.text,
    visibility: status.visibility,
    spoiler_text: status.spoiler_text.to_s,
    sensitive: !!status.sensitive,
    in_reply_to_id: status.in_reply_to_id,
    expected_reply_id: expected_reply&.id,
    created_at: status.created_at.to_f,
    media_attachments: media,
    poll: poll,
  }}.to_json)
end
''',
        timeout=180,
    )
    probe_payload = json.loads(output)
    current = None
    if probe_payload.get("exists"):
        current = {
            "text": probe_payload.get("text"),
            "visibility": probe_payload.get("visibility"),
            "spoiler_text": probe_payload.get("spoiler_text") or "",
            "sensitive": bool(probe_payload.get("sensitive")),
            "reply_to_id": probe_payload.get("in_reply_to_id"),
            "created_at": probe_payload.get("created_at"),
            "media_attachments": probe_payload.get("media_attachments") or [],
            "poll": probe_payload.get("poll"),
        }

    def media_matches() -> bool:
        expected = payload.get("media_attachments") or []
        if not expected:
            return True
        actual = list(current.get("media_attachments") or []) if current else []
        if len(actual) < len(expected):
            return False
        used: set[int] = set()
        for item in expected:
            matched_index = None
            for index, candidate in enumerate(actual):
                if index in used:
                    continue
                if item.get("match_filename") and item.get("filename") is not None and candidate.get("filename") != item.get("filename"):
                    continue
                if item.get("mime_type") is not None and candidate.get("mime_type") != item.get("mime_type"):
                    continue
                if item.get("description") is not None and not _text_equal(candidate.get("description"), item.get("description")):
                    continue
                if item.get("content_b64") is not None:
                    images_match, _summary = _image_expectations_match([item], [candidate])
                    if not images_match:
                        continue
                matched_index = index
                break
            if matched_index is None:
                return False
            used.add(matched_index)
        return True

    def poll_matches() -> bool:
        expected = payload.get("poll")
        if expected is None:
            return True
        actual = current.get("poll") if current else None
        return bool(
            actual
            and _text_tuple(actual.get("options") or ()) == _text_tuple(expected.get("options") or ())
            and bool(actual.get("multiple")) == bool(expected.get("multiple"))
            and bool(actual.get("hide_totals")) == bool(expected.get("hide_totals"))
        )

    expected_reply_was_specified = bool(payload.get("reply_to_id") or payload.get("reply_to_username"))
    expected_reply_id = probe_payload.get("expected_reply_id") if expected_reply_was_specified else None
    reply_matches = (
        current is not None
        and ((current["reply_to_id"] == expected_reply_id) if expected_reply_was_specified else current["reply_to_id"] is None)
    )
    exact_match = bool(
        current
        and current["visibility"] == asset.visibility
        and _text_equal(current["spoiler_text"], asset.spoiler_text or "")
        and current["sensitive"] == asset.sensitive
        and reply_matches
        and media_matches()
        and poll_matches()
        and (
            asset.created_at_ms is None
            or abs(float(current["created_at"] or 0) * 1000 - int(asset.created_at_ms)) <= 1000
        )
    )
    if current:
        current["media_attachments"] = _sanitize_image_content_items(current["media_attachments"])
    return AssetProbe(
        label=f"mastodon_status:{asset.username}:{asset.text}",
        identity_exists=current is not None,
        exact_match=exact_match,
        current=current,
    )


def _probe_mastodon_follow(client, asset: MastodonFollowAsset, task: BaseTask | None) -> AssetProbe:
    output = _mastodon_rails_runner(
        client,
        f"""
require "json"
follower = Account.find_by(username: {json.dumps(asset.follower_username)}, domain: nil)
followed = Account.find_by(username: {json.dumps(asset.followed_username)}, domain: nil)
if follower.nil? || followed.nil?
  puts({{exists: false}}.to_json)
else
  relation = Follow.find_by(account_id: follower.id, target_account_id: followed.id)
  puts({{
    exists: !relation.nil?,
    follower: follower.username,
    followed: followed.username
  }}.to_json)
end
""",
        timeout=180,
    )
    payload = json.loads(output)
    current = None
    if payload.get("exists"):
        current = {
            "follower": payload.get("follower"),
            "followed": payload.get("followed"),
        }
    return AssetProbe(
        label=f"mastodon_follow:{asset.follower_username}->{asset.followed_username}",
        identity_exists=current is not None,
        exact_match=current is not None,
        current=current,
    )


def _probe_mastodon_status_interaction(client, asset, interaction: str) -> AssetProbe:
    output = _mastodon_rails_runner(
        client,
        f'''
require "json"
actor = Account.find_by(username: {json.dumps(asset.actor_username)}, domain: nil)
target_account = Account.find_by(username: {json.dumps(asset.target_username)}, domain: nil)
target = target_account && Status.where(account: target_account, reblog_of_id: nil, deleted_at: nil).order(created_at: :desc).to_a.find {{ |status| status.text.to_s.strip == {json.dumps(asset.target_text)}.to_s.strip }}
exists = false
if actor && target
  case {json.dumps(interaction)}
  when "favorite"
    exists = Favourite.exists?(account: actor, status: target)
  when "reblog"
    exists = Status.exists?(account: actor, reblog_of_id: target.id, deleted_at: nil)
  when "bookmark"
    exists = Bookmark.exists?(account: actor, status: target)
  end
end
puts({{
  exists: exists,
  actor: actor&.username,
  target_username: target_account&.username,
  target_text: target&.text,
  interaction: {json.dumps(interaction)},
}}.to_json)
''',
        timeout=180,
    )
    payload = json.loads(output)
    current = None
    if payload.get("exists"):
        current = {
            "actor": payload.get("actor"),
            "target_username": payload.get("target_username"),
            "target_text": payload.get("target_text"),
            "interaction": payload.get("interaction"),
        }
    return AssetProbe(
        label=f"mastodon_{interaction}:{asset.actor_username}:{asset.target_username}:{asset.target_text}",
        identity_exists=current is not None,
        exact_match=current is not None,
        current=current,
    )


def _probe_mastodon_poll_vote(client, asset: MastodonPollVoteAsset, task: BaseTask | None) -> AssetProbe:
    output = _mastodon_rails_runner(
        client,
        f'''
require "json"
voter = Account.find_by(username: {json.dumps(asset.voter_username)}, domain: nil)
poll_account = Account.find_by(username: {json.dumps(asset.poll_username)}, domain: nil)
status = poll_account && Status.where(account: poll_account, reblog_of_id: nil, deleted_at: nil).order(created_at: :desc).to_a.find {{ |item| item.text.to_s.strip == {json.dumps(asset.poll_text)}.to_s.strip }}
poll = status&.poll
choices = []
if voter && poll
  choices = PollVote.where(account: voter, poll: poll).order(:choice).map {{ |vote| poll.options[vote.choice] }}.compact
end
puts({{
  exists: voter && poll && choices.any?,
  voter: voter&.username,
  poll_username: poll_account&.username,
  poll_text: status&.text,
  choices: choices,
}}.to_json)
''',
        timeout=180,
    )
    payload = json.loads(output)
    current = None
    if payload.get("exists"):
        current = {
            "voter": payload.get("voter"),
            "poll_username": payload.get("poll_username"),
            "poll_text": payload.get("poll_text"),
            "choices": payload.get("choices") or [],
        }
    expected = {str(choice).strip() for choice in asset.choices}
    actual = {str(choice).strip() for choice in (current.get("choices") or [])} if current else set()
    exact_match = current is not None and actual == expected and len(actual) == len(asset.choices)
    return AssetProbe(
        label=f"mastodon_poll_vote:{asset.voter_username}:{asset.poll_username}:{asset.poll_text}",
        identity_exists=current is not None,
        exact_match=exact_match,
        current=current,
    )


def _asset_probe_from_remote(payload: dict[str, Any]) -> AssetProbe:
    return AssetProbe(
        label=payload.get("label", "asset"),
        identity_exists=bool(payload.get("identity_exists")),
        exact_match=bool(payload.get("exact_match")),
        current=payload.get("current"),
    )


def _probe_asset(client, asset: Asset | dict, task: BaseTask | None = None) -> AssetProbe:
    parsed = parse_asset(asset)
    if isinstance(parsed, ContactAsset):
        return _probe_contact(client, parsed, task)
    if isinstance(parsed, SmsMessageAsset):
        return _probe_sms(client, parsed, task)
    if isinstance(parsed, AlarmAsset):
        return _probe_alarm(client, parsed, task)
    if isinstance(parsed, CalendarEventAsset):
        return _probe_calendar_event(client, parsed, task)
    if isinstance(parsed, DeviceFileAsset):
        return _probe_device_file(client, parsed, task)
    if isinstance(parsed, ElementXUserAsset):
        return _probe_elementx_user(client, parsed, task)
    if isinstance(parsed, ElementXRoomAsset):
        return _probe_elementx_room(client, parsed, task)
    if isinstance(parsed, ElementXMessageAsset):
        return _probe_elementx_message(client, parsed, task)
    if isinstance(parsed, ElementXFileAsset):
        return _probe_elementx_file(client, parsed, task)
    if isinstance(parsed, ElementXPollAsset):
        return _probe_elementx_poll(client, parsed, task)
    if isinstance(parsed, MailAccountAsset):
        return _probe_mail_account(client, parsed, task)
    if isinstance(parsed, MailMessageAsset):
        return _probe_mail_message(client, parsed, task)
    if isinstance(parsed, MattermostTeamAsset):
        return _probe_mattermost_team(client, parsed, task)
    if isinstance(parsed, MattermostSessionAsset):
        return _probe_mattermost_session(client, parsed, task)
    if isinstance(parsed, MattermostChannelAsset):
        return _probe_mattermost_channel(client, parsed, task)
    if isinstance(parsed, MattermostChannelMembershipAsset):
        return _probe_mattermost_channel_membership(client, parsed, task)
    if isinstance(parsed, MattermostDirectChannelAsset):
        return _probe_mattermost_direct_channel(client, parsed, task)
    if isinstance(parsed, MattermostUserAsset):
        return _probe_mattermost_user(client, parsed, task)
    if isinstance(parsed, MattermostPostAsset):
        return _probe_mattermost_post(client, parsed, task)
    if isinstance(parsed, MattermostFilePostAsset):
        return _probe_mattermost_file_post(client, parsed, task)
    if isinstance(parsed, MattermostDirectPostAsset):
        return _probe_mattermost_direct_post(client, parsed, task)
    if isinstance(parsed, MattermostReactionAsset):
        return _probe_mattermost_reaction(client, parsed, task)
    if isinstance(parsed, TempusPlaylistAsset):
        return _probe_tempus_playlist(client, parsed, task)
    if isinstance(parsed, TempusFavoriteAsset):
        return _probe_tempus_favorite(client, parsed, task)
    if isinstance(parsed, MastodonAccountAsset):
        return _probe_mastodon_account(client, parsed, task)
    if isinstance(parsed, MastodonStatusAsset):
        return _probe_mastodon_status(client, parsed, task)
    if isinstance(parsed, MastodonFollowAsset):
        return _probe_mastodon_follow(client, parsed, task)
    if isinstance(parsed, MastodonFavoriteAsset):
        return _probe_mastodon_status_interaction(client, parsed, "favorite")
    if isinstance(parsed, MastodonReblogAsset):
        return _probe_mastodon_status_interaction(client, parsed, "reblog")
    if isinstance(parsed, MastodonBookmarkAsset):
        return _probe_mastodon_status_interaction(client, parsed, "bookmark")
    if isinstance(parsed, MastodonPollVoteAsset):
        return _probe_mastodon_poll_vote(client, parsed, task)
    if isinstance(parsed, XiaoShiLiuPostAsset) and parsed.expected_images:
        payload = _serialize_for_eval(parsed, task=task)
        probe = _asset_probe_from_remote(_probe_xiaoshiliu_asset_remote(client, payload))
        return _probe_with_expected_images(probe, payload["expected_images"])
    if isinstance(parsed, XiaoShiLiuUserAsset | XiaoShiLiuPostAsset | XiaoShiLiuCommentAsset | XiaoShiLiuLikeAsset | XiaoShiLiuCollectionAsset | XiaoShiLiuFollowAsset | XiaoShiLiuNotificationAsset):
        return _asset_probe_from_remote(_probe_xiaoshiliu_asset_remote(client, parsed))
    if isinstance(parsed, MallMemberAsset | MallAddressAsset | MallProductAsset | MallBrandAsset | MallCartItemAsset | MallOrderAsset | MallReviewAsset):
        return _asset_probe_from_remote(_probe_mall_asset_remote(client, parsed))
    if isinstance(parsed, MeituanUserAsset | MeituanRestaurantAsset | MeituanFoodAsset | MeituanAddressAsset | MeituanCartItemAsset | MeituanOrderAsset | MeituanCollectionAsset | MeituanCommentAsset):
        return _asset_probe_from_remote(_probe_meituan_asset_remote(client, parsed))
    if isinstance(parsed, TravelUserAsset | TravelFlightBookingAsset | TravelHotelBookingAsset | TravelAttractionBookingAsset | TravelFavoriteAsset | TravelReviewAsset):
        return _asset_probe_from_remote(_probe_travel_asset_remote(client, parsed))
    if isinstance(parsed, HmdpBlogAsset) and parsed.expected_images:
        payload = _serialize_for_eval(parsed, task=task)
        probe = _asset_probe_from_remote(_probe_hmdp_asset_remote(client, payload))
        return _probe_with_expected_images(probe, payload["expected_images"])
    if isinstance(parsed, HmdpUserAsset | HmdpShopAsset | HmdpBlogAsset | HmdpBlogCommentAsset | HmdpFollowAsset | HmdpShopFavoriteAsset | HmdpShopReviewAsset | HmdpBlogLikeAsset | HmdpVoucherAsset | HmdpVoucherOrderAsset):
        return _asset_probe_from_remote(_probe_hmdp_asset_remote(client, parsed))
    raise TypeError(f"Unsupported asset type: {type(parsed).__name__}")


def _result(name: str, passed: bool, reason: str, *, weight: float = 1.0) -> CriterionResult:
    return CriterionResult(
        name=name,
        passed=passed,
        score=1.0 if passed else 0.0,
        reason=reason,
        weight=weight,
    )


def asset_probe(client, asset: Asset | dict, *, task: BaseTask | None = None) -> AssetProbe:
    return _probe_asset(client, asset, task=task)


def asset_exists(
    client,
    asset: Asset | dict,
    *,
    task: BaseTask | None = None,
    weight: float = 1.0,
) -> CriterionResult:
    probe = asset_probe(client, asset, task=task)
    if probe.exact_match:
        return _result(
            f"AssetExists({probe.label})",
            True,
            f"{probe.label} matches expected state: {_as_json(probe.current)}",
            weight=weight,
        )
    return _result(
        f"AssetExists({probe.label})",
        False,
        f"{probe.label} does not match expected state. Current: {_as_json(probe.current)}",
        weight=weight,
    )


def asset_missing(
    client,
    asset: Asset | dict,
    *,
    task: BaseTask | None = None,
    weight: float = 1.0,
) -> CriterionResult:
    probe = asset_probe(client, asset, task=task)
    if not probe.exact_match:
        return _result(
            f"AssetMissing({probe.label})",
            True,
            f"{probe.label} is not present in the expected state. Current: {_as_json(probe.current)}",
            weight=weight,
        )
    return _result(
        f"AssetMissing({probe.label})",
        False,
        f"{probe.label} still matches the expected state: {_as_json(probe.current)}",
        weight=weight,
    )


def asset_deleted(
    client,
    asset: Asset | dict,
    *,
    task: BaseTask | None = None,
    weight: float = 1.0,
) -> CriterionResult:
    probe = asset_probe(client, asset, task=task)
    if not probe.identity_exists:
        return _result(
            f"AssetDeleted({probe.label})",
            True,
            f"{probe.label} no longer exists.",
            weight=weight,
        )
    return _result(
        f"AssetDeleted({probe.label})",
        False,
        f"{probe.label} still exists. Current: {_as_json(probe.current)}",
        weight=weight,
    )


def asset_modified(
    client,
    before: Asset | dict,
    after: Asset | dict,
    *,
    task: BaseTask | None = None,
    weight: float = 1.0,
) -> CriterionResult:
    before_asset = parse_asset(before)
    after_asset = parse_asset(after)
    if before_asset.kind != after_asset.kind:
        raise ValueError(
            f"AssetModified requires matching asset kinds, got {before_asset.kind!r} and {after_asset.kind!r}"
        )
    if (
        isinstance(before_asset, ElementXMessageAsset)
        and isinstance(after_asset, ElementXMessageAsset)
        and before_asset.room == after_asset.room
        and before_asset.sender_username == after_asset.sender_username
        and before_asset.text != after_asset.text
    ):
        edit_probe = _probe_elementx_message_edit(client, before_asset, after_asset, task)
        if edit_probe.exact_match:
            return _result(
                f"AssetModified({edit_probe.label})",
                True,
                (
                    f"{edit_probe.label} was edited into the expected message state. "
                    f"Current: {_as_json(edit_probe.current)}"
                ),
                weight=weight,
            )
        return _result(
            f"AssetModified({edit_probe.label})",
            False,
            f"Message edit was not observed. Current: {_as_json(edit_probe.current)}",
            weight=weight,
        )
    before_probe = asset_probe(client, before_asset, task=task)
    after_probe = asset_probe(client, after_asset, task=task)
    passed = (not before_probe.exact_match) and after_probe.exact_match
    if passed:
        return _result(
            f"AssetModified({before_probe.label})",
            True,
            (
                f"{before_probe.label} no longer matches the old state and now matches the new state. "
                f"Current: {_as_json(after_probe.current)}"
            ),
            weight=weight,
        )
    return _result(
        f"AssetModified({before_probe.label})",
        False,
        (
            f"Modification check failed. Old probe: {_as_json(before_probe.current)}; "
            f"new probe: {_as_json(after_probe.current)}"
        ),
        weight=weight,
    )




class AssetExists(Criterion):
    def __init__(self, asset: Asset | dict, *, task: BaseTask | None = None, weight: float = 1.0):
        super().__init__(weight=weight)
        self.asset = parse_asset(asset)
        self.task = task

    def evaluate(self, controller) -> CriterionResult:
        return asset_exists(controller, self.asset, task=self.task, weight=self.weight)


class AssetMissing(Criterion):
    def __init__(self, asset: Asset | dict, *, task: BaseTask | None = None, weight: float = 1.0):
        super().__init__(weight=weight)
        self.asset = parse_asset(asset)
        self.task = task

    def evaluate(self, controller) -> CriterionResult:
        return asset_missing(controller, self.asset, task=self.task, weight=self.weight)


class AssetDeleted(Criterion):
    def __init__(self, asset: Asset | dict, *, task: BaseTask | None = None, weight: float = 1.0):
        super().__init__(weight=weight)
        self.asset = parse_asset(asset)
        self.task = task

    def evaluate(self, controller) -> CriterionResult:
        return asset_deleted(controller, self.asset, task=self.task, weight=self.weight)


class AssetModified(Criterion):
    def __init__(
        self,
        before: Asset | dict,
        after: Asset | dict,
        *,
        task: BaseTask | None = None,
        weight: float = 1.0,
    ):
        super().__init__(weight=weight)
        self.before = parse_asset(before)
        self.after = parse_asset(after)
        self.task = task

    def evaluate(self, controller) -> CriterionResult:
        return asset_modified(
            controller,
            self.before,
            self.after,
            task=self.task,
            weight=self.weight,
        )



def _exec_json(client, script: str, timeout: float = 120.0) -> dict[str, Any]:
    output = client.exec("python3 - <<'PY'\n" + script + "\nPY", timeout=timeout)
    return json.loads(output)
