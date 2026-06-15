from __future__ import annotations

import base64
import hashlib
import json
import shlex
from typing import TYPE_CHECKING, Any

from gma.apps._shell import launch_webapp_with_login_extras, run_bash
from gma.apps.offline_webapps import ensure_meituan_backend as _ensure_meituan_backend

MEITUAN_WEB_URL = "http://10.0.2.2:8050/meituan/"
MEITUAN_LOGIN_USERNAME = "owner"
MEITUAN_LOGIN_PASSWORD = "123456"
MEITUAN_LOGIN_USER_ID = 9901
MEITUAN_LOGIN_CITY = ""
MEITUAN_WEBAPP_ID = "gma_meituan"
MEITUAN_WEBAPP_ACTION = "org.chromium.chrome.browser.webapps.WebappManager.ACTION_START_SECURE_WEBAPP"
MEITUAN_WEBAPP_COMPONENT = "com.android.chrome/org.chromium.chrome.browser.webapps.SecureWebAppLauncher"
MEITUAN_WEBAPP_NAME = "美团外卖"


if TYPE_CHECKING:
    from gma.runtime.controller import AndroidController


_RUNTIME = r'''
function nextId(field) {
  var ids = db.ids.findOne();
  if (!ids) {
    db.ids.insert({restaurant_id: 0, food_id: 0, order_id: 0, user_id: 0, address_id: 0, category_id: 0, sku_id: 0, shopping_cart_id: 0, comment_id: 0});
    ids = db.ids.findOne();
  }
  var value = (ids[field] || 0) + 1;
  var update = {$set: {}};
  update.$set[field] = value;
  db.ids.update({_id: ids._id}, update);
  return value;
}
function now() { return new Date(); }
function assetDate(value) { return value == null ? now() : new Date(Number(value)); }
function assetSeconds(value) { return String(Math.floor(Number(value) / 1000)); }
function dateMs(value) {
  if (value == null) return null;
  var parsed = new Date(value).getTime();
  return isNaN(parsed) ? null : parsed;
}
function defaultImage() { return "/img/restaurant.a244c07f.jpg"; }
function defaultAvatar() { return "/img/delivery-avatar.61d561c7.png"; }
function userById(id) { return db.admins.findOne({id: id}); }
function restaurantByName(name) { return db.restaurants.findOne({name: name}); }
function categoryByRestaurantAndName(restaurantId, name) { return db.categories.findOne({restaurant_id: restaurantId, name: name}); }
function foodByRestaurantAndName(restaurantId, name) { return db.foods.findOne({restaurant_id: restaurantId, name: name}); }
function addressByName(userId, name) { var cursor = db.addresses.find({user_id: userId}).sort({id: -1}); while (cursor.hasNext()) { var item = cursor.next(); if (textEq(item.name, name)) return item; } return null; }
function latestOrder(query) { var cursor = db.orders.find(query).sort({create_time_timestamp: -1, id: -1}).limit(1); return cursor.hasNext() ? cursor.next() : null; }
function clone(obj) { return JSON.parse(JSON.stringify(obj)); }
function exactValue(a, b) { return JSON.stringify(a) === JSON.stringify(b); }
function textEq(a, b) { return String(a == null ? "" : a).trim() === String(b == null ? "" : b).trim(); }
function scalarNumber(value) { return Number(value || 0); }

function ensureUser(asset) {
  var user = asset.user_id ? userById(asset.user_id) : db.admins.findOne({username: asset.username});
  var userId = asset.user_id || (user ? user.id : nextId('user_id'));
  var doc = {
    username: asset.username,
    password: asset.password || '123456',
    id: userId,
    status: asset.status == null ? 1 : asset.status,
    city: asset.city || '',
    avatar: asset.avatar || defaultAvatar(),
    create_time: user && user.create_time ? user.create_time : now(),
    address: user && user.address ? user.address : []
  };
  db.admins.update({id: userId}, {$set: doc}, {upsert: true});
  return db.admins.findOne({id: userId});
}
function ensureRestaurant(asset) {
  var current = restaurantByName(asset.name);
  var restaurantId = asset.restaurant_id || (current ? current.id : nextId('restaurant_id'));
  var doc = {
    id: restaurantId,
    name: asset.name,
    month_sales: asset.month_sales || 0,
    month_sales_tip: String(asset.month_sales || 0) + ' sold/mo',
    wm_poi_score: asset.wm_poi_score == null ? 5 : asset.wm_poi_score,
    delivery_score: asset.wm_poi_score == null ? 5 : asset.wm_poi_score,
    quality_score: asset.wm_poi_score == null ? 5 : asset.wm_poi_score,
    pack_score: asset.wm_poi_score == null ? 5 : asset.wm_poi_score,
    food_score: asset.wm_poi_score == null ? 5 : asset.wm_poi_score,
    delivery_time_tip: '30 min',
    third_category: asset.category || 'Asset Check',
    pic_url: asset.pic_url || defaultImage(),
    shopping_time_start: '8:00',
    shopping_time_end: '24:00',
    min_price: asset.min_price || 0,
    min_price_tip: 'Min ¥' + String(asset.min_price || 0),
    shipping_fee: asset.shipping_fee || 0,
    shipping_fee_tip: 'Delivery ¥' + String(asset.shipping_fee || 0),
    bulletin: asset.bulletin || '',
    address: asset.address || '',
    call_center: asset.phone || '',
    distance: '',
    average_price_tip: 'Avg ¥20',
    comment_number: current && current.comment_number ? current.comment_number : 0,
    lng: current && current.lng ? current.lng : '113.854074',
    lat: current && current.lat ? current.lat : '22.901119',
    created_at: current && current.created_at ? current.created_at : now(),
    discounts2: current && current.discounts2 ? current.discounts2 : []
  };
  db.restaurants.update({id: restaurantId}, {$set: doc}, {upsert: true});
  return db.restaurants.findOne({id: restaurantId});
}
function ensureRestaurantByName(name) {
  var restaurant = restaurantByName(name);
  if (restaurant) return restaurant;
  return ensureRestaurant({kind: 'meituan_restaurant', app: 'Meituan', name: name});
}
function ensureCategory(restaurant, name) {
  var category = categoryByRestaurantAndName(restaurant.id, name);
  if (category) return category;
  var id = nextId('category_id');
  db.categories.insert({id: id, name: name, restaurant_id: restaurant.id, created_at: now(), spus: []});
  return db.categories.findOne({id: id});
}
function ensureFood(asset) {
  var restaurant = ensureRestaurantByName(asset.restaurant_name);
  var category = ensureCategory(restaurant, asset.category_name || 'Asset Check');
  var current = foodByRestaurantAndName(restaurant.id, asset.name);
  var foodId = asset.food_id || (current ? current.id : nextId('food_id'));
  var skuId = asset.sku_id || (current && current.skus && current.skus[0] ? current.skus[0].id : nextId('sku_id'));
  var skuObjectId = current && current.skus && current.skus[0] ? current.skus[0]._id : new ObjectId();
  var doc = {
    id: foodId,
    restaurant_id: restaurant.id,
    category_id: category.id,
    name: asset.name,
    praise_num: current && current.praise_num ? current.praise_num : 0,
    praise_content: asset.description || '',
    month_saled: asset.month_saled || 0,
    month_saled_content: String(asset.month_saled || 0),
    pic_url: asset.pic_url || defaultImage(),
    created_at: current && current.created_at ? current.created_at : now(),
    skus: [{description: asset.description || '', price: String(asset.price), id: skuId, _id: skuObjectId}],
    attrs: [],
    status_remind_list: []
  };
  db.foods.update({id: foodId}, {$set: doc}, {upsert: true});
  var food = db.foods.findOne({id: foodId});
  db.categories.update({id: category.id}, {$addToSet: {spus: food._id}});
  return food;
}
function ensureAddress(asset) {
  var current = addressByName(asset.user_id, asset.name);
  var addressId = current ? current.id : nextId('address_id');
  var doc = {
    id: addressId,
    name: asset.name,
    gender: asset.gender || 'male',
    phone: asset.phone,
    address: asset.address,
    address_detail: asset.address_detail,
    house_number: asset.address_detail,
    title: asset.label || 'Office',
    province: asset.province || '',
    city: asset.city || '',
    user_id: asset.user_id,
    created_at: current && current.created_at ? current.created_at : now()
  };
  db.addresses.update({id: addressId}, {$set: doc}, {upsert: true});
  return db.addresses.findOne({id: addressId});
}
function applyCartItem(asset) {
  var restaurant = ensureRestaurantByName(asset.restaurant_name);
  var food = foodByRestaurantAndName(restaurant.id, asset.food_name);
  if (!food) throw new Error('Meituan food not found: ' + asset.food_name);
  var sku = food.skus[0];
  var current = db.shoppingcarts.findOne({user_id: asset.user_id, restaurant_id: restaurant.id, sku_id: sku.id});
  var cartId = current ? current.id : nextId('shopping_cart_id');
  db.shoppingcarts.update({id: cartId}, {$set: {id: cartId, restaurant_id: restaurant.id, sku_id: sku.id, name: food.name, price: Number(sku.price), spec: asset.spec || '', num: asset.quantity || 1, user_id: asset.user_id}}, {upsert: true});
}
function applyOrder(asset) {
  var restaurant = ensureRestaurantByName(asset.restaurant_name);
  var address = addressByName(asset.user_id, asset.address_name);
  if (!address) throw new Error('Meituan address not found: ' + asset.address_name);
  var foods = [];
  var total = 0;
  asset.foods.forEach(function(item) {
    var food = foodByRestaurantAndName(restaurant.id, item.food_name);
    if (!food) throw new Error('Meituan order food not found: ' + item.food_name);
    var sku = food.skus[0];
    var price = item.price == null ? Number(sku.price) : Number(item.price);
    var num = item.quantity || 1;
    total += price * num;
    foods.push({name: food.name, price: price, num: num, total_price: String(price * num), spec: item.spec || '', pic_url: food.pic_url || defaultImage(), _id: new ObjectId()});
  });
  var orderId = asset.order_id || null;
  var existing = orderId ? db.orders.findOne({id: orderId}) : db.orders.findOne({user_numeric_id: asset.user_id, restaurant_id: restaurant.id, remark: asset.remark || '', status: asset.status || 'Unpaid', 'foods.name': foods[0].name});
  if (!orderId) orderId = existing ? existing.id : nextId('order_id');
  var user = userById(asset.user_id);
  db.orders.update({id: orderId}, {$set: {
    id: orderId,
    total_price: total,
    address: address._id,
    user_id: user ? user._id : asset.user_id,
    user_numeric_id: asset.user_id,
    remark: asset.remark || '',
    restaurant_id: restaurant.id,
    status: asset.status || 'Unpaid',
    code: asset.code == null ? 0 : asset.code,
    restaurant: restaurant._id,
    shipping_fee: restaurant.shipping_fee || 0,
    create_time_timestamp: asset.created_at_ms == null ? String(Math.floor(Date.now() / 1000)) : assetSeconds(asset.created_at_ms),
    create_time: asset.created_at_ms == null ? (existing && existing.create_time ? existing.create_time : now()) : assetDate(asset.created_at_ms),
    foods: foods,
    pay_remain_time: '900',
    delivery_status: asset.delivery_status == null ? 0 : asset.delivery_status,
    has_comment: asset.has_comment == null ? false : asset.has_comment
  }}, {upsert: true});
}
function applyCollection(asset) {
  var restaurant = ensureRestaurantByName(asset.restaurant_name);
  db.collections.update({user_id: asset.user_id, restaurant_id: restaurant.id}, {$set: {user_id: asset.user_id, restaurant_id: restaurant.id, restaurant: restaurant._id, create_time: now()}}, {upsert: true});
}
function applyComment(asset) {
  var restaurant = ensureRestaurantByName(asset.restaurant_name);
  var current = db.comments.findOne({user_id: asset.user_id, restaurant_id: restaurant.id, comment_data: asset.content});
  var id = current ? current.id : nextId('comment_id');
  db.comments.update({id: id}, {$set: {
    id: id,
    user_id: asset.user_id,
    user_name: asset.user_name,
    avatar: defaultAvatar(),
    restaurant_id: restaurant.id,
    restaurant: restaurant._id,
    comment_data: asset.content,
    order_id: asset.order_id || id,
    food_score: asset.food_score || 5,
    delivery_score: asset.delivery_score || 5,
    quality_score: 0,
    pack_score: 0,
    pic_url: [],
    add_comment_list: [],
    comment_time: asset.created_at_ms == null ? (current && current.comment_time ? current.comment_time : now()) : assetDate(asset.created_at_ms)
  }}, {upsert: true});
  if (asset.order_id != null) {
    db.orders.update({id: asset.order_id}, {$set: {has_comment: true}});
  }
}
function applyAsset(asset) {
  if (asset.kind === 'meituan_user') ensureUser(asset);
  else if (asset.kind === 'meituan_restaurant') ensureRestaurant(asset);
  else if (asset.kind === 'meituan_food') ensureFood(asset);
  else if (asset.kind === 'meituan_address') ensureAddress(asset);
  else if (asset.kind === 'meituan_cart_item') applyCartItem(asset);
  else if (asset.kind === 'meituan_order') applyOrder(asset);
  else if (asset.kind === 'meituan_collection') applyCollection(asset);
  else if (asset.kind === 'meituan_comment') applyComment(asset);
  else throw new Error('Unsupported Meituan asset kind: ' + asset.kind);
}
function simpleDoc(doc) {
  if (!doc) return null;
  var item = clone(doc);
  delete item._id;
  delete item.__v;
  return item;
}
function currentAsset(asset) {
  if (asset.kind === 'meituan_user') return simpleDoc(asset.user_id ? userById(asset.user_id) : db.admins.findOne({username: asset.username}));
  if (asset.kind === 'meituan_restaurant') return simpleDoc(restaurantByName(asset.name));
  if (asset.kind === 'meituan_food') { var r = restaurantByName(asset.restaurant_name); return r ? simpleDoc(foodByRestaurantAndName(r.id, asset.name)) : null; }
  if (asset.kind === 'meituan_address') return simpleDoc(addressByName(asset.user_id, asset.name));
  if (asset.kind === 'meituan_cart_item') { var cr = restaurantByName(asset.restaurant_name); var f = cr ? foodByRestaurantAndName(cr.id, asset.food_name) : null; var sku = f && f.skus ? f.skus[0] : null; return sku ? simpleDoc(db.shoppingcarts.findOne({user_id: asset.user_id, restaurant_id: cr.id, sku_id: sku.id})) : null; }
  if (asset.kind === 'meituan_order') { if (asset.order_id) return simpleDoc(db.orders.findOne({id: asset.order_id})); var rr = restaurantByName(asset.restaurant_name); if (!rr) return null; var user = userById(asset.user_id); var query = {restaurant_id: rr.id, status: asset.status || 'Unpaid'}; query.$or = user ? [{user_numeric_id: asset.user_id}, {user_id: user._id}] : [{user_numeric_id: asset.user_id}]; var latest = null; var cursor = db.orders.find(query).sort({create_time_timestamp: -1, id: -1}); while (cursor.hasNext()) { var candidate = simpleDoc(cursor.next()); if (latest === null) latest = candidate; if (exactAsset(asset, candidate)) return candidate; } return latest; }
  if (asset.kind === 'meituan_collection') { var xr = restaurantByName(asset.restaurant_name); return xr ? simpleDoc(db.collections.findOne({user_id: asset.user_id, restaurant_id: xr.id})) : null; }
  if (asset.kind === 'meituan_comment') { var tr = restaurantByName(asset.restaurant_name); if (!tr) return null; var cursor = db.comments.find({user_id: asset.user_id, restaurant_id: tr.id}).sort({comment_time: -1, id: -1}); while (cursor.hasNext()) { var comment = cursor.next(); if (textEq(comment.comment_data, asset.content)) return simpleDoc(comment); } return null; }
  throw new Error('Unsupported Meituan asset kind: ' + asset.kind);
}
function exactAsset(asset, current) {
  if (!current) return false;
  if (asset.kind === 'meituan_user') return current.username === asset.username && (!asset.user_id || current.id === asset.user_id) && current.status === (asset.status == null ? 1 : asset.status);
  if (asset.kind === 'meituan_restaurant') return textEq(current.name, asset.name) && textEq(current.third_category, asset.category || 'Asset Check') && Number(current.min_price || 0) === Number(asset.min_price || 0);
  if (asset.kind === 'meituan_food') return textEq(current.name, asset.name) && Number(current.skus[0].price) === Number(asset.price);
  if (asset.kind === 'meituan_address') { var details = [current.address_detail || '', current.house_number || ''].map(function(value) { return String(value).trim(); }); var label = current.title || current.label || ''; var expectedLabel = asset.label || 'Office'; return textEq(current.name, asset.name) && current.phone === asset.phone && textEq(current.address, asset.address) && details.indexOf(String(asset.address_detail || '').trim()) !== -1 && textEq(label, expectedLabel); }
  if (asset.kind === 'meituan_cart_item') return current.name === asset.food_name && Number(current.num) === Number(asset.quantity || 1);
  if (asset.kind === 'meituan_order') { var orderFoods = current.foods || []; var foodMatches = (asset.foods || []).every(function(expected) { return orderFoods.some(function(actual) { var ok = textEq(actual.name, expected.food_name) && Number(actual.num || 0) === Number(expected.quantity || 1); if (expected.price != null) ok = ok && Number(actual.price) === Number(expected.price); return ok; }); }); var ok = current.status === (asset.status || 'Unpaid') && orderFoods.length === asset.foods.length && foodMatches; if (asset.code != null) ok = ok && Number(current.code || 0) === Number(asset.code); if (asset.delivery_status != null) { var currentDeliveryStatus = Number(current.delivery_status || 0); var expectedDeliveryStatus = Number(asset.delivery_status); if (expectedDeliveryStatus === 1 && (asset.status || 'Unpaid') === 'Payment successful') ok = ok && currentDeliveryStatus >= 1; else ok = ok && currentDeliveryStatus === expectedDeliveryStatus; } if (asset.has_comment != null) ok = ok && Boolean(current.has_comment) === Boolean(asset.has_comment); if (asset.created_at_ms != null) ok = ok && Math.abs(Number(current.create_time_timestamp || 0) * 1000 - Number(asset.created_at_ms)) <= 1000; return ok; }
  if (asset.kind === 'meituan_collection') return current.user_id === asset.user_id;
  if (asset.kind === 'meituan_comment') { var ok = textEq(current.comment_data, asset.content) && Number(current.food_score) === Number(asset.food_score || 5) && Number(current.delivery_score) === Number(asset.delivery_score || 5); if (asset.created_at_ms != null) ok = ok && Math.abs(dateMs(current.comment_time) - Number(asset.created_at_ms)) <= 1000; return ok; }
  return false;
}
function labelFor(asset) {
  if (asset.kind === 'meituan_user') return 'meituan_user:' + asset.username;
  if (asset.kind === 'meituan_restaurant') return 'meituan_restaurant:' + asset.name;
  if (asset.kind === 'meituan_food') return 'meituan_food:' + asset.name;
  if (asset.kind === 'meituan_address') return 'meituan_address:' + asset.name;
  if (asset.kind === 'meituan_cart_item') return 'meituan_cart_item:' + asset.food_name;
  if (asset.kind === 'meituan_order') return 'meituan_order:' + (asset.order_id || asset.restaurant_name);
  if (asset.kind === 'meituan_collection') return 'meituan_collection:' + asset.restaurant_name;
  if (asset.kind === 'meituan_comment') return 'meituan_comment:' + asset.content;
  return asset.kind;
}
function probeAsset(asset) {
  var current = currentAsset(asset);
  return {label: labelFor(asset), identity_exists: current !== null, exact_match: exactAsset(asset, current), current: current};
}
'''


