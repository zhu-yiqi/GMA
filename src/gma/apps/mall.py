from __future__ import annotations

import base64
import json
from typing import TYPE_CHECKING, Any

from gma.apps._shell import launch_webapp_with_login_extras, run_bash
from gma.apps.offline_webapps import ensure_mall_backend as _ensure_mall_backend

if TYPE_CHECKING:
    from gma.runtime.controller import AndroidController


MALL_WEB_URL = "http://10.0.2.2:8040"
MALL_IMAGE = MALL_WEB_URL + "/static/temp/banner1.jpg"
MALL_LOGIN_USERNAME = "owner"
MALL_LOGIN_PASSWORD = "123456"
MALL_LOGIN_NICKNAME = "owner"
MALL_LOGIN_PHONE = "15510002011"
MALL_LOGIN_CITY = ""
MALL_PASSWORD_HASH_123456 = "$2a$10$NZ5o7r2E.ayT2ZoxgjlI.eJ6OEYqjH7INR/F.mXDbjZJi9HF0YCVG"

_RUNTIME = r'''
import json
import subprocess

MYSQL = ["docker", "exec", "-i", "mall-mysql", "mysql", "-umall", "-pmall_pass_2025", "--default-character-set=utf8mb4", "mall"]
QUERY = MYSQL + ["--batch", "--raw", "--skip-column-names"]
IMAGE = "http://10.0.2.2:8040/static/temp/banner1.jpg"
PASSWORD_HASH = "$2a$10$NZ5o7r2E.ayT2ZoxgjlI.eJ6OEYqjH7INR/F.mXDbjZJi9HF0YCVG"


def q(value):
    if value is None:
        return "NULL"
    return "'" + str(value).replace("\\", "\\\\").replace("'", "''").replace("\0", "") + "'"


def b(value):
    return "1" if value else "0"


def ts(value_ms):
    if value_ms is None:
        return "now()"
    return "from_unixtime(" + str(int(value_ms) / 1000.0) + ")"


def exec_sql(sql):
    subprocess.run(MYSQL, input=sql, text=True, check=True)


def rows(sql):
    out = subprocess.check_output(QUERY + ["-e", sql], text=True)
    return [["" if cell == "NULL" else cell for cell in line.split("\t")] for line in out.splitlines() if line.strip()]


def scalar(sql):
    data = rows(sql)
    return data[0][0] if data and data[0] else None


def ensure_member(username):
    current = scalar("select id from ums_member where username = " + q(username) + " limit 1")
    if current:
        return int(current)
    exec_sql(
        "insert into ums_member (username, password, nickname, status, create_time, icon) values ("
        + q(username) + ", " + q(PASSWORD_HASH) + ", " + q(username) + ", 1, now(), " + q(IMAGE) + ")"
    )
    return int(scalar("select id from ums_member where username = " + q(username) + " limit 1"))


def member_id(username):
    value = scalar("select id from ums_member where username = " + q(username) + " limit 1")
    return int(value) if value else None


def product_id(product_sn):
    value = scalar("select id from pms_product where product_sn = " + q(product_sn) + " limit 1")
    return int(value) if value else None


def sku_id_for(product_id_value, sku_code=None):
    if sku_code:
        value = scalar("select id from pms_sku_stock where sku_code = " + q(sku_code) + " limit 1")
        if value:
            return int(value)
    value = scalar("select id from pms_sku_stock where product_id = " + str(product_id_value) + " order by id limit 1")
    return int(value) if value else None


def product_current_by_sn(product_sn):
    pid = product_id(product_sn)
    if not pid:
        return None
    data = rows(
        "select id, name, product_sn, price, stock, sub_title, description, pic, brand_name, product_category_name, publish_status, delete_status "
        "from pms_product where id = " + str(pid)
    )[0]
    skus = rows("select id, sku_code, price, stock from pms_sku_stock where product_id = " + str(pid) + " order by id")
    return {
        "id": int(data[0]), "name": data[1], "product_sn": data[2], "price": float(data[3] or 0),
        "stock": int(data[4] or 0), "sub_title": data[5] or None, "description": data[6] or None,
        "pic": data[7] or None, "brand_name": data[8] or None, "product_category_name": data[9] or None,
        "publish_status": data[10] == "1", "delete_status": data[11] == "1",
        "skus": [{"id": int(r[0]), "sku_code": r[1], "price": float(r[2] or 0), "stock": int(r[3] or 0)} for r in skus],
    }


def business_current(asset):
    data = rows(
        "select id, name, first_letter, sort, factory_status, show_status, product_count, product_comment_count, logo, big_pic, brand_story "
        "from pms_brand where name = " + q(asset["name"]) + " limit 1"
    )
    if not data:
        return None
    r = data[0]
    product_rows = rows(
        "select product_sn from pms_product where brand_id = " + r[0] + " or brand_name = " + q(asset["name"]) + " order by product_sn"
    )
    return {
        "id": int(r[0]),
        "name": r[1],
        "first_letter": r[2] or None,
        "sort": int(r[3] or 0),
        "factory_status": r[4] == "1",
        "show_status": r[5] == "1",
        "product_count": int(r[6] or 0),
        "product_comment_count": int(r[7] or 0),
        "logo": r[8] or None,
        "big_pic": r[9] or None,
        "brand_story": r[10] or None,
        "product_sns": [row[0] for row in product_rows],
    }


def apply_member(asset):
    mid = ensure_member(asset["username"])
    exec_sql(
        "update ums_member set password = " + q(PASSWORD_HASH)
        + ", nickname = " + q(asset.get("nickname") or asset["username"])
        + ", phone = " + q(asset.get("phone"))
        + ", status = " + str(asset.get("status", 1))
        + ", icon = " + q(asset.get("icon") or IMAGE)
        + ", gender = " + (str(asset["gender"]) if asset.get("gender") is not None else "NULL")
        + ", birthday = " + q(asset.get("birthday"))
        + ", city = " + q(asset.get("city"))
        + ", job = " + q(asset.get("job"))
        + ", personalized_signature = " + q(asset.get("personalized_signature"))
        + " where id = " + str(mid)
    )


def apply_address(asset):
    mid = ensure_member(asset["member_username"])
    if asset.get("default_status"):
        exec_sql("update ums_member_receive_address set default_status = 0 where member_id = " + str(mid))
    existing = scalar(
        "select id from ums_member_receive_address where member_id = " + str(mid)
        + " and name = " + q(asset["name"])
        + " and phone_number = " + q(asset["phone_number"])
        + " and detail_address = " + q(asset["detail_address"])
        + " order by id desc limit 1"
    )
    values = (
        "member_id = " + str(mid)
        + ", name = " + q(asset["name"])
        + ", phone_number = " + q(asset["phone_number"])
        + ", default_status = " + b(asset.get("default_status"))
        + ", post_code = " + q(asset.get("post_code"))
        + ", province = " + q(asset.get("province"))
        + ", city = " + q(asset.get("city"))
        + ", region = " + q(asset.get("region"))
        + ", detail_address = " + q(asset["detail_address"])
    )
    if existing:
        exec_sql("update ums_member_receive_address set " + values + " where id = " + existing)
    else:
        exec_sql("insert into ums_member_receive_address set " + values)


def apply_product(asset):
    pid = product_id(asset["product_sn"])
    brand_name = asset.get("brand_name") or "Xiaomi"
    category_name = asset.get("product_category_name") or "Mobile Phones"
    brand_id = scalar("select id from pms_brand where name = " + q(brand_name) + " limit 1") or "6"
    category_id = scalar("select id from pms_product_category where name = " + q(category_name) + " limit 1") or "19"
    fields = (
        "name = " + q(asset["name"])
        + ", brand_id = " + str(brand_id)
        + ", product_category_id = " + str(category_id)
        + ", feight_template_id = 0"
        + ", product_attribute_category_id = 3"
        + ", product_sn = " + q(asset["product_sn"])
        + ", price = " + str(asset["price"])
        + ", promotion_price = " + str(asset["price"])
        + ", original_price = " + str(asset["price"])
        + ", stock = " + str(asset.get("stock", 100))
        + ", low_stock = 0"
        + ", sub_title = " + q(asset.get("sub_title"))
        + ", description = " + q(asset.get("description"))
        + ", pic = " + q(asset.get("pic") or IMAGE)
        + ", album_pics = " + q(asset.get("pic") or IMAGE)
        + ", detail_title = " + q(asset["name"])
        + ", detail_desc = " + q(asset.get("sub_title"))
        + ", detail_html = " + q(asset.get("description") or asset.get("sub_title") or asset["name"])
        + ", detail_mobile_html = " + q(asset.get("description") or asset.get("sub_title") or asset["name"])
        + ", brand_name = " + q(brand_name)
        + ", product_category_name = " + q(category_name)
        + ", publish_status = " + b(asset.get("publish_status", True))
        + ", delete_status = " + b(asset.get("delete_status"))
        + ", new_status = 1, recommand_status = 1, verify_status = 0, sort = 0, sale = 0"
        + ", gift_growth = 0, gift_point = 0, use_point_limit = 0, preview_status = 0, promotion_per_limit = 0, promotion_type = 0"
    )
    if pid:
        exec_sql("update pms_product set " + fields + " where id = " + str(pid))
    else:
        exec_sql("insert into pms_product set " + fields)
        pid = product_id(asset["product_sn"])
    sku_code = asset.get("sku_code") or asset["product_sn"] + "-SKU"
    sid = sku_id_for(pid, sku_code)
    sku_fields = (
        "product_id = " + str(pid)
        + ", sku_code = " + q(sku_code)
        + ", price = " + str(asset["price"])
        + ", stock = " + str(asset.get("stock", 100))
        + ", low_stock = 0, pic = " + q(asset.get("pic") or IMAGE)
        + ", sale = 0, promotion_price = " + str(asset["price"])
        + ", lock_stock = 0, sp_data = " + q("[]")
    )
    if sid:
        exec_sql("update pms_sku_stock set " + sku_fields + " where id = " + str(sid))
    else:
        exec_sql("insert into pms_sku_stock set " + sku_fields)


def apply_business(asset):
    name = asset["name"]
    brand_id = scalar("select id from pms_brand where name = " + q(name) + " limit 1")
    first_letter = asset.get("first_letter") or (name[:1].upper() if name else "")
    fields = (
        "name = " + q(name)
        + ", first_letter = " + q(first_letter)
        + ", sort = " + str(asset.get("sort", 0))
        + ", factory_status = " + b(asset.get("factory_status", True))
        + ", show_status = " + b(asset.get("show_status", True))
        + ", logo = " + q(asset.get("logo") or IMAGE)
        + ", big_pic = " + q(asset.get("big_pic") or asset.get("logo") or IMAGE)
        + ", brand_story = " + q(asset.get("brand_story"))
    )
    if brand_id:
        exec_sql("update pms_brand set " + fields + " where id = " + str(brand_id))
    else:
        exec_sql("insert into pms_brand set " + fields + ", product_count = 0, product_comment_count = 0")
        brand_id = scalar("select id from pms_brand where name = " + q(name) + " limit 1")
    for product in asset.get("products", []):
        product = dict(product)
        product["brand_name"] = name
        apply_product(product)
    count = scalar("select count(*) from pms_product where brand_id = " + str(brand_id) + " or brand_name = " + q(name)) or "0"
    exec_sql("update pms_brand set product_count = " + str(count) + " where id = " + str(brand_id))


def apply_cart_item(asset):
    mid = ensure_member(asset["member_username"])
    product = product_current_by_sn(asset["product_sn"])
    if not product:
        raise RuntimeError("Mall product not found: " + asset["product_sn"])
    sku = product["skus"][0] if product["skus"] else {"id": None, "sku_code": None, "price": product["price"]}
    existing = scalar("select id from oms_cart_item where member_id = " + str(mid) + " and product_id = " + str(product["id"]) + " order by id desc limit 1")
    fields = (
        "product_id = " + str(product["id"])
        + ", product_sku_id = " + (str(sku["id"]) if sku.get("id") else "NULL")
        + ", member_id = " + str(mid)
        + ", quantity = " + str(asset.get("quantity", 1))
        + ", price = " + str(sku.get("price") or product["price"])
        + ", product_pic = " + q(product.get("pic") or IMAGE)
        + ", product_name = " + q(product["name"])
        + ", product_sub_title = " + q(product.get("sub_title"))
        + ", product_sku_code = " + q(sku.get("sku_code"))
        + ", member_nickname = " + q(asset["member_username"])
        + ", modify_date = now(), create_date = coalesce(create_date, now())"
        + ", delete_status = " + b(asset.get("delete_status"))
        + ", product_brand = " + q(product.get("brand_name"))
        + ", product_sn = " + q(product["product_sn"])
        + ", product_attr = " + q("[]")
    )
    if existing:
        exec_sql("update oms_cart_item set " + fields + " where id = " + existing)
    else:
        exec_sql("insert into oms_cart_item set " + fields)


def apply_order(asset):
    mid = ensure_member(asset["member_username"])
    total = 0.0
    items = []
    for item in asset["items"]:
        product = product_current_by_sn(item["product_sn"])
        if not product:
            raise RuntimeError("Mall order product not found: " + item["product_sn"])
        sku = product["skus"][0] if product["skus"] else {"id": None, "sku_code": None, "price": product["price"]}
        price = float(item.get("price") if item.get("price") is not None else sku.get("price") or product["price"])
        qty = int(item.get("quantity", 1))
        total += price * qty
        items.append((product, sku, price, qty))
    existing = scalar("select id from oms_order where order_sn = " + q(asset["order_sn"]) + " limit 1")
    create_time_expr = ts(asset.get("created_at_ms")) if asset.get("created_at_ms") is not None else "coalesce(create_time, now())"
    order_fields = (
        "member_id = " + str(mid)
        + ", order_sn = " + q(asset["order_sn"])
        + ", create_time = " + create_time_expr
        + ", member_username = " + q(asset["member_username"])
        + ", total_amount = " + str(total)
        + ", pay_amount = " + str(total)
        + ", freight_amount = 0, promotion_amount = 0, integration_amount = 0, coupon_amount = 0, discount_amount = 0"
        + ", status = " + str(asset.get("status", 0))
        + ", receiver_name = " + q(asset["receiver_name"])
        + ", receiver_phone = " + q(asset["receiver_phone"])
        + ", receiver_province = " + q(asset.get("receiver_province"))
        + ", receiver_city = " + q(asset.get("receiver_city"))
        + ", receiver_region = " + q(asset.get("receiver_region"))
        + ", receiver_detail_address = " + q(asset["receiver_detail_address"])
        + ", note = " + q(asset.get("note"))
        + ", delete_status = 0"
    )
    if existing:
        order_id = int(existing)
        exec_sql("update oms_order set " + order_fields + " where id = " + str(order_id))
        exec_sql("delete from oms_order_item where order_id = " + str(order_id))
    else:
        exec_sql("insert into oms_order set " + order_fields)
        order_id = int(scalar("select id from oms_order where order_sn = " + q(asset["order_sn"]) + " limit 1"))
    for product, sku, price, qty in items:
        exec_sql(
            "insert into oms_order_item (order_id, order_sn, product_id, product_pic, product_name, product_brand, product_sn, product_price, product_quantity, product_sku_id, product_sku_code, real_amount, product_attr) values ("
            + str(order_id) + ", " + q(asset["order_sn"]) + ", " + str(product["id"]) + ", " + q(product.get("pic") or IMAGE) + ", "
            + q(product["name"]) + ", " + q(product.get("brand_name")) + ", " + q(product["product_sn"]) + ", " + str(price) + ", " + str(qty) + ", "
            + (str(sku.get("id")) if sku.get("id") else "NULL") + ", " + q(sku.get("sku_code")) + ", " + str(price * qty) + ", " + q("[]") + ")"
        )


def apply_review(asset):
    mid = ensure_member(asset["member_username"])
    product = product_current_by_sn(asset["product_sn"])
    if not product:
        raise RuntimeError("Mall review product not found: " + asset["product_sn"])
    order_id = scalar(
        "select id from oms_order where order_sn = " + q(asset["order_sn"])
        + " and member_id = " + str(mid)
        + " limit 1"
    )
    if not order_id:
        raise RuntimeError("Mall review order not found: " + asset["order_sn"])
    item_rows = rows(
        "select id, product_name, product_attr from oms_order_item where order_id = "
        + str(order_id)
        + " and product_sn = " + q(asset["product_sn"])
        + " order by id limit 1"
    )
    if not item_rows:
        raise RuntimeError("Mall review order item not found: " + asset["product_sn"])
    order_item_id, product_name, product_attr = item_rows[0]
    created_expr = ts(asset.get("created_at_ms"))
    existing = scalar(
        "select id from pms_comment where order_id = " + str(order_id)
        + " and order_item_id = " + str(order_item_id)
        + " limit 1"
    )
    fields = (
        "product_id = " + str(product["id"])
        + ", member_id = " + str(mid)
        + ", order_id = " + str(order_id)
        + ", order_item_id = " + str(order_item_id)
        + ", member_nick_name = " + q(asset["member_username"])
        + ", member_icon = " + q(IMAGE)
        + ", product_name = " + q(product_name)
        + ", star = " + str(int(asset.get("star", 5)))
        + ", content = " + q(asset["content"])
        + ", pics = " + q("")
        + ", product_attribute = " + q(product_attr or "[]")
        + ", create_time = " + created_expr
        + ", show_status = " + str(int(asset.get("show_status", 1)))
        + ", collect_couont = 0, read_count = 0, replay_count = 0"
    )
    if existing:
        exec_sql("update pms_comment set " + fields + " where id = " + existing)
    else:
        exec_sql("insert into pms_comment set " + fields)
    exec_sql("update oms_order set comment_time = " + created_expr + " where id = " + str(order_id))


def apply_asset(asset):
    kind = asset["kind"]
    if kind == "mall_member": apply_member(asset)
    elif kind == "mall_address": apply_address(asset)
    elif kind == "mall_product": apply_product(asset)
    elif kind == "mall_brand": apply_business(asset)
    elif kind == "mall_cart_item": apply_cart_item(asset)
    elif kind == "mall_order": apply_order(asset)
    elif kind == "mall_review": apply_review(asset)
    else: raise RuntimeError("Unsupported Mall asset kind: " + kind)


def member_current(asset):
    data = rows("select username, nickname, phone, status, icon, gender, birthday, city, job, personalized_signature from ums_member where username = " + q(asset["username"]) + " limit 1")
    if not data: return None
    r = data[0]
    return {"username": r[0], "nickname": r[1] or None, "phone": r[2] or None, "status": int(r[3] or 0), "icon": r[4] or None, "gender": int(r[5]) if r[5] else None, "birthday": r[6] or None, "city": r[7] or None, "job": r[8] or None, "personalized_signature": r[9] or None}


def address_current(asset):
    mid = member_id(asset["member_username"])
    if not mid: return None
    data = rows("select name, phone_number, default_status, post_code, province, city, region, detail_address from ums_member_receive_address where member_id = " + str(mid) + " and name = " + q(asset["name"]) + " and phone_number = " + q(asset["phone_number"]) + " and detail_address = " + q(asset["detail_address"]) + " order by id desc limit 1")
    if not data: return None
    r = data[0]
    return {"member_username": asset["member_username"], "name": r[0], "phone_number": r[1], "default_status": r[2] == "1", "post_code": r[3] or None, "province": r[4] or None, "city": r[5] or None, "region": r[6] or None, "detail_address": r[7]}


def cart_current(asset):
    mid = member_id(asset["member_username"]); pid = product_id(asset["product_sn"])
    if not mid or not pid: return None
    data = rows("select quantity, delete_status, product_name from oms_cart_item where member_id = " + str(mid) + " and product_id = " + str(pid) + " order by id desc limit 1")
    if not data: return None
    return {"member_username": asset["member_username"], "product_sn": asset["product_sn"], "quantity": int(data[0][0] or 0), "delete_status": data[0][1] == "1", "product_name": data[0][2]}


def order_current(asset):
    data = rows("select id, member_username, order_sn, total_amount, status, receiver_name, receiver_phone, receiver_province, receiver_city, receiver_region, receiver_detail_address, note, round(unix_timestamp(create_time) * 1000) from oms_order where order_sn = " + q(asset["order_sn"]) + " limit 1")
    if not data: return None
    r = data[0]
    items = rows("select product_sn, product_quantity, product_price from oms_order_item where order_id = " + r[0] + " order by id")
    return {"id": int(r[0]), "member_username": r[1], "order_sn": r[2], "total_amount": float(r[3] or 0), "status": int(r[4] or 0), "receiver_name": r[5], "receiver_phone": r[6], "receiver_province": r[7] or None, "receiver_city": r[8] or None, "receiver_region": r[9] or None, "receiver_detail_address": r[10], "note": r[11] or None, "created_at_ms": int(float(r[12] or 0)), "items": [{"product_sn": x[0], "quantity": int(x[1] or 0), "price": float(x[2] or 0)} for x in items]}


def review_current(asset):
    data = rows(
        "select c.id, o.order_sn, i.product_sn, o.member_username, c.content, c.star, c.show_status, round(unix_timestamp(c.create_time) * 1000), round(unix_timestamp(o.comment_time) * 1000) "
        "from pms_comment c join oms_order o on o.id = c.order_id join oms_order_item i on i.id = c.order_item_id "
        "where o.order_sn = " + q(asset["order_sn"]) + " and i.product_sn = " + q(asset["product_sn"]) + " order by c.id desc limit 1"
    )
    if not data:
        return None
    r = data[0]
    return {"id": int(r[0]), "order_sn": r[1], "product_sn": r[2], "member_username": r[3], "content": r[4], "star": int(r[5] or 0), "show_status": int(r[6] or 0), "created_at_ms": int(float(r[7] or 0)), "comment_time_ms": int(float(r[8] or 0))}


def text_equal(a, b):
    if isinstance(a, str) and isinstance(b, str):
        return a.strip() == b.strip()
    return a == b

def exact_subset(asset, current, keys):
    return all(text_equal(current.get(k), asset.get(k)) for k in keys if asset.get(k) is not None)


def region_path(value):
    return ", ".join(str(part).strip() for part in value if part is not None and str(part).strip())


def normalized_region_variants(value):
    parts = [str(part).strip() for part in value if part is not None and str(part).strip()]
    variants = [parts]
    deduped = []
    for part in parts:
        if not deduped or part.lower() != deduped[-1].lower():
            deduped.append(part)
    if deduped != parts:
        variants.append(deduped)

    normalized = set()
    for variant in variants:
        text = " ".join(variant).lower()
        normalized.add("".join(ch for ch in text if ch.isalnum()))
    return normalized


def region_equal(expected, current):
    expected_region = region_path(expected)
    if not expected_region:
        return True
    if text_equal(region_path(current), expected_region):
        return True
    return bool(normalized_region_variants(expected) & normalized_region_variants(current))


def exact_address(asset, current):
    if not exact_subset(asset, current, ["member_username", "name", "phone_number", "detail_address", "post_code", "default_status"]):
        return False
    return region_equal(
        [asset.get("province"), asset.get("city"), asset.get("region")],
        [current.get("province"), current.get("city"), current.get("region")],
    )


def probe_asset(asset):
    kind = asset["kind"]
    if kind == "mall_member":
        current = member_current(asset); exact = bool(current and exact_subset(asset, current, ["username", "nickname", "phone", "status", "icon", "gender", "birthday", "city", "job", "personalized_signature"])); label = "mall_member:" + asset["username"]
    elif kind == "mall_address":
        current = address_current(asset); exact = bool(current and exact_address(asset, current)); label = "mall_address:" + asset["name"]
    elif kind == "mall_product":
        current = product_current_by_sn(asset["product_sn"]); exact = bool(current and text_equal(current.get("name"), asset["name"]) and abs(current.get("price", 0) - float(asset["price"])) < 0.001 and current.get("stock") == asset.get("stock", 100)); label = "mall_product:" + asset["product_sn"]
    elif kind == "mall_brand":
        current = business_current(asset); expected_products = sorted(product["product_sn"] for product in asset.get("products", [])); actual_products = sorted(current.get("product_sns", [])) if current else []; exact = bool(current and exact_subset(asset, current, ["name", "first_letter", "sort", "factory_status", "show_status", "logo", "big_pic", "brand_story"]) and all(product_sn in actual_products for product_sn in expected_products)); label = "mall_brand:" + asset["name"]
    elif kind == "mall_cart_item":
        current = cart_current(asset); exact = bool(current and current.get("quantity") == asset.get("quantity", 1) and current.get("delete_status") == bool(asset.get("delete_status"))); label = "mall_cart_item:" + asset["member_username"] + ":" + asset["product_sn"]
    elif kind == "mall_order":
        current = order_current(asset); expected_items = sorted((i["product_sn"], int(i.get("quantity", 1))) for i in asset["items"]); actual_items = sorted((i["product_sn"], i["quantity"]) for i in current.get("items", [])) if current else [] ; exact = bool(current and current.get("member_username") == asset["member_username"] and current.get("status") == asset.get("status", 0) and text_equal(current.get("receiver_name"), asset["receiver_name"]) and actual_items == expected_items and (asset.get("created_at_ms") is None or abs(current.get("created_at_ms", 0) - int(asset["created_at_ms"])) <= 1000)); label = "mall_order:" + asset["order_sn"]
    elif kind == "mall_review":
        current = review_current(asset); exact = bool(current and exact_subset(asset, current, ["order_sn", "product_sn", "member_username", "content", "star", "show_status"]) and (asset.get("created_at_ms") is None or abs(current.get("created_at_ms", 0) - int(asset["created_at_ms"])) <= 1000)); label = "mall_review:" + asset["order_sn"] + ":" + asset["product_sn"]
    else:
        raise RuntimeError("Unsupported Mall asset kind: " + kind)
    return {"label": label, "identity_exists": current is not None, "exact_match": exact, "current": current}
'''


