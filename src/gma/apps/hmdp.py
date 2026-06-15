from __future__ import annotations

import base64
import json
from typing import TYPE_CHECKING, Any

from gma.apps._shell import launch_webapp_with_login_extras, run_bash
from gma.apps.offline_webapps import ensure_hmdp_backend as _ensure_hmdp_backend

if TYPE_CHECKING:
    from gma.runtime.controller import AndroidController

HMDP_WEB_URL = "http://10.0.2.2:8070/hmdp/"
HMDP_LOGIN_PHONE = "13810246820"
HMDP_LOGIN_PASSWORD = "123456"
HMDP_LOGIN_NICKNAME = "owner"
HMDP_DEFAULT_ICON = "/hmdp/src/assets/imgs/icons/default-icon.png"
HMDP_DEFAULT_IMAGE = "/hmdp/yelp-photos/G5G4GbnmovFSdvdC3PoFHw.jpg"

_RUNTIME = r'''
import base64, hashlib, json, random, subprocess, time, urllib.request

MYSQL = ["docker", "exec", "-i", "hmdp-mysql", "mysql", "-uroot", "-phmdp_root_2025", "--default-character-set=utf8mb4"]
QUERY = MYSQL + ["--batch", "--raw", "--skip-column-names"]
DBS = ("hmdp_0", "hmdp_1")
DEFAULT_IMAGE = "/hmdp/yelp-photos/G5G4GbnmovFSdvdC3PoFHw.jpg"
DEFAULT_ICON = "/hmdp/src/assets/imgs/icons/default-icon.png"
SALT = "gma_hmdp_asset_salt"

def q(v):
    if v is None:
        return "NULL"
    return "'" + str(v).replace("\\", "\\\\").replace("'", "''").replace("\0", "") + "'"

def text_equal(a, b):
    if isinstance(a, str) and isinstance(b, str):
        return a.strip() == b.strip()
    return a == b

def dt(value_ms):
    if value_ms is None:
        return "CURRENT_TIMESTAMP"
    return "FROM_UNIXTIME(" + str(int(value_ms) / 1000.0) + ")"

def exec_sql(db, sql):
    subprocess.run(MYSQL + [db], input=sql, text=True, check=True)

def rows(db, sql):
    out = subprocess.check_output(QUERY + [db, "-e", sql], text=True)
    return [["" if c == "NULL" else c for c in line.split("\t")] for line in out.splitlines() if line.strip()]

def scalar(db, sql):
    data = rows(db, sql)
    return data[0][0] if data and data[0] else None

def rows_all(sql):
    out = []
    for db in DBS:
        out.extend((db, r) for r in rows(db, sql))
    return out

def scalar_all(sql):
    for db in DBS:
        value = scalar(db, sql)
        if value not in (None, ""):
            return value
    return None

def is_image_bytes(raw, content_type=None):
    if not raw:
        return False
    content_type = (content_type or "").split(";", 1)[0].strip().lower()
    if content_type.startswith("image/"):
        return True
    if content_type in ("text/html", "application/json", "text/plain"):
        return False
    return (
        raw.startswith(b"\x89PNG\r\n\x1a\n")
        or raw.startswith(b"\xff\xd8\xff")
        or raw.startswith(b"GIF87a")
        or raw.startswith(b"GIF89a")
        or raw.startswith(b"RIFF") and raw[8:12] == b"WEBP"
        or raw.startswith(b"BM")
    )

def hmdp_upload_paths(path):
    paths = []
    if path.startswith("/hmdp/imgs/"):
        paths.append("/app/uploads/" + path[len("/hmdp/imgs/"):])
    if path.startswith("/imgs/"):
        paths.append("/app/uploads/" + path[len("/imgs/"):])
    if path.startswith("/uploads/"):
        paths.append("/app" + path)
    return paths

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
        candidates.append("http://127.0.0.1:8070" + path)
        if not path.startswith("/hmdp/"):
            candidates.append("http://127.0.0.1:8070/hmdp" + path)
        candidates.append("http://127.0.0.1:8071" + path)
    seen = set()
    errors = []
    for candidate in candidates:
        if candidate in seen:
            continue
        seen.add(candidate)
        try:
            with urllib.request.urlopen(candidate, timeout=10) as response:
                raw = response.read()
                content_type = response.headers.get("Content-Type", "")
                if is_image_bytes(raw, content_type):
                    return raw, None
                errors.append(f"{candidate}: non-image response ({content_type or 'unknown content type'})")
        except Exception as exc:
            errors.append(f"{candidate}: {type(exc).__name__}")
    if value.startswith("/"):
        container_paths = []
        path = value if value.startswith("/") else "/" + value
        for upload_path in hmdp_upload_paths(path):
            container_paths.append(("hmdp-backend", upload_path))
        container_paths.append(("hmdp-frontend", "/usr/share/nginx/html" + value))
        if value.startswith("/hmdp/"):
            container_paths.append(("hmdp-frontend", "/usr/share/nginx/html/" + value[len("/hmdp/"):]))
        container_paths.append(("hmdp-frontend", "/usr/share/nginx/html/hmdp" + value))
        for container, path in container_paths:
            try:
                raw = subprocess.check_output(["docker", "exec", container, "cat", path])
                if is_image_bytes(raw):
                    return raw, None
                errors.append(f"{container}:{path}: non-image bytes")
            except Exception as exc:
                errors.append(f"{container}:{path}: {type(exc).__name__}")
    return None, "image bytes not found" + (": " + "; ".join(errors) if errors else "")

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

def redis(*args):
    return subprocess.check_output(["docker", "exec", "hmdp-redis", "redis-cli", *map(str, args)], text=True).strip()

JS_SAFE_MAX = 9007199254740991

def gen_id():
    # Keep generated IDs below JavaScript's max safe integer; HMDP routes IDs through Vue.
    return int(time.time() * 1000) * 1000 + random.randint(100, 999)

def is_frontend_safe_id(value):
    try:
        value = int(value)
    except Exception:
        return False
    return 0 < value <= JS_SAFE_MAX

def seeded_shop_id(name, requested=None, current=None):
    if requested is not None and is_frontend_safe_id(requested):
        return int(requested)
    if current and is_frontend_safe_id(current.get("id")) and int(current["id"]) <= 100000:
        return int(current["id"])
    ids = []
    for _db, row in rows_all("select id,name from tb_shop where id between 1 and 100000 order by id"):
        try:
            ids.append((int(row[0]), row[1] or ""))
        except Exception:
            pass
    if not ids:
        return gen_id()
    ids = sorted({item for item in ids}, reverse=True)
    start = abs(java_hash(name)) % len(ids)
    for offset in range(len(ids)):
        candidate, owner = ids[(start + offset) % len(ids)]
        if owner == name or not owner.startswith("Asset Check HMDP"):
            return candidate
    return ids[start][0]

def java_hash(s):
    h = 0
    for ch in str(s):
        h = (31 * h + ord(ch)) & 0xFFFFFFFF
    return h - 0x100000000 if h >= 0x80000000 else h

def user_table(user_id):
    return f"hmdp_{int(user_id) % 2}", f"tb_user_{(int(user_id) // 2) % 2}"

def user_info_table(user_id):
    return f"hmdp_{int(user_id) % 2}", f"tb_user_info_{(int(user_id) // 2) % 2}"

def user_phone_table(phone):
    h = abs(java_hash(phone))
    return f"hmdp_{h % 2}", f"tb_user_phone_{(h // 2) % 2}"

def voucher_table(voucher_id):
    return f"hmdp_{int(voucher_id) % 2}", f"tb_voucher_{(int(voucher_id) // 2) % 2}"

def seckill_table(voucher_id):
    return f"hmdp_{int(voucher_id) % 2}", f"tb_seckill_voucher_{(int(voucher_id) // 2) % 2}"

def order_table(user_id, voucher_id):
    return f"hmdp_{int(user_id) % 2}", f"tb_voucher_order_{int(voucher_id) % 2}"

def password(raw):
    return SALT + "@" + hashlib.md5((raw + SALT).encode()).hexdigest()

def csv(v):
    if v is None:
        return ""
    return v if isinstance(v, str) else ",".join(v)

def user_current(phone):
    for db in DBS:
        for i in (0, 1):
            data = rows(db, f"select id, phone, password, nick_name, icon from tb_user_{i} where phone = {q(phone)} order by id limit 1")
            if data:
                r = data[0]
                info_db, info_table = user_info_table(r[0])
                info_rows = rows(info_db, f"select city, introduce, fans, followee, gender, birthday, credits, level from {info_table} where user_id = {r[0]} limit 1")
                info = None
                if info_rows:
                    x = info_rows[0]
                    info = {"city": x[0] or None, "introduce": x[1] or None, "fans": int(x[2] or 0), "followee": int(x[3] or 0), "gender": int(x[4] or 0), "birthday": x[5] or None, "credits": int(x[6] or 0), "level": int(x[7] or 0)}
                return {"id": int(r[0]), "phone": r[1], "password": r[2], "nick_name": r[3], "icon": r[4], "info": info}
    return None

def ensure_user(a):
    cur = user_current(a["phone"])
    uid = int(a.get("user_id") or (cur or {}).get("id") or gen_id())
    db, table = user_table(uid)
    fields = f"phone={q(a['phone'])}, password={q(password(a.get('password') or '123456'))}, nick_name={q(a.get('nick_name') or a.get('nickname') or a['phone'])}, icon={q(a.get('icon') or DEFAULT_ICON)}"
    if scalar(db, f"select id from {table} where id = {uid} limit 1"):
        exec_sql(db, f"update {table} set {fields} where id = {uid}")
    else:
        exec_sql(db, f"insert into {table} set id={uid}, {fields}")
    stale_user_ids = []
    for cleanup_db in DBS:
        for cleanup_i in (0, 1):
            cleanup_table = f"tb_user_{cleanup_i}"
            for row in rows(cleanup_db, f"select id from {cleanup_table} where phone = {q(a['phone'])} and id <> {uid}"):
                stale_user_ids.append(int(row[0]))
            exec_sql(cleanup_db, f"delete from {cleanup_table} where phone = {q(a['phone'])} and id <> {uid}")
    for stale_uid in stale_user_ids:
        stale_info_db, stale_info_table = user_info_table(stale_uid)
        exec_sql(stale_info_db, f"delete from {stale_info_table} where user_id = {stale_uid}")
    pdb, ptable = user_phone_table(a["phone"])
    phone_rows = rows(pdb, f"select id from {ptable} where phone = {q(a['phone'])} order by id")
    pid = phone_rows[0][0] if phone_rows else None
    if len(phone_rows) > 1:
        keep = int(pid)
        exec_sql(pdb, f"delete from {ptable} where phone = {q(a['phone'])} and id <> {keep}")
    exec_sql(pdb, f"update {ptable} set user_id={uid} where id={pid}" if pid else f"insert into {ptable} set id={gen_id()}, user_id={uid}, phone={q(a['phone'])}")
    idb, itable = user_info_table(uid)
    iid = scalar(idb, f"select id from {itable} where user_id = {uid} limit 1")
    info = f"city={q(a.get('city'))}, introduce={q(a.get('introduce'))}, fans={int(a.get('fans',0))}, followee={int(a.get('followee',0))}, gender={int(a.get('gender',0))}, birthday={q(a.get('birthday'))}, credits={int(a.get('credits',0))}, level={int(a.get('level',0))}"
    exec_sql(idb, f"update {itable} set {info} where id={iid}" if iid else f"insert into {itable} set id={gen_id()}, user_id={uid}, {info}")
    return uid

def user_id(phone):
    cur = user_current(phone)
    return cur["id"] if cur else None

def ensure_user_exists(phone):
    existing = user_id(phone)
    if existing:
        return existing
    return ensure_user({"kind": "hmdp_user", "phone": phone, "password": "123456", "nick_name": phone})

def type_id(a):
    if a.get("type_id") is not None:
        return int(a["type_id"])
    return int(scalar_all("select id from tb_shop_type where name = " + q(a.get("type_name") or "Food") + " limit 1") or 1)

def shop_current(name):
    data = rows_all("select id,name,type_id,images,area,address,x,y,avg_price,sold,comments,score,open_hours,tags from tb_shop where name = " + q(name) + " limit 1")
    if not data:
        return None
    db, r = data[0]
    return {"id": int(r[0]), "name": r[1], "type_id": int(r[2]), "type_name": scalar(db, "select name from tb_shop_type where id=" + r[2] + " limit 1"), "images": [x for x in (r[3] or "").split(",") if x], "area": r[4] or None, "address": r[5], "x": float(r[6]), "y": float(r[7]), "avg_price": int(r[8] or 0), "sold": int(r[9] or 0), "comments": int(r[10] or 0), "score": int(r[11] or 0) / 10, "open_hours": r[12] or None, "tags": [x.strip() for x in (r[13] or "").split(",") if x.strip()]}

def ensure_shop(a):
    cur = shop_current(a["name"])
    old_sid = int(cur["id"]) if cur else None
    sid = seeded_shop_id(a["name"], a.get("shop_id"), cur)
    score = float(a.get("score", 4.8))
    score_int = int(round(score * 10)) if score <= 5 else int(score)
    fields = (
        f"id={sid}, name={q(a['name'])}, type_id={type_id(a)}, "
        f"images={q(csv(a.get('images') or [DEFAULT_IMAGE]))}, "
        f"area={q(a.get('area'))}, "
        f"address={q(a.get('address') or 'Asset HMDP Address')}, "
        f"x={float(a.get('x',120.149993))}, y={float(a.get('y',30.334229))}, "
        f"avg_price={int(a.get('avg_price',50))}, sold={int(a.get('sold',0))}, "
        f"comments={int(a.get('comments',0))}, score={score_int}, "
        f"open_hours={q(a.get('open_hours') or '09:00-21:00')}, "
        f"tags={q(csv(a.get('tags') or []))}"
    )
    for db in DBS:
        existing_name = scalar(db, f"select name from tb_shop where id={sid} limit 1")
        if existing_name:
            exec_sql(db, f"delete from tb_blog where shop_id={sid}")
            exec_sql(db, f"delete from tb_shop_review where shop_id={sid}")
            exec_sql(db, f"delete from tb_shop_favorite where shop_id={sid}")
            for i in (0, 1):
                exec_sql(db, f"delete from tb_voucher_{i} where shop_id={sid}")
        if old_sid and old_sid != sid:
            exec_sql(db, f"update tb_blog set shop_id={sid} where shop_id={old_sid}")
            exec_sql(db, f"update tb_shop_review set shop_id={sid} where shop_id={old_sid}")
            exec_sql(db, f"update tb_shop_favorite set shop_id={sid} where shop_id={old_sid}")
            for i in (0, 1):
                exec_sql(db, f"update tb_voucher_{i} set shop_id={sid} where shop_id={old_sid}")
            exec_sql(db, f"delete from tb_shop where id={old_sid}")
        existing = scalar(db, f"select id from tb_shop where id={sid} limit 1")
        if existing:
            exec_sql(db, f"update tb_shop set {fields} where id={sid}")
        else:
            exec_sql(db, f"insert into tb_shop set {fields}")
    try:
        keys = ["cache:shop:" + str(sid), "hmdp-cache:shop:" + str(sid), "hmdp-cache:shop_null:" + str(sid), "lock:shop:" + str(sid)]
        if old_sid and old_sid != sid:
            keys.extend(["cache:shop:" + str(old_sid), "hmdp-cache:shop:" + str(old_sid), "hmdp-cache:shop_null:" + str(old_sid), "lock:shop:" + str(old_sid)])
        redis("DEL", *keys)
    except Exception:
        pass
    return sid

def shop_id(name):
    cur = shop_current(name)
    return cur["id"] if cur else None

def blog_current(a):
    uid = user_id(a["author_phone"])
    if not uid:
        return None
    data = rows_all(f"select id,shop_id,user_id,title,images,content,liked,comments,round(unix_timestamp(create_time)*1000) from tb_blog where user_id={uid} and title={q(a['title'])} order by create_time desc limit 1")
    if not data:
        return None
    db, r = data[0]
    return {"id": int(r[0]), "shop_id": int(r[1]), "shop_name": scalar(db, "select name from tb_shop where id=" + r[1] + " limit 1"), "author_phone": a["author_phone"], "title": r[3], "images": [x for x in (r[4] or "").split(",") if x], "content": r[5], "liked": int(r[6] or 0), "comments": int(r[7] or 0), "created_at_ms": int(float(r[8] or 0))}

def ensure_blog(a):
    uid = ensure_user_exists(a["author_phone"])
    sid = shop_id(a.get("shop_name") or "") or ensure_shop({"kind": "hmdp_shop", "name": a.get("shop_name") or "Asset HMDP Shop"})
    cur = blog_current(a)
    bid = int(a.get("blog_id") or (cur or {}).get("id") or gen_id())
    time_fields = f", create_time={dt(a.get('created_at_ms'))}, update_time={dt(a.get('created_at_ms'))}" if a.get("created_at_ms") is not None else ""
    fields = f"id={bid}, shop_id={sid}, user_id={uid}, title={q(a['title'])}, images={q(csv(a.get('images') or [DEFAULT_IMAGE]))}, content={q(a['content'])}, liked={int(a.get('liked') or 0)}, comments={int(a.get('comments') or 0)}{time_fields}"
    for db in DBS:
        existing = scalar(db, f"select id from tb_blog where user_id={uid} and title={q(a['title'])} limit 1")
        exec_sql(db, f"update tb_blog set {fields} where id={existing}" if existing else f"insert into tb_blog set {fields}")
    return bid

def blog_id(title, author_phone):
    cur = blog_current({"title": title, "author_phone": author_phone})
    return cur["id"] if cur else None

def comment_current(a):
    bid = blog_id(a["blog_title"], a["blog_author_phone"]); uid = user_id(a["author_phone"])
    if not bid or not uid:
        return None
    data = rows_all(f"select id,user_id,blog_id,parent_id,answer_id,content,liked,status,round(unix_timestamp(create_time)*1000) from tb_blog_comments where blog_id={bid} and user_id={uid} and content={q(a['content'])} order by create_time desc limit 1")
    if not data:
        return None
    r = data[0][1]
    return {"id": int(r[0]), "author_phone": a["author_phone"], "blog_title": a["blog_title"], "blog_author_phone": a["blog_author_phone"], "content": r[5], "liked": int(r[6] or 0), "status": int(r[7] or 0), "created_at_ms": int(float(r[8] or 0))}

def ensure_comment(a):
    bid = blog_id(a["blog_title"], a["blog_author_phone"])
    if not bid:
        raise RuntimeError("HMDP blog not found: " + a["blog_title"])
    uid = ensure_user_exists(a["author_phone"])
    cur = comment_current(a); cid = int(a.get("comment_id") or (cur or {}).get("id") or gen_id())
    time_fields = f", create_time={dt(a.get('created_at_ms'))}, update_time={dt(a.get('created_at_ms'))}" if a.get("created_at_ms") is not None else ""
    fields = f"id={cid}, user_id={uid}, blog_id={bid}, parent_id=0, answer_id=0, content={q(a['content'])}, liked={int(a.get('liked',0))}, status={int(a.get('status',0))}{time_fields}"
    for db in DBS:
        existing = scalar(db, f"select id from tb_blog_comments where blog_id={bid} and user_id={uid} and content={q(a['content'])} limit 1")
        exec_sql(db, f"update tb_blog_comments set {fields} where id={existing}" if existing else f"insert into tb_blog_comments set {fields}")
        count = scalar(db, f"select count(*) from tb_blog_comments where blog_id={bid} and status=0") or "0"
        exec_sql(db, f"update tb_blog set comments={count} where id={bid}")

def ensure_follow(a):
    follower = ensure_user_exists(a["follower_phone"])
    following = ensure_user_exists(a["following_phone"])
    db = f"hmdp_{int(follower) % 2}"
    if not scalar(db, f"select id from tb_follow where user_id={follower} and follow_user_id={following} limit 1"):
        exec_sql(db, f"insert into tb_follow set id={gen_id()}, user_id={follower}, follow_user_id={following}")
    try: redis("SADD", "follows:" + str(follower), str(following))
    except Exception: pass

def follow_current(a):
    follower = user_id(a["follower_phone"]); following = user_id(a["following_phone"])
    if not follower or not following: return None
    db = f"hmdp_{int(follower) % 2}"
    ok = scalar(db, f"select id from tb_follow where user_id={follower} and follow_user_id={following} limit 1")
    return {"follower_phone": a["follower_phone"], "following_phone": a["following_phone"], "follower_id": follower, "following_id": following} if ok else None

def ensure_favorite(a):
    uid = ensure_user_exists(a["user_phone"])
    sid = shop_id(a["shop_name"])
    if not sid: raise RuntimeError("HMDP shop not found: " + a["shop_name"])
    for db in DBS:
        exec_sql(db, f"insert ignore into tb_shop_favorite (shop_id,user_id) values ({sid},{uid})")

def favorite_current(a):
    uid = user_id(a["user_phone"]); sid = shop_id(a["shop_name"])
    if not uid or not sid: return None
    ok = scalar_all(f"select id from tb_shop_favorite where user_id={uid} and shop_id={sid} limit 1")
    return {"user_phone": a["user_phone"], "shop_name": a["shop_name"], "user_id": uid, "shop_id": sid} if ok else None

def review_current(a):
    uid = user_id(a["user_phone"]); sid = shop_id(a["shop_name"])
    if not uid or not sid: return None
    data = rows_all(f"select id,score,content,images,liked,status,round(unix_timestamp(create_time)*1000) from tb_shop_review where shop_id={sid} and user_id={uid} and content={q(a['content'])} order by create_time desc limit 1")
    if not data: return None
    r = data[0][1]
    return {"id": int(r[0]), "user_phone": a["user_phone"], "shop_name": a["shop_name"], "score": int(r[1] or 0), "content": r[2], "images": [x for x in (r[3] or "").split(",") if x], "liked": int(r[4] or 0), "status": int(r[5] or 0), "created_at_ms": int(float(r[6] or 0))}

def ensure_review(a):
    uid = ensure_user_exists(a["user_phone"])
    sid = shop_id(a["shop_name"])
    if not sid: raise RuntimeError("HMDP shop not found: " + a["shop_name"])
    cur = review_current(a); rid = int(a.get("review_id") or (cur or {}).get("id") or gen_id())
    time_fields = f", create_time={dt(a.get('created_at_ms'))}, update_time={dt(a.get('created_at_ms'))}" if a.get("created_at_ms") is not None else ""
    fields = f"id={rid}, shop_id={sid}, user_id={uid}, score={int(a.get('score',5))}, content={q(a['content'])}, images={q(csv(a.get('images') or []))}, liked={int(a.get('liked',0))}, status={int(a.get('status',0))}{time_fields}"
    for db in DBS:
        existing = scalar(db, f"select id from tb_shop_review where shop_id={sid} and user_id={uid} and content={q(a['content'])} limit 1")
        exec_sql(db, f"update tb_shop_review set {fields} where id={existing}" if existing else f"insert into tb_shop_review set {fields}")
        count = scalar(db, f"select count(*) from tb_shop_review where shop_id={sid} and status=0") or "0"
        exec_sql(db, f"update tb_shop set comments={count} where id={sid}")

def ensure_like(a):
    uid = ensure_user_exists(a["user_phone"])
    bid = blog_id(a["blog_title"], a["blog_author_phone"])
    if not bid: raise RuntimeError("HMDP blog not found: " + a["blog_title"])
    key = "blog:liked:" + str(bid)
    if not redis("ZSCORE", key, uid):
        redis("ZADD", key, int(time.time()*1000), uid)
        for db in DBS: exec_sql(db, f"update tb_blog set liked=liked+1 where id={bid}")

def like_current(a):
    uid = user_id(a["user_phone"]); bid = blog_id(a["blog_title"], a["blog_author_phone"])
    if not uid or not bid: return None
    score = redis("ZSCORE", "blog:liked:" + str(bid), uid)
    return {"user_phone": a["user_phone"], "blog_title": a["blog_title"], "blog_author_phone": a["blog_author_phone"], "user_id": uid, "blog_id": bid} if score else None

def voucher_current(a):
    sid = shop_id(a["shop_name"])
    if not sid: return None
    for db in DBS:
        for i in (0, 1):
            data = rows(db, f"select id,shop_id,title,sub_title,rules,pay_value,actual_value,type,status from tb_voucher_{i} where shop_id={sid} and title={q(a['title'])} limit 1")
            if data:
                r = data[0]
                return {"id": int(r[0]), "shop_name": a["shop_name"], "shop_id": int(r[1]), "title": r[2], "sub_title": r[3] or None, "rules": r[4] or None, "pay_value": int(r[5] or 0), "actual_value": int(r[6] or 0), "voucher_type": int(r[7] or 0), "status": int(r[8] or 0)}
    return None

def ensure_voucher(a):
    sid = shop_id(a["shop_name"])
    if not sid: raise RuntimeError("HMDP shop not found: " + a["shop_name"])
    cur = voucher_current(a); vid = int(a.get("voucher_id") or (cur or {}).get("id") or gen_id())
    db, table = voucher_table(vid)
    vtype = int(a.get("voucher_type", a.get("type", 1)))
    fields = f"id={vid}, shop_id={sid}, title={q(a['title'])}, sub_title={q(a.get('sub_title'))}, rules={q(a.get('rules'))}, pay_value={int(a.get('pay_value',100))}, actual_value={int(a.get('actual_value',500))}, type={vtype}, status={int(a.get('status',1))}"
    existing = scalar(db, f"select id from {table} where shop_id={sid} and title={q(a['title'])} limit 1")
    exec_sql(db, f"update {table} set {fields} where id={existing}" if existing else f"insert into {table} set {fields}")
    if existing: vid = int(existing)
    if vtype == 1:
        sdb, stable = seckill_table(vid)
        stock = int(a.get("stock") if a.get("stock") is not None else 20)
        init_stock = int(a.get("init_stock") if a.get("init_stock") is not None else stock)
        min_level = int(a["min_level"]) if a.get("min_level") is not None else "NULL"
        sexisting = scalar(sdb, f"select id from {stable} where voucher_id={vid} limit 1")
        sfields = f"voucher_id={vid}, init_stock={init_stock}, stock={stock}, allowed_levels={q(a.get('allowed_levels'))}, min_level={min_level}, begin_time={q(a.get('begin_time') or '2026-01-01 00:00:00')}, end_time={q(a.get('end_time') or '2027-01-01 00:00:00')}"
        exec_sql(sdb, f"update {stable} set {sfields} where id={sexisting}" if sexisting else f"insert into {stable} set id={gen_id()}, {sfields}")
    return vid

def order_current(a):
    uid = user_id(a["user_phone"]); voucher = voucher_current({"shop_name": a["shop_name"], "title": a["voucher_title"]})
    if not uid or not voucher: return None
    for db in DBS:
        for i in (0,1):
            data = rows(db, f"select id,user_id,voucher_id,pay_type,status,reconciliation_status,round(unix_timestamp(create_time)*1000) from tb_voucher_order_{i} where user_id={uid} and voucher_id={voucher['id']} order by create_time desc limit 1")
            if data:
                r = data[0]
                return {"id": int(r[0]), "user_phone": a["user_phone"], "shop_name": a["shop_name"], "voucher_title": a["voucher_title"], "user_id": int(r[1]), "voucher_id": int(r[2]), "pay_type": int(r[3] or 0), "status": int(r[4] or 0), "reconciliation_status": int(r[5] or 0), "created_at_ms": int(float(r[6] or 0))}
    return None

def ensure_order(a):
    uid = ensure_user_exists(a["user_phone"])
    existing_voucher = voucher_current({"shop_name": a["shop_name"], "title": a["voucher_title"]})
    vid = existing_voucher["id"] if existing_voucher else ensure_voucher({"kind":"hmdp_voucher", "shop_name": a["shop_name"], "title": a["voucher_title"]})
    cur = order_current(a); oid = int(a.get("order_id") or (cur or {}).get("id") or gen_id())
    db, table = order_table(uid, vid)
    time_fields = f", create_time={dt(a.get('created_at_ms'))}, update_time={dt(a.get('created_at_ms'))}" if a.get("created_at_ms") is not None else ""
    fields = f"id={oid}, user_id={uid}, voucher_id={vid}, pay_type={int(a.get('pay_type',1))}, status={int(a.get('status',1))}, reconciliation_status={int(a.get('reconciliation_status',1))}{time_fields}"
    existing = scalar(db, f"select id from {table} where id={oid} or (user_id={uid} and voucher_id={vid}) limit 1")
    exec_sql(db, f"update {table} set {fields} where id={existing}" if existing else f"insert into {table} set {fields}")

def sync_user_index():
    users = []
    seen = set()
    for db in DBS:
        for i in (0, 1):
            for r in rows(db, f"select id,nick_name,icon from tb_user_{i} where nick_name is not null and nick_name <> '' order by id"):
                if not r or r[0] in seen:
                    continue
                seen.add(r[0])
                users.append({"id": str(r[0]), "nickName": r[1], "icon": "" if len(r) < 3 or r[2] == "NULL" else r[2]})
    payload = json.dumps({"success": True, "errorMsg": "", "data": users, "total": str(len(users))}, ensure_ascii=False, separators=(",", ":"))
    for path in ("/tmp/gma_hmdp_export/hmdp/hmdp-vue3/dist/gma-user-index.json", "/tmp/gma_hmdp_user_index.json"):
        try:
            import os
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as fh:
                fh.write(payload)
        except Exception:
            pass
    try:
        subprocess.run(["docker", "cp", "/tmp/gma_hmdp_user_index.json", "hmdp-frontend:/usr/share/nginx/html/gma-user-index.json"], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass

def apply_asset(a):
    k = a["kind"]
    if k == "hmdp_user": ensure_user(a)
    elif k == "hmdp_shop": ensure_shop(a)
    elif k == "hmdp_blog": ensure_blog(a)
    elif k == "hmdp_blog_comment": ensure_comment(a)
    elif k == "hmdp_follow": ensure_follow(a)
    elif k == "hmdp_shop_favorite": ensure_favorite(a)
    elif k == "hmdp_shop_review": ensure_review(a)
    elif k == "hmdp_blog_like": ensure_like(a)
    elif k == "hmdp_voucher": ensure_voucher(a)
    elif k == "hmdp_voucher_order": ensure_order(a)
    else: raise RuntimeError("Unsupported HMDP asset kind: " + k)

def subset(a, cur, keys):
    return all(text_equal(cur.get(k), a.get(k)) for k in keys if a.get(k) is not None)

def time_matches(a, cur):
    return a.get("created_at_ms") is None or abs(int(cur.get("created_at_ms") or 0) - int(a["created_at_ms"])) <= 1000

def probe_asset(a):
    k = a["kind"]
    if k == "hmdp_user":
        cur = user_current(a["phone"]); exact = bool(cur and subset(a, cur, ["phone", "nick_name", "icon"])); label = "hmdp_user:" + a["phone"]
    elif k == "hmdp_shop":
        cur = shop_current(a["name"]); tags = set(a.get("tags") or []); exact = bool(cur and subset(a, cur, ["name", "type_name", "area", "address", "avg_price", "sold", "comments", "open_hours"]) and tags.issubset(set(cur.get("tags") or []))); label = "hmdp_shop:" + a["name"]
    elif k == "hmdp_blog":
        cur = blog_current(a)
        if cur and a.get("expected_images"):
            cur["image_contents"] = image_contents(cur.get("images") or [])
        exact = bool(cur and subset(a, cur, ["author_phone", "shop_name", "title", "content", "liked", "comments"]) and (not a.get("images") or all(x in cur.get("images", []) for x in a.get("images", []))) and time_matches(a, cur)); label = "hmdp_blog:" + a["title"]
    elif k == "hmdp_blog_comment":
        cur = comment_current(a); exact = bool(cur and subset(a, cur, ["author_phone", "blog_title", "blog_author_phone", "content", "liked", "status"]) and time_matches(a, cur)); label = "hmdp_blog_comment:" + a["content"]
    elif k == "hmdp_follow":
        cur = follow_current(a); exact = cur is not None; label = "hmdp_follow:" + a["follower_phone"] + ":" + a["following_phone"]
    elif k == "hmdp_shop_favorite":
        cur = favorite_current(a); exact = cur is not None; label = "hmdp_shop_favorite:" + a["user_phone"] + ":" + a["shop_name"]
    elif k == "hmdp_shop_review":
        cur = review_current(a); exact = bool(cur and subset(a, cur, ["user_phone", "shop_name", "score", "content", "liked", "status"]) and time_matches(a, cur)); label = "hmdp_shop_review:" + a["content"]
    elif k == "hmdp_blog_like":
        cur = like_current(a); exact = cur is not None; label = "hmdp_blog_like:" + a["user_phone"] + ":" + a["blog_title"]
    elif k == "hmdp_voucher":
        cur = voucher_current(a); exact = bool(cur and subset(a, cur, ["shop_name", "title", "sub_title", "rules", "pay_value", "actual_value", "status"])); label = "hmdp_voucher:" + a["title"]
    elif k == "hmdp_voucher_order":
        cur = order_current(a); exact = bool(cur and subset(a, cur, ["user_phone", "shop_name", "voucher_title", "pay_type", "status", "reconciliation_status"]) and time_matches(a, cur)); label = "hmdp_voucher_order:" + a["user_phone"] + ":" + a["voucher_title"]
    else:
        raise RuntimeError("Unsupported HMDP asset kind: " + k)
    return {"label": label, "identity_exists": cur is not None, "exact_match": exact, "current": cur}
'''

