from __future__ import annotations

import base64
import hashlib
import json
import posixpath
import shlex
from pathlib import Path
from typing import TYPE_CHECKING, Any
from urllib.parse import unquote, urlparse

from gma.apps._shell import launch_webapp_with_login_extras, run_bash
from gma.apps.offline_webapps import ensure_xiaoshiliu_backend as _ensure_xiaoshiliu_backend

if TYPE_CHECKING:
    from gma.runtime.controller import AndroidController


XIAOSHILIU_WEB_URL = "http://10.0.2.2:8030"
XIAOSHILIU_API_URL = "http://localhost:8031"
XIAOSHILIU_HEALTH_URL = f"{XIAOSHILIU_API_URL}/api/health"
XIAOSHILIU_DEFAULT_AVATAR = "/assets/avatar-ClIy5dZi.png"
XIAOSHILIU_DEFAULT_IMAGE = "/assets/frame%20(1)-By2z8fPJ.jpg"
XIAOSHILIU_LOGIN_USER_ID = "xsl_user_000"
XIAOSHILIU_LOGIN_PASSWORD = "123456"
XIAOSHILIU_LOGIN_NICKNAME = "owner"
XIAOSHILIU_LOGIN_EMAIL = "xsl_user_000@example.com"


_RUNTIME = r'''
import base64
import hashlib
import html
import json
import subprocess
import sys
import urllib.request

MYSQL = [
    "docker",
    "exec",
    "-i",
    "xiaoshiliu-mysql",
    "mysql",
    "-uxiaoshiliu_user",
    "-p123456",
    "--default-character-set=utf8mb4",
    "xiaoshiliu",
]
QUERY = MYSQL + ["--batch", "--raw", "--skip-column-names"]
DEFAULT_AVATAR = "/assets/avatar-ClIy5dZi.png"
DEFAULT_IMAGE = "/assets/frame%20(1)-By2z8fPJ.jpg"
STATUS = {"published": 0, "draft": 1, "pending": 2}
STATUS_REV = {0: "published", 1: "draft", 2: "pending"}
POST_TYPE = {"image": 1, "video": 2}
POST_TYPE_REV = {1: "image", 2: "video"}
ALLOWED_CATEGORIES = {
    "Food",
    "Study",
    "Campus Life",
    "Photography",
    "Music",
    "Technology",
    "Fashion",
    "Fitness",
    "Travel",
    "Dorm Life",
}
NOTIFICATION_TYPE = {
    "like_post": 1,
    "like_comment": 2,
    "collection": 3,
    "comment": 4,
    "reply": 5,
    "follow": 6,
    "mention_comment": 7,
    "mention": 8,
}
NOTIFICATION_TYPE_REV = {value: key for key, value in NOTIFICATION_TYPE.items()}


def q(value):
    if value is None:
        return "NULL"
    return "'" + str(value).replace("\\", "\\\\").replace("'", "''").replace("\0", "") + "'"

def text_equal(a, b):
    if isinstance(a, str) and isinstance(b, str):
        return html.unescape(a).strip() == html.unescape(b).strip()
    return a == b


def b(value):
    return "1" if value else "0"


def ts(value_ms):
    if value_ms is None:
        return "CURRENT_TIMESTAMP"
    return "FROM_UNIXTIME(" + str(int(value_ms) / 1000.0) + ")"


def exec_sql(sql):
    subprocess.run(MYSQL, input=sql, text=True, check=True)


def rows(sql):
    output = subprocess.check_output(QUERY + ["-e", sql], text=True)
    return [["" if cell == "NULL" else cell for cell in line.split("\t")] for line in output.splitlines() if line.strip()]


def scalar(sql):
    data = rows(sql)
    if not data or not data[0]:
        return None
    return data[0][0]


def fetch_image_bytes(image_url):
    if not image_url:
        return None, "empty image url"
    value = str(image_url)
    candidates = []
    if value.startswith("http://10.0.2.2:"):
        candidates.append(value.replace("http://10.0.2.2:", "http://127.0.0.1:", 1))
    elif value.startswith("http://localhost:"):
        candidates.append(value.replace("http://localhost:", "http://127.0.0.1:", 1))
    elif value.startswith("http://127.0.0.1:"):
        candidates.append(value)
    elif value.startswith("http://") or value.startswith("https://"):
        candidates.append(value)
    else:
        path = value if value.startswith("/") else "/" + value
        for base in ("http://127.0.0.1:8030", "http://127.0.0.1:8031"):
            candidates.append(base + path)
    seen = set()
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            with urllib.request.urlopen(candidate, timeout=10) as response:
                return response.read(), None
        except Exception:
            pass
    if value.startswith("/"):
        container_paths = []
        if value.startswith("/uploads/"):
            container_paths.append(("xiaoshiliu-backend", "/app" + value))
        container_paths.append(("xiaoshiliu-frontend", "/usr/share/nginx/html" + value))
        for container, path in container_paths:
            try:
                return subprocess.check_output(["docker", "exec", container, "cat", path]), None
            except Exception:
                pass
    return None, "image bytes not found"


def image_contents(image_urls):
    items = []
    for image_url in image_urls or []:
        raw, error = fetch_image_bytes(image_url)
        item = {"url": image_url}
        if raw is not None:
            item["content_b64"] = base64.b64encode(raw).decode("ascii")
            item["byte_sha256"] = hashlib.sha256(raw).hexdigest()
        else:
            item["error"] = error
        items.append(item)
    return items


def ensure_post_schema():
    exists = scalar(
        "select count(*) from information_schema.columns where table_schema = database() "
        "and table_name = 'posts' and column_name = 'share_count'"
    )
    if int(exists or 0) == 0:
        exec_sql("alter table posts add column share_count int(11) default 0 comment 'share count' after comment_count")


def ensure_category(category):
    if not category:
        return None
    if category not in ALLOWED_CATEGORIES:
        raise ValueError("Unsupported XiaoShiLiu category: " + str(category))
    category_id = scalar(
        "select id from categories where name = " + q(category)
        + " or category_title = " + q(category)
        + " order by id limit 1"
    )
    if category_id:
        return int(category_id)
    raise ValueError("XiaoShiLiu category is not available in the app database: " + str(category))


def ensure_user(user_id, *, nickname=None):
    current = scalar("select id from users where user_id = " + q(user_id) + " limit 1")
    if current:
        return int(current)
    exec_sql(
        "insert into users (user_id, nickname, email, password, avatar, is_active, verified) values ("
        + q(user_id)
        + ", "
        + q(nickname or user_id)
        + ", "
        + q(user_id + "@example.com")
        + ", SHA2('123456', 256), "
        + q(DEFAULT_AVATAR)
        + ", 1, 0)"
    )
    return int(scalar("select id from users where user_id = " + q(user_id) + " limit 1"))


def user_id_for(logical_id):
    value = scalar("select id from users where user_id = " + q(logical_id) + " limit 1")
    return int(value) if value else None


def find_post_id(title, author_user_id):
    return _find_post_id(title, author_user_id)


def _find_post_id(title, author_user_id):
    value = scalar(
        "select p.id from posts p join users u on u.id = p.user_id "
        "where p.title = " + q(title) + " and u.user_id = " + q(author_user_id)
        + " order by p.id desc limit 1"
    )
    return int(value) if value else None


def find_comment_id(asset):
    post_id = find_post_id(asset.get("post_title"), asset.get("post_author_user_id"))
    if not post_id:
        return None
    author_id = user_id_for(asset.get("author_user_id") or asset.get("comment_author_user_id"))
    if not author_id:
        return None
    parent_sql = "c.parent_id is null"
    if asset.get("parent_content") and asset.get("parent_author_user_id"):
        parent_id = find_comment_id({
            "post_title": asset.get("post_title"),
            "post_author_user_id": asset.get("post_author_user_id"),
            "author_user_id": asset.get("parent_author_user_id"),
            "content": asset.get("parent_content"),
        })
        if not parent_id:
            return None
        parent_sql = "c.parent_id = " + str(parent_id)
    value = scalar(
        "select c.id from comments c where c.post_id = " + str(post_id)
        + " and c.user_id = " + str(author_id)
        + " and c.content = " + q(asset.get("content") or asset.get("comment_content"))
        + " and " + parent_sql
        + " order by c.id desc limit 1"
    )
    return int(value) if value else None


def resolve_target(asset):
    post_id = find_post_id(asset.get("post_title"), asset.get("post_author_user_id"))
    if not post_id:
        return None, None, None
    if asset.get("target_type", "post") == "post" or not asset.get("comment_content"):
        return 1, post_id, post_id
    comment_id = find_comment_id({
        "post_title": asset.get("post_title"),
        "post_author_user_id": asset.get("post_author_user_id"),
        "author_user_id": asset.get("comment_author_user_id"),
        "content": asset.get("comment_content"),
    })
    if not comment_id:
        return None, None, post_id
    return 2, comment_id, post_id


def recompute_post_counts(post_id):
    exec_sql(
        "update posts set "
        "like_count = (select count(*) from likes where target_type = 1 and target_id = " + str(post_id) + "), "
        "collect_count = (select count(*) from collections where post_id = " + str(post_id) + "), "
        "comment_count = (select count(*) from comments where post_id = " + str(post_id) + ") "
        "where id = " + str(post_id)
    )


def recompute_user_counts(user_db_id):
    exec_sql(
        "update users set "
        "follow_count = (select count(*) from follows where follower_id = " + str(user_db_id) + "), "
        "fans_count = (select count(*) from follows where following_id = " + str(user_db_id) + "), "
        "like_count = (select coalesce(sum(p.like_count), 0) from posts p where p.user_id = " + str(user_db_id) + ") "
        "where id = " + str(user_db_id)
    )


def apply_user(asset):
    nickname = asset.get("nickname") or asset["user_id"]
    email = asset.get("email") or asset["user_id"] + "@example.com"
    interests = json.dumps(asset.get("interests") or [], ensure_ascii=False)
    existing = user_id_for(asset["user_id"])
    if existing:
        exec_sql(
            "update users set "
            "password = SHA2(" + q(asset.get("password") or "123456") + ", 256), "
            "nickname = " + q(nickname) + ", "
            "email = " + q(email) + ", "
            "avatar = " + q(asset.get("avatar") or DEFAULT_AVATAR) + ", "
            "bio = " + q(asset.get("bio")) + ", "
            "location = " + q(asset.get("location")) + ", "
            "gender = " + q(asset.get("gender")) + ", "
            "zodiac_sign = " + q(asset.get("zodiac_sign")) + ", "
            "mbti = " + q(asset.get("mbti")) + ", "
            "education = " + q(asset.get("education")) + ", "
            "major = " + q(asset.get("major")) + ", "
            "interests = cast(" + q(interests) + " as json), "
            "verified = " + b(asset.get("verified")) + ", "
            "is_active = " + b(asset.get("is_active", True)) + " "
            "where id = " + str(existing)
        )
    else:
        exec_sql(
            "insert into users (user_id, password, nickname, email, avatar, bio, location, gender, zodiac_sign, mbti, education, major, interests, verified, is_active) values ("
            + q(asset["user_id"])
            + ", SHA2(" + q(asset.get("password") or "123456") + ", 256), "
            + q(nickname) + ", " + q(email) + ", " + q(asset.get("avatar") or DEFAULT_AVATAR) + ", "
            + q(asset.get("bio")) + ", " + q(asset.get("location")) + ", " + q(asset.get("gender")) + ", "
            + q(asset.get("zodiac_sign")) + ", " + q(asset.get("mbti")) + ", " + q(asset.get("education")) + ", "
            + q(asset.get("major")) + ", cast(" + q(interests) + " as json), " + b(asset.get("verified")) + ", " + b(asset.get("is_active", True)) + ")"
        )
    recompute_user_counts(user_id_for(asset["user_id"]))


def apply_post(asset):
    ensure_post_schema()
    share_count = max(0, int(asset.get("share_count") or 0))
    author_id = ensure_user(asset["author_user_id"])
    category_id = ensure_category(asset.get("category"))
    post_type = POST_TYPE[asset.get("post_type", "image")]
    status = STATUS[asset.get("status", "published")]
    post_id = find_post_id(asset["title"], asset["author_user_id"])
    category_sql = "NULL" if category_id is None else str(category_id)
    if post_id:
        exec_sql(
            "update posts set content = " + q(asset.get("content") or "")
            + ", category_id = " + category_sql
            + ", type = " + str(post_type)
            + ", status = " + str(status)
            + ", share_count = " + str(share_count)
            + (", created_at = " + ts(asset.get("created_at_ms")) if asset.get("created_at_ms") is not None else "")
            + " where id = " + str(post_id)
        )
        exec_sql("delete from post_images where post_id = " + str(post_id) + "; delete from post_videos where post_id = " + str(post_id) + "; delete from post_tags where post_id = " + str(post_id))
    else:
        exec_sql(
            "insert into posts (user_id, title, content, category_id, type, status, created_at, share_count) values ("
            + str(author_id) + ", " + q(asset["title"]) + ", " + q(asset.get("content") or "") + ", "
            + category_sql + ", " + str(post_type) + ", " + str(status) + ", " + ts(asset.get("created_at_ms")) + ", " + str(share_count) + ")"
        )
        post_id = find_post_id(asset["title"], asset["author_user_id"])
    if post_type == 1:
        images = asset.get("image_urls") or [DEFAULT_IMAGE]
        for image in images:
            exec_sql("insert into post_images (post_id, image_url) values (" + str(post_id) + ", " + q(image) + ")")
    else:
        exec_sql(
            "insert into post_videos (post_id, cover_url, video_url) values ("
            + str(post_id) + ", " + q(asset.get("cover_url") or DEFAULT_IMAGE) + ", " + q(asset.get("video_url")) + ")"
        )
    for tag in asset.get("tags") or []:
        exec_sql("insert into tags (name, use_count) values (" + q(tag) + ", 0) on duplicate key update name = values(name)")
        tag_id = int(scalar("select id from tags where name = " + q(tag) + " limit 1"))
        exec_sql("insert ignore into post_tags (post_id, tag_id) values (" + str(post_id) + ", " + str(tag_id) + ")")
    exec_sql("update tags t set use_count = (select count(*) from post_tags pt where pt.tag_id = t.id)")
    recompute_post_counts(post_id)
    recompute_user_counts(author_id)


def apply_comment(asset):
    author_id = ensure_user(asset["author_user_id"])
    post_id = find_post_id(asset["post_title"], asset["post_author_user_id"])
    if not post_id:
        raise RuntimeError("XiaoShiLiu post not found for comment: " + asset["post_title"])
    parent_id = None
    if asset.get("parent_content"):
        parent_id = find_comment_id({
            "post_title": asset["post_title"],
            "post_author_user_id": asset["post_author_user_id"],
            "author_user_id": asset["parent_author_user_id"],
            "content": asset["parent_content"],
        })
        if not parent_id:
            raise RuntimeError("XiaoShiLiu parent comment not found: " + asset["parent_content"])
    existing = find_comment_id(asset)
    if not existing:
        exec_sql(
            "insert into comments (post_id, user_id, parent_id, content, created_at) values ("
            + str(post_id) + ", " + str(author_id) + ", " + (str(parent_id) if parent_id else "NULL") + ", " + q(asset["content"]) + ", " + ts(asset.get("created_at_ms")) + ")"
        )
    elif asset.get("created_at_ms") is not None:
        exec_sql("update comments set created_at = " + ts(asset.get("created_at_ms")) + " where id = " + str(existing))
    recompute_post_counts(post_id)


def apply_like(asset):
    ensure_user(asset["user_id"])
    target_type, target_id, post_id = resolve_target(asset)
    user_db_id = user_id_for(asset["user_id"])
    if not target_id:
        raise RuntimeError("XiaoShiLiu like target not found")
    exec_sql(
        "insert ignore into likes (user_id, target_type, target_id) values ("
        + str(user_db_id) + ", " + str(target_type) + ", " + str(target_id) + ")"
    )
    if post_id:
        recompute_post_counts(post_id)
        author_id = int(scalar("select user_id from posts where id = " + str(post_id)))
        recompute_user_counts(author_id)
    if target_type == 2:
        exec_sql("update comments set like_count = (select count(*) from likes where target_type = 2 and target_id = " + str(target_id) + ") where id = " + str(target_id))


def apply_collection(asset):
    ensure_user(asset["user_id"])
    post_id = find_post_id(asset["post_title"], asset["post_author_user_id"])
    if not post_id:
        raise RuntimeError("XiaoShiLiu collection post not found: " + asset["post_title"])
    user_db_id = user_id_for(asset["user_id"])
    exec_sql("insert ignore into collections (user_id, post_id) values (" + str(user_db_id) + ", " + str(post_id) + ")")
    recompute_post_counts(post_id)


def apply_follow(asset):
    follower_id = ensure_user(asset["follower_user_id"])
    following_id = ensure_user(asset["following_user_id"])
    exec_sql("insert ignore into follows (follower_id, following_id) values (" + str(follower_id) + ", " + str(following_id) + ")")
    recompute_user_counts(follower_id)
    recompute_user_counts(following_id)


def apply_notification(asset):
    receiver_id = ensure_user(asset["user_id"])
    sender_id = ensure_user(asset["sender_user_id"])
    notification_type = NOTIFICATION_TYPE[asset["notification_type"]]
    target_id = None
    comment_id = None
    if asset.get("post_title") and asset.get("post_author_user_id"):
        target_id = find_post_id(asset["post_title"], asset["post_author_user_id"])
    if asset.get("comment_content") and asset.get("comment_author_user_id"):
        comment_id = find_comment_id({
            "post_title": asset.get("post_title"),
            "post_author_user_id": asset.get("post_author_user_id"),
            "author_user_id": asset.get("comment_author_user_id"),
            "content": asset.get("comment_content"),
        })
    title = asset.get("title") or "Asset seeded notification"
    where = (
        "user_id = " + str(receiver_id)
        + " and sender_id = " + str(sender_id)
        + " and type = " + str(notification_type)
        + " and title = " + q(title)
        + " and " + ("target_id is null" if target_id is None else "target_id = " + str(target_id))
        + " and " + ("comment_id is null" if comment_id is None else "comment_id = " + str(comment_id))
    )
    existing = scalar("select id from notifications where " + where + " order by id desc limit 1")
    if existing:
        exec_sql(
            "update notifications set is_read = " + b(asset.get("is_read"))
            + (", created_at = " + ts(asset.get("created_at_ms")) if asset.get("created_at_ms") is not None else "")
            + " where id = " + existing
        )
    else:
        exec_sql(
            "insert into notifications (user_id, sender_id, type, title, target_id, comment_id, is_read, created_at) values ("
            + str(receiver_id) + ", " + str(sender_id) + ", " + str(notification_type) + ", " + q(title) + ", "
            + (str(target_id) if target_id is not None else "NULL") + ", "
            + (str(comment_id) if comment_id is not None else "NULL") + ", " + b(asset.get("is_read")) + ", " + ts(asset.get("created_at_ms")) + ")"
        )


def apply_asset(asset):
    kind = asset["kind"]
    if kind == "xiaoshiliu_user":
        apply_user(asset)
    elif kind == "xiaoshiliu_post":
        apply_post(asset)
    elif kind == "xiaoshiliu_comment":
        apply_comment(asset)
    elif kind == "xiaoshiliu_like":
        apply_like(asset)
    elif kind == "xiaoshiliu_collection":
        apply_collection(asset)
    elif kind == "xiaoshiliu_follow":
        apply_follow(asset)
    elif kind == "xiaoshiliu_notification":
        apply_notification(asset)
    else:
        raise RuntimeError("Unsupported XiaoShiLiu asset kind: " + kind)


def user_current(asset):
    data = rows(
        "select id, user_id, nickname, email, avatar, bio, location, gender, zodiac_sign, mbti, education, major, "
        "coalesce(json_unquote(json_extract(interests, '$')), '[]'), verified, is_active, follow_count, fans_count, like_count "
        "from users where user_id = " + q(asset["user_id"]) + " limit 1"
    )
    if not data:
        return None
    row = data[0]
    try:
        interests = json.loads(row[12] or "[]")
    except Exception:
        interests = []
    return {
        "id": int(row[0]),
        "user_id": row[1],
        "nickname": row[2],
        "email": row[3] or None,
        "avatar": row[4] or None,
        "bio": row[5] or None,
        "location": row[6] or None,
        "gender": row[7] or None,
        "zodiac_sign": row[8] or None,
        "mbti": row[9] or None,
        "education": row[10] or None,
        "major": row[11] or None,
        "interests": interests,
        "verified": row[13] == "1",
        "is_active": row[14] == "1",
        "follow_count": int(row[15] or 0),
        "fans_count": int(row[16] or 0),
        "like_count": int(row[17] or 0),
    }


def post_current(asset):
    post_id = find_post_id(asset["title"], asset["author_user_id"])
    if not post_id:
        return None
    ensure_post_schema()
    data = rows(
        "select p.id, u.user_id, p.title, p.content, coalesce(c.name, ''), coalesce(c.category_title, ''), p.type, p.status, "
        "p.like_count, p.collect_count, p.comment_count, p.share_count, round(unix_timestamp(p.created_at) * 1000) "
        "from posts p join users u on u.id = p.user_id left join categories c on c.id = p.category_id "
        "where p.id = " + str(post_id)
    )[0]
    images = [row[0] for row in rows("select image_url from post_images where post_id = " + str(post_id) + " order by id")]
    videos = rows("select cover_url, video_url from post_videos where post_id = " + str(post_id) + " order by id")
    tags = [row[0] for row in rows("select t.name from post_tags pt join tags t on t.id = pt.tag_id where pt.post_id = " + str(post_id) + " order by t.name")]
    return {
        "id": int(data[0]),
        "author_user_id": data[1],
        "title": data[2],
        "content": data[3],
        "category": data[4] or data[5] or None,
        "category_title": data[5] or None,
        "post_type": POST_TYPE_REV.get(int(data[6] or 1), "image"),
        "status": STATUS_REV.get(int(data[7] or 0), "published"),
        "image_urls": images,
        "video": {"cover_url": videos[0][0], "video_url": videos[0][1]} if videos else None,
        "tags": tags,
        "like_count": int(data[8] or 0),
        "collect_count": int(data[9] or 0),
        "comment_count": int(data[10] or 0),
        "share_count": int(data[11] or 0),
        "created_at_ms": int(float(data[12] or 0)),
    }


def comment_current(asset):
    comment_id = find_comment_id(asset)
    if not comment_id:
        return None
    data = rows(
        "select c.id, u.user_id, c.content, c.parent_id, c.like_count, p.title, round(unix_timestamp(c.created_at) * 1000) "
        "from comments c join users u on u.id = c.user_id join posts p on p.id = c.post_id where c.id = " + str(comment_id)
    )[0]
    return {
        "id": int(data[0]),
        "author_user_id": data[1],
        "content": data[2],
        "parent_id": int(data[3]) if data[3] else None,
        "like_count": int(data[4] or 0),
        "post_title": data[5],
        "created_at_ms": int(float(data[6] or 0)),
    }


def like_current(asset):
    target_type, target_id, post_id = resolve_target(asset)
    user_db_id = user_id_for(asset["user_id"])
    if not target_id or not user_db_id:
        return None
    value = scalar(
        "select id from likes where user_id = " + str(user_db_id)
        + " and target_type = " + str(target_type)
        + " and target_id = " + str(target_id)
        + " limit 1"
    )
    if not value:
        return None
    return {"id": int(value), "user_id": asset["user_id"], "target_type": asset.get("target_type", "post"), "target_id": target_id, "post_id": post_id}


def collection_current(asset):
    user_db_id = user_id_for(asset["user_id"])
    post_id = find_post_id(asset["post_title"], asset["post_author_user_id"])
    if not user_db_id or not post_id:
        return None
    value = scalar("select id from collections where user_id = " + str(user_db_id) + " and post_id = " + str(post_id) + " limit 1")
    if not value:
        return None
    return {"id": int(value), "user_id": asset["user_id"], "post_id": post_id}


def follow_current(asset):
    follower_id = user_id_for(asset["follower_user_id"])
    following_id = user_id_for(asset["following_user_id"])
    if not follower_id or not following_id:
        return None
    value = scalar("select id from follows where follower_id = " + str(follower_id) + " and following_id = " + str(following_id) + " limit 1")
    if not value:
        return None
    return {"id": int(value), "follower_user_id": asset["follower_user_id"], "following_user_id": asset["following_user_id"]}


def notification_current(asset):
    receiver_id = user_id_for(asset["user_id"])
    sender_id = user_id_for(asset["sender_user_id"])
    if not receiver_id or not sender_id:
        return None
    notification_type = NOTIFICATION_TYPE[asset["notification_type"]]
    clauses = [
        "user_id = " + str(receiver_id),
        "sender_id = " + str(sender_id),
        "type = " + str(notification_type),
    ]
    if asset.get("title"):
        clauses.append("title = " + q(asset["title"]))
    if asset.get("post_title") and asset.get("post_author_user_id"):
        post_id = find_post_id(asset["post_title"], asset["post_author_user_id"])
        if not post_id:
            return None
        clauses.append("target_id = " + str(post_id))
    if asset.get("comment_content") and asset.get("comment_author_user_id"):
        comment_id = find_comment_id({
            "post_title": asset.get("post_title"),
            "post_author_user_id": asset.get("post_author_user_id"),
            "author_user_id": asset.get("comment_author_user_id"),
            "content": asset.get("comment_content"),
        })
        if not comment_id:
            return None
        clauses.append("comment_id = " + str(comment_id))
    data = rows("select id, title, is_read, target_id, comment_id, round(unix_timestamp(created_at) * 1000) from notifications where " + " and ".join(clauses) + " order by id desc limit 1")
    if not data:
        return None
    row = data[0]
    return {
        "id": int(row[0]),
        "user_id": asset["user_id"],
        "sender_user_id": asset["sender_user_id"],
        "notification_type": asset["notification_type"],
        "title": row[1],
        "is_read": row[2] == "1",
        "target_id": int(row[3]) if row[3] else None,
        "comment_id": int(row[4]) if row[4] else None,
        "created_at_ms": int(float(row[5] or 0)),
    }


def exact_user(asset, current):
    checks = {
        "user_id": asset["user_id"],
        "nickname": asset.get("nickname") or asset["user_id"],
        "email": asset.get("email") or asset["user_id"] + "@example.com",
        "avatar": asset.get("avatar") or DEFAULT_AVATAR,
        "verified": bool(asset.get("verified")),
        "is_active": bool(asset.get("is_active", True)),
    }
    optional = ["bio", "location", "gender", "zodiac_sign", "mbti", "education", "major"]
    for key in optional:
        if asset.get(key) is not None:
            checks[key] = asset.get(key)
    if asset.get("interests"):
        checks["interests"] = asset.get("interests")
    return all(current.get(key) == value for key, value in checks.items())


def exact_post(asset, current):
    if current.get("author_user_id") != asset["author_user_id"]:
        return False
    if not text_equal(current.get("title"), asset["title"]) or not text_equal(current.get("content"), asset.get("content")):
        return False
    if current.get("post_type") != asset.get("post_type", "image") or current.get("status") != asset.get("status", "published"):
        return False
    if asset.get("category") and asset.get("category") not in {current.get("category"), current.get("category_title")}:
        return False
    if asset.get("tags") and sorted(asset.get("tags")) != current.get("tags"):
        return False
    if asset.get("image_urls") and asset.get("image_urls") != current.get("image_urls"):
        return False
    min_image_count = int(asset.get("min_image_count") or 0)
    if min_image_count and len(current.get("image_urls") or []) < min_image_count:
        return False
    if asset.get("post_type") == "video":
        video = current.get("video") or {}
        if video.get("video_url") != asset.get("video_url"):
            return False
        if asset.get("cover_url") and video.get("cover_url") != asset.get("cover_url"):
            return False
    if asset.get("created_at_ms") is not None and abs(current.get("created_at_ms", 0) - int(asset["created_at_ms"])) > 1000:
        return False
    if current.get("share_count", 0) != int(asset.get("share_count") or 0):
        return False
    return True


def exact_notification(asset, current):
    if current.get("is_read") != bool(asset.get("is_read")):
        return False
    if asset.get("title") and current.get("title") != asset.get("title"):
        return False
    if asset.get("created_at_ms") is not None and abs(current.get("created_at_ms", 0) - int(asset["created_at_ms"])) > 1000:
        return False
    return True


def probe_asset(asset):
    kind = asset["kind"]
    if kind == "xiaoshiliu_user":
        current = user_current(asset)
        exact = bool(current and exact_user(asset, current))
        label = "xiaoshiliu_user:" + asset["user_id"]
    elif kind == "xiaoshiliu_post":
        current = post_current(asset)
        if current and asset.get("expected_images"):
            current["image_contents"] = image_contents(current.get("image_urls") or [])
        exact = bool(current and exact_post(asset, current))
        label = "xiaoshiliu_post:" + asset["title"]
    elif kind == "xiaoshiliu_comment":
        current = comment_current(asset)
        exact = bool(current and text_equal(current.get("content"), asset["content"]) and current.get("author_user_id") == asset["author_user_id"] and (asset.get("created_at_ms") is None or abs(current.get("created_at_ms", 0) - int(asset["created_at_ms"])) <= 1000))
        label = "xiaoshiliu_comment:" + asset["content"]
    elif kind == "xiaoshiliu_like":
        current = like_current(asset)
        exact = current is not None
        label = "xiaoshiliu_like:" + asset["user_id"]
    elif kind == "xiaoshiliu_collection":
        current = collection_current(asset)
        exact = current is not None
        label = "xiaoshiliu_collection:" + asset["user_id"]
    elif kind == "xiaoshiliu_follow":
        current = follow_current(asset)
        exact = current is not None
        label = "xiaoshiliu_follow:" + asset["follower_user_id"] + "->" + asset["following_user_id"]
    elif kind == "xiaoshiliu_notification":
        current = notification_current(asset)
        exact = bool(current and exact_notification(asset, current))
        label = "xiaoshiliu_notification:" + asset["notification_type"]
    else:
        raise RuntimeError("Unsupported XiaoShiLiu asset kind: " + kind)
    return {"label": label, "identity_exists": current is not None, "exact_match": exact, "current": current}
'''