def _payload(asset: Any) -> str:
    data = asset.model_dump() if hasattr(asset, "model_dump") else dict(asset)
    return base64.b64encode(json.dumps(data, ensure_ascii=False).encode("utf-8")).decode("ascii")


def _run_asset_script(client: AndroidController, asset: Any, action: str) -> str:
    script = f"""
set -euo pipefail
PYTHON_BIN=/app/gma/.venv/bin/python3
if [ ! -x "$PYTHON_BIN" ]; then PYTHON_BIN=python3; fi
"$PYTHON_BIN" - <<'INNER_PY'
import base64
import json
{_RUNTIME}
asset = json.loads(base64.b64decode({_payload(asset)!r}).decode('utf-8'))
if {action!r} == 'apply':
    apply_asset(asset)
else:
    print(json.dumps(probe_asset(asset), ensure_ascii=False))
INNER_PY
"""
    return run_bash(client, script, timeout=120)


def ensure_mall_backend(client: AndroidController) -> None:
    _ensure_mall_backend(client)


def mall_login_member_asset(
    *,
    username: str = MALL_LOGIN_USERNAME,
    password: str = MALL_LOGIN_PASSWORD,
    nickname: str = MALL_LOGIN_NICKNAME,
    phone: str | None = MALL_LOGIN_PHONE,
    city: str = MALL_LOGIN_CITY,
) -> dict[str, Any]:
    return {
        "kind": "mall_member",
        "app": "Mall",
        "username": username,
        "password": password,
        "nickname": nickname,
        "phone": phone,
        "status": 1,
        "icon": MALL_IMAGE,
        "city": city,
    }