def _payload(asset: Any) -> str:
    data = asset.model_dump() if hasattr(asset, "model_dump") else dict(asset)
    return base64.b64encode(json.dumps(data, ensure_ascii=False).encode()).decode("ascii")

def _run_asset_script(client: AndroidController, asset: Any, action: str) -> str:
    script = f"""
set -euo pipefail
python3 - <<'INNER_PY'
import base64, json
{_RUNTIME}
asset = json.loads(base64.b64decode({_payload(asset)!r}).decode('utf-8'))
if {action!r} == 'apply':
    apply_asset(asset)
    sync_user_index()
else:
    print(json.dumps(probe_asset(asset), ensure_ascii=False))
INNER_PY
"""
    return run_bash(client, script, timeout=120)

def ensure_hmdp_backend(client: AndroidController) -> None:
    _ensure_hmdp_backend(client)

def hmdp_login_user_asset(
    *,
    phone: str = HMDP_LOGIN_PHONE,
    password: str = HMDP_LOGIN_PASSWORD,
    nick_name: str | None = HMDP_LOGIN_NICKNAME,
) -> dict[str, Any]:
    return {"kind": "hmdp_user", "app": "HMDP", "phone": phone, "password": password, "nick_name": nick_name or phone, "icon": HMDP_DEFAULT_ICON, "city": "Hangzhou", "level": 1}