def _password_hash(password: str) -> str:
    first = base64.b64encode(hashlib.md5(password.encode("utf-8")).digest())
    return base64.b64encode(hashlib.md5(first).digest()).decode("ascii")


def _asset_json(asset: Any) -> str:
    data = asset.model_dump() if hasattr(asset, "model_dump") else dict(asset)
    if data.get("kind") == "meituan_user":
        data["password"] = _password_hash(data.get("password") or "123456")
    return json.dumps(data, ensure_ascii=False)


def _run_asset_script(client: AndroidController, asset: Any, action: str) -> str:
    script = f"""
set -euo pipefail
cat > /tmp/gma_meituan_asset.js <<'INNER_JS'
{_RUNTIME}
var asset = {_asset_json(asset)};
if ({json.dumps(action)} === 'apply') {{
  applyAsset(asset);
}} else {{
  print(JSON.stringify(probeAsset(asset)));
}}
INNER_JS
docker exec -i meituan-mongo mongo takeaway --quiet < /tmp/gma_meituan_asset.js
"""
    return run_bash(client, script, timeout=120)


def ensure_meituan_backend(client: AndroidController) -> None:
    _ensure_meituan_backend(client)


def meituan_login_user_asset(
    *,
    username: str = MEITUAN_LOGIN_USERNAME,
    password: str = MEITUAN_LOGIN_PASSWORD,
    user_id: int | None = MEITUAN_LOGIN_USER_ID,
    city: str = MEITUAN_LOGIN_CITY,
) -> dict[str, Any]:
    return {
        "kind": "meituan_user",
        "app": "Meituan",
        "username": username,
        "password": password,
        "user_id": user_id,
        "city": city,
        "status": 1,
    }