def _asset_data(asset: Any) -> dict[str, Any]:
    if hasattr(asset, "model_dump"):
        return asset.model_dump()
    return dict(asset)


def _payload(asset: Any) -> str:
    data = _asset_data(asset)
    raw = json.dumps(data, ensure_ascii=False).encode("utf-8")
    return base64.b64encode(raw).decode("ascii")


def _run_asset_script(client: AndroidController, asset: Any, action: str, *, timeout: float = 120.0) -> str:
    payload = _payload(asset)
    script = f"""
set -euo pipefail
python3 - <<'INNER_PY'
import base64
import json
{_RUNTIME}
asset = json.loads(base64.b64decode({payload!r}).decode('utf-8'))
if {action!r} == 'apply':
    apply_asset(asset)
else:
    print(json.dumps(probe_asset(asset), ensure_ascii=False))
INNER_PY
"""
    return run_bash(client, script, timeout=timeout)


def ensure_xiaoshiliu_backend(client: AndroidController) -> None:
    _ensure_xiaoshiliu_backend(client)


def xiaoshiliu_login_user_asset(
    *,
    user_id: str = XIAOSHILIU_LOGIN_USER_ID,
    password: str = XIAOSHILIU_LOGIN_PASSWORD,
    nickname: str = XIAOSHILIU_LOGIN_NICKNAME,
    email: str = XIAOSHILIU_LOGIN_EMAIL,
) -> dict[str, Any]:
    return {
        "kind": "xiaoshiliu_user",
        "app": "XiaoShiLiu",
        "user_id": user_id,
        "password": password,
        "nickname": nickname,
        "email": email,
        "avatar": XIAOSHILIU_DEFAULT_AVATAR,
        "bio": "Default owner account.",
        "verified": False,
        "is_active": True,
    }