def ensure_mall_login_user(
    client: AndroidController,
    *,
    username: str = MALL_LOGIN_USERNAME,
    password: str = MALL_LOGIN_PASSWORD,
    nickname: str | None = MALL_LOGIN_NICKNAME,
    phone: str | None = MALL_LOGIN_PHONE,
) -> None:
    ensure_mall_backend(client)
    _run_asset_script(
        client,
        mall_login_member_asset(
            username=username,
            password=password,
            nickname=nickname or username,
            phone=phone,
        ),
        "apply",
    )


def login_mall_app(
    client: AndroidController,
    *,
    username: str = MALL_LOGIN_USERNAME,
    password: str = MALL_LOGIN_PASSWORD,
    ensure_user: bool = True,
) -> None:
    if ensure_user:
        nickname = MALL_LOGIN_NICKNAME if username == MALL_LOGIN_USERNAME else username
        phone = MALL_LOGIN_PHONE if username == MALL_LOGIN_USERNAME else None
        ensure_mall_login_user(client, username=username, password=password, nickname=nickname, phone=phone)
    launch_webapp_with_login_extras(
        client,
        "gma.webapp.mall",
        username=username,
        password=password,
    )


def apply_mall_asset(client: AndroidController, asset: Any) -> None:
    ensure_mall_backend(client)
    _run_asset_script(client, asset, "apply")


def probe_mall_asset(client: AndroidController, asset: Any) -> dict[str, Any]:
    ensure_mall_backend(client)
    return json.loads(_run_asset_script(client, asset, "probe"))