def ensure_hmdp_login_user(
    client: AndroidController,
    *,
    phone: str = HMDP_LOGIN_PHONE,
    password: str = HMDP_LOGIN_PASSWORD,
    nick_name: str | None = HMDP_LOGIN_NICKNAME,
) -> None:
    ensure_hmdp_backend(client)
    _run_asset_script(
        client,
        hmdp_login_user_asset(phone=phone, password=password, nick_name=nick_name),
        "apply",
    )

def login_hmdp_app(
    client: AndroidController,
    *,
    phone: str = HMDP_LOGIN_PHONE,
    password: str = HMDP_LOGIN_PASSWORD,
    ensure_user: bool = True,
) -> None:
    if ensure_user:
        nick_name = HMDP_LOGIN_NICKNAME if phone == HMDP_LOGIN_PHONE else phone
        ensure_hmdp_login_user(client, phone=phone, password=password, nick_name=nick_name)
    launch_webapp_with_login_extras(
        client,
        "gma.webapp.hmdp",
        phone=phone,
        password=password,
    )

def apply_hmdp_asset(client: AndroidController, asset: Any) -> None:
    ensure_hmdp_backend(client)
    _run_asset_script(client, asset, "apply")

def probe_hmdp_asset(client: AndroidController, asset: Any) -> dict[str, Any]:
    ensure_hmdp_backend(client)
    return json.loads(_run_asset_script(client, asset, "probe"))