def ensure_xiaoshiliu_login_user(
    client: AndroidController,
    *,
    user_id: str = XIAOSHILIU_LOGIN_USER_ID,
    password: str = XIAOSHILIU_LOGIN_PASSWORD,
    nickname: str | None = XIAOSHILIU_LOGIN_NICKNAME,
    email: str | None = XIAOSHILIU_LOGIN_EMAIL,
) -> None:
    ensure_xiaoshiliu_backend(client)
    _run_asset_script(
        client,
        xiaoshiliu_login_user_asset(
            user_id=user_id,
            password=password,
            nickname=nickname or user_id,
            email=email or f"{user_id}@example.com",
        ),
        "apply",
        timeout=120,
    )


def login_xiaoshiliu_app(
    client: AndroidController,
    *,
    user_id: str = XIAOSHILIU_LOGIN_USER_ID,
    password: str = XIAOSHILIU_LOGIN_PASSWORD,
    ensure_user: bool = True,
) -> None:
    if ensure_user:
        nickname = XIAOSHILIU_LOGIN_NICKNAME if user_id == XIAOSHILIU_LOGIN_USER_ID else user_id
        email = XIAOSHILIU_LOGIN_EMAIL if user_id == XIAOSHILIU_LOGIN_USER_ID else f"{user_id}@example.com"
        ensure_xiaoshiliu_login_user(client, user_id=user_id, password=password, nickname=nickname, email=email)
    device_arg = shlex.quote(getattr(client, "device", "emulator-5554"))
    run_bash(
        client,
        f"""
set -eu
adb -s {device_arg} shell am force-stop gma.webapp.xiaoshiliu >/dev/null 2>&1 || true
adb -s {device_arg} shell pm clear gma.webapp.xiaoshiliu >/dev/null 2>&1 || true
""",
        timeout=30,
    )
    launch_webapp_with_login_extras(
        client,
        "gma.webapp.xiaoshiliu",
        user_id=user_id,
        password=password,
    )
    _sync_xiaoshiliu_frontend_session(client, user_id=user_id, password=password)