def ensure_meituan_login_user(
    client: AndroidController,
    *,
    username: str = MEITUAN_LOGIN_USERNAME,
    password: str = MEITUAN_LOGIN_PASSWORD,
    user_id: int | None = None,
) -> None:
    ensure_meituan_backend(client)
    if user_id is None and username == MEITUAN_LOGIN_USERNAME:
        user_id = MEITUAN_LOGIN_USER_ID
    _run_asset_script(
        client,
        meituan_login_user_asset(username=username, password=password, user_id=user_id),
        "apply",
    )


def launch_meituan_installed_app(
    client: AndroidController,
    *,
    username: str | None = None,
    password: str | None = None,
) -> None:
    if username is not None or password is not None:
        launch_webapp_with_login_extras(
            client,
            "gma.webapp.meituan",
            username=username,
            password=password,
        )
        return
    device = getattr(client, "device", "emulator-5554")
    args = [
        "adb",
        "-s",
        str(device),
        "shell",
        "am",
        "start",
        "-a",
        MEITUAN_WEBAPP_ACTION,
        "-n",
        MEITUAN_WEBAPP_COMPONENT,
        "--es",
        "org.chromium.chrome.browser.webapp_id",
        MEITUAN_WEBAPP_ID,
        "--es",
        "org.chromium.chrome.browser.webapp_url",
        MEITUAN_WEB_URL,
        "--es",
        "org.chromium.chrome.browser.webapp_scope",
        MEITUAN_WEB_URL,
        "--es",
        "org.chromium.chrome.browser.webapp_name",
        MEITUAN_WEBAPP_NAME,
        "--es",
        "org.chromium.chrome.browser.webapp_short_name",
        MEITUAN_WEBAPP_NAME,
        "--ei",
        "org.chromium.chrome.browser.webapp_display_mode",
        "3",
        "--ei",
        "org.chromium.chrome.browser.webapp_source",
        "12",
    ]
    command = " ".join(shlex.quote(arg) for arg in args)
    run_bash(client, command, timeout=30)


def login_meituan_app(
    client: AndroidController,
    *,
    username: str = MEITUAN_LOGIN_USERNAME,
    password: str = MEITUAN_LOGIN_PASSWORD,
    ensure_user: bool = True,
) -> None:
    if ensure_user:
        ensure_meituan_login_user(client, username=username, password=password)
    launch_meituan_installed_app(client, username=username, password=password)


def apply_meituan_asset(client: AndroidController, asset: Any) -> None:
    ensure_meituan_backend(client)
    _run_asset_script(client, asset, "apply")


def probe_meituan_asset(client: AndroidController, asset: Any) -> dict[str, Any]:
    ensure_meituan_backend(client)
    return json.loads(_run_asset_script(client, asset, "probe"))