def _sync_xiaoshiliu_frontend_session(
    client: AndroidController,
    *,
    user_id: str,
    password: str,
) -> None:
    payload = base64.b64encode(
        json.dumps(
            {
                "device": getattr(client, "device", "emulator-5554"),
                "user_id": user_id,
                "password": password,
            }
        ).encode("utf-8")
    ).decode("ascii")
    script = r'''
set -eu
PYTHON_BIN=/app/gma/.venv/bin/python3
if [ ! -x "$PYTHON_BIN" ]; then PYTHON_BIN=python3; fi
"$PYTHON_BIN" - <<'INNER_PY'
import asyncio
import base64
import json
import subprocess
import time
import urllib.request

import websockets

config = json.loads(base64.b64decode("__PAYLOAD__").decode("utf-8"))
device = config["device"]
port = "9236"
page_list_url = "http://127.0.0.1:" + port + "/json"


def adb(*args, check=True, **kwargs):
    return subprocess.run(["adb", "-s", device, *args], check=check, **kwargs)


def sql_quote(value):
    return "'" + str(value).replace("\\", "\\\\").replace("'", "''") + "'"


subprocess.run(
    [
        "docker",
        "exec",
        "-i",
        "xiaoshiliu-mysql",
        "mysql",
        "-uxiaoshiliu_user",
        "-p123456",
        "xiaoshiliu",
        "-e",
        "DELETE FROM user_sessions WHERE user_id=(SELECT id FROM users WHERE user_id=" + sql_quote(config["user_id"]) + ");",
    ],
    check=True,
    stdout=subprocess.DEVNULL,
)

login_request = urllib.request.Request(
    "http://localhost:8031/api/auth/login",
    data=json.dumps({"user_id": config["user_id"], "password": config["password"]}).encode("utf-8"),
    headers={"Content-Type": "application/json"},
    method="POST",
)
with urllib.request.urlopen(login_request, timeout=20) as response:
    login_payload = json.loads(response.read().decode("utf-8"))
if not login_payload or login_payload.get("code") != 200 or not login_payload.get("data", {}).get("tokens"):
    raise RuntimeError("XiaoShiLiu backend login failed: " + json.dumps(login_payload, ensure_ascii=False))

adb("shell", "monkey", "-p", "gma.webapp.xiaoshiliu", "-c", "android.intent.category.LAUNCHER", "1", stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)

pid = ""
deadline = time.time() + 25
while time.time() < deadline:
    result = adb("shell", "pidof", "gma.webapp.xiaoshiliu", check=False, capture_output=True, text=True, timeout=10)
    pid = (result.stdout or "").strip().split()
    pid = pid[0] if pid else ""
    if pid:
        break
    time.sleep(1)
if not pid:
    raise RuntimeError("XiaoShiLiu WebView package did not start")

adb("forward", "--remove", "tcp:" + port, check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
adb("forward", "tcp:" + port, "localabstract:webview_devtools_remote_" + pid, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def list_pages():
    with urllib.request.urlopen(page_list_url, timeout=5) as response:
        pages = json.loads(response.read().decode("utf-8"))
    return [page for page in pages if page.get("type") == "page" and page.get("webSocketDebuggerUrl")]


def get_page():
    deadline = time.time() + 20
    last = None
    while time.time() < deadline:
        try:
            pages = list_pages()
            last = pages
            page = next((item for item in pages if (item.get("url") or "").startswith("http://10.0.2.2:8030")), None)
            if not page and pages:
                page = pages[0]
            if page:
                return page
        except Exception as exc:
            last = repr(exc)
        time.sleep(1)
    raise RuntimeError("Could not attach to XiaoShiLiu WebView page: " + repr(last))


async def call_cdp(websocket, message_id, method, params=None, timeout=20):
    await websocket.send(json.dumps({"id": message_id, "method": method, "params": params or {}}))
    deadline = time.time() + timeout
    while time.time() < deadline:
        message = json.loads(await asyncio.wait_for(websocket.recv(), timeout=max(0.5, deadline - time.time())))
        if message.get("id") != message_id:
            continue
        if "error" in message:
            raise RuntimeError(message["error"])
        return message
    raise RuntimeError(f"Timed out waiting for CDP response to {method}")


def unwrap_runtime_value(response):
    result = response.get("result", {})
    if "exceptionDetails" in result:
        raise RuntimeError(result["exceptionDetails"])
    value = result.get("result", {})
    if value.get("subtype") == "error":
        raise RuntimeError(value)
    return value.get("value")


async def evaluate(websocket, message_id, expression, *, timeout=20):
    response = await call_cdp(
        websocket,
        message_id,
        "Runtime.evaluate",
        {"expression": expression, "returnByValue": True, "awaitPromise": True},
        timeout=timeout,
    )
    return unwrap_runtime_value(response)


async def navigate(websocket, message_id, url, *, timeout=20):
    await call_cdp(websocket, message_id, "Page.navigate", {"url": url}, timeout=timeout)


async def wait_until_interactive(websocket, start_message_id, *, timeout=20):
    message_id = start_message_id
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            ready_state = await evaluate(websocket, message_id, "document.readyState", timeout=5)
            if ready_state in ("interactive", "complete"):
                return message_id + 1
        except Exception:
            pass
        message_id += 1
        await asyncio.sleep(1)
    return message_id


login_script = """
(async function () {
  const userId = USER_ID_PLACEHOLDER;
  const password = PASSWORD_PLACEHOLDER;
  const response = await fetch('/api/auth/login', {
    method: 'POST',
    credentials: 'include',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({user_id: userId, password})
  });
  const payload = await response.json();
  if (!payload || payload.code !== 200 || !payload.data || !payload.data.tokens) {
    throw new Error('XiaoShiLiu browser login failed: ' + JSON.stringify(payload));
  }
  localStorage.setItem('token', payload.data.tokens.access_token);
  localStorage.setItem('refreshToken', payload.data.tokens.refresh_token);
  localStorage.setItem('userInfo', JSON.stringify(payload.data.user));
  localStorage.setItem('GMA-XSL-Seed-User', userId);
  return {user_id: payload.data.user.user_id, token: !!payload.data.tokens.access_token};
})()
"""
login_script = login_script.replace("USER_ID_PLACEHOLDER", json.dumps(config["user_id"]))
login_script = login_script.replace("PASSWORD_PLACEHOLDER", json.dumps(config["password"]))

state_expression = """
JSON.stringify({
  href: location.href,
  marker: localStorage.getItem('GMA-XSL-Seed-User'),
  token: !!localStorage.getItem('token'),
  userInfo: JSON.parse(localStorage.getItem('userInfo') || '{}'),
  text: document.body ? document.body.innerText.slice(0, 2000) : ''
})
"""

async def sync_frontend_session():
    page = get_page()
    websocket_url = page["webSocketDebuggerUrl"]
    last = None
    async with websockets.connect(websocket_url, max_size=None) as websocket:
        message_id = 1
        await call_cdp(websocket, message_id, "Page.enable")
        message_id += 1
        await call_cdp(websocket, message_id, "Runtime.enable")
        message_id += 1
        await call_cdp(
            websocket,
            message_id,
            "Page.addScriptToEvaluateOnNewDocument",
            {"source": login_script},
        )
        message_id += 1
        await navigate(websocket, message_id, "http://10.0.2.2:8030/user", timeout=20)
        message_id += 1
        message_id = await wait_until_interactive(websocket, message_id, timeout=20)
        login_result = await evaluate(websocket, message_id, login_script, timeout=30)
        message_id += 1
        raw_after_login = await evaluate(websocket, message_id, state_expression, timeout=10) or "{}"
        message_id += 1
        after_login = json.loads(raw_after_login)
        initial_state = {"login_result": login_result, "after_login": after_login}
        last = initial_state
        current = (after_login.get("userInfo") or {}).get("user_id")
        if (
            after_login.get("token")
            and after_login.get("marker") == config["user_id"]
            and current == config["user_id"]
            and str(after_login.get("href") or "").startswith("http://10.0.2.2:8030")
            and "Please log in" not in (after_login.get("text") or "")
        ):
            return after_login

        for _ in range(20):
            await asyncio.sleep(1)
            try:
                raw = await evaluate(websocket, message_id, state_expression, timeout=10) or "{}"
                message_id += 1
                last = json.loads(raw)
                current = (last.get("userInfo") or {}).get("user_id")
                if last.get("token") and last.get("marker") == config["user_id"] and current == config["user_id"]:
                    if str(last.get("href") or "").startswith("http://10.0.2.2:8030") and "Please log in" not in (last.get("text") or ""):
                        return last
            except Exception as exc:
                last = {"error": repr(exc)}
                message_id += 1
    raise RuntimeError("XiaoShiLiu frontend login verification failed: " + json.dumps({"initial": initial_state, "last": last}, ensure_ascii=False))


last_error = None
for _ in range(3):
    try:
        final_state = asyncio.run(sync_frontend_session())
        print(json.dumps(final_state, ensure_ascii=False))
        raise SystemExit(0)
    except Exception as exc:
        last_error = exc
        time.sleep(2)

raise RuntimeError(str(last_error))
INNER_PY
'''.replace("__PAYLOAD__", payload)
    run_bash(client, script, timeout=90)



def _task_local_frontend_image(task_root: Path | None, image_url: str) -> tuple[Path, str] | None:
    if task_root is None or not image_url:
        return None
    parsed = urlparse(str(image_url))
    if parsed.scheme or parsed.netloc:
        return None
    frontend_path = unquote(parsed.path)
    if not frontend_path.startswith("/assets/"):
        return None
    relative = frontend_path.removeprefix("/assets/")
    relative_path = Path(relative)
    if relative_path.is_absolute() or any(part in ("", ".", "..") for part in relative_path.parts):
        return None
    assets_dir = (task_root / "assets").resolve()
    source_path = (assets_dir / relative_path).resolve()
    try:
        source_path.relative_to(assets_dir)
    except ValueError:
        return None
    if not source_path.is_file():
        return None
    target_path = posixpath.normpath("/usr/share/nginx/html" + frontend_path)
    if not target_path.startswith("/usr/share/nginx/html/assets/"):
        return None
    return source_path, target_path


def _copy_xiaoshiliu_frontend_image(client: AndroidController, source_path: Path, target_path: str) -> None:
    payload = base64.b64encode(source_path.read_bytes()).decode("ascii")
    digest = hashlib.sha256(target_path.encode("utf-8")).hexdigest()[:16]
    temp_b64 = f"/tmp/gma_xiaoshiliu_asset_{digest}.b64"
    temp_file = f"/tmp/gma_xiaoshiliu_asset_{digest}"
    run_bash(client, f": > {shlex.quote(temp_b64)}", timeout=30)
    for start in range(0, len(payload), 60000):
        chunk = payload[start:start + 60000]
        run_bash(
            client,
            "\n".join(
                [
                    f"cat <<'__GMA_XSL_IMAGE_B64__' >> {shlex.quote(temp_b64)}",
                    chunk,
                    "__GMA_XSL_IMAGE_B64__",
                ]
            ),
            timeout=30,
        )
    target_dir = posixpath.dirname(target_path)
    run_bash(
        client,
        "\n".join(
            [
                "set -euo pipefail",
                f"base64 -d {shlex.quote(temp_b64)} > {shlex.quote(temp_file)}",
                f"docker exec xiaoshiliu-frontend mkdir -p {shlex.quote(target_dir)}",
                f"docker cp {shlex.quote(temp_file)} xiaoshiliu-frontend:{shlex.quote(target_path)}",
                f"rm -f {shlex.quote(temp_b64)} {shlex.quote(temp_file)}",
            ]
        ),
        timeout=60,
    )


def install_xiaoshiliu_frontend_images(
    client: AndroidController,
    task_root: Path | None,
    image_urls: list[str] | tuple[str, ...] | None,
) -> None:
    if not task_root or not image_urls:
        return
    seen: set[str] = set()
    for image_url in image_urls:
        image = _task_local_frontend_image(task_root, image_url)
        if image is None:
            continue
        source_path, target_path = image
        if target_path in seen:
            continue
        seen.add(target_path)
        _copy_xiaoshiliu_frontend_image(client, source_path, target_path)

def apply_xiaoshiliu_asset(client: AndroidController, asset: Any, task_root: Path | None = None) -> None:
    ensure_xiaoshiliu_backend(client)
    data = _asset_data(asset)
    if data.get("kind") == "xiaoshiliu_post":
        install_xiaoshiliu_frontend_images(client, task_root, data.get("image_urls"))
    _run_asset_script(client, asset, "apply", timeout=120)


def probe_xiaoshiliu_asset(client: AndroidController, asset: Any) -> dict[str, Any]:
    ensure_xiaoshiliu_backend(client)
    output = _run_asset_script(client, asset, "probe", timeout=120)
    return json.loads(output)
