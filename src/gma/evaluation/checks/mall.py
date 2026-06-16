from __future__ import annotations

import base64
import json
from typing import Any

from gma.evaluation.criteria import Criterion


def exec_python_json(client: Any, script: str, timeout: int = 60) -> dict[str, Any]:
    """Execute a Python snippet in the environment container and parse its JSON output."""
    output = client.exec("python3 - <<\x27PY\x27\n" + script + "\nPY", timeout=timeout)
    for line in reversed(output.splitlines()):
        line = line.strip()
        if not line:
            continue
        return json.loads(line)
    raise ValueError("Python snippet did not emit JSON output")


_PROBE_SCRIPT = r'''
import base64
import json
import shlex
import subprocess

payload = json.loads(base64.b64decode("__PAYLOAD__").decode("utf-8"))

MYSQL = [
    "docker", "exec", "-i", "mall-mysql", "mysql",
    "-umall", "-pmall_pass_2025", "--default-character-set=utf8mb4", "mall",
]
QUERY = MYSQL + ["--batch", "--raw", "--skip-column-names"]


def q(value):
    if value is None:
        return "NULL"
    return "'" + str(value).replace("\\", "\\\\").replace("'", "''").replace("\0", "") + "'"


def rows(sql):
    out = subprocess.check_output(QUERY + ["-e", sql], text=True)
    return [["" if cell == "NULL" else cell for cell in line.split("\t")] for line in out.splitlines() if line.strip()]


def scalar(sql):
    data = rows(sql)
    return data[0][0] if data and data[0] else None


def int_or_none(value):
    return int(value) if value not in (None, "") else None


def float_or_none(value):
    return float(value) if value not in (None, "") else None


def member_id(username):
    value = scalar("select id from ums_member where username = " + q(username) + " limit 1")
    return int_or_none(value)


def product_id(product_sn):
    value = scalar("select id from pms_product where product_sn = " + q(product_sn) + " limit 1")
    return int_or_none(value)


def mongo_eval(js):
    quoted = shlex.quote(js)
    cmd = (
        "if command -v mongosh >/dev/null 2>&1; then "
        "mongosh mall-port --quiet --eval " + quoted + "; "
        "else mongo mall-port --quiet --eval " + quoted + "; fi"
    )
    return subprocess.check_output(["docker", "exec", "mall-mongo", "sh", "-lc", cmd], text=True).strip()


def find_favorite():
    mid = member_id(payload["member_username"])
    pid = product_id(payload["product_sn"])
    if not mid or not pid:
        return {"exists": False, "member_id": mid, "product_id": pid, "favorite": None}
    js = """
var midLong = NumberLong(%(mid_json)s);
var pidLong = NumberLong(%(pid_json)s);
var midNum = Number(%(mid_json)s);
var pidNum = Number(%(pid_json)s);
var d = db.memberProductCollection.findOne({memberId: {$in: [midLong, midNum]}, productId: {$in: [pidLong, pidNum]}});
if (!d) {
  print('null');
} else {
  print(JSON.stringify({
    memberId: Number(d.memberId),
    productId: Number(d.productId),
    productName: d.productName || null,
    productSubTitle: d.productSubTitle || null,
    productPrice: d.productPrice == null ? null : Number(d.productPrice)
  }));
}
""" % {"mid_json": json.dumps(str(mid)), "pid_json": json.dumps(str(pid))}
    raw = mongo_eval(js)
    doc = None if not raw or raw == "null" else json.loads(raw.splitlines()[-1])
    return {"exists": doc is not None, "member_id": mid, "product_id": pid, "favorite": doc}


def find_checkout_order():
    mid = member_id(payload["member_username"])
    if not mid:
        return {"exists": False, "member_id": None, "order": None}
    data = rows(
        "select o.id, o.order_sn, o.status, o.member_username, o.receiver_name, o.receiver_phone, "
        "o.receiver_province, o.receiver_city, o.receiver_region, o.receiver_detail_address, "
        "o.pay_amount, i.product_sn, i.product_quantity, i.product_name "
        "from oms_order o join oms_order_item i on i.order_id = o.id "
        "where o.member_id = " + str(mid) + " and i.product_sn = " + q(payload["product_sn"]) + " "
        "order by o.id desc limit 1"
    )
    if not data:
        return {"exists": False, "member_id": mid, "order": None}
    r = data[0]
    return {
        "exists": True,
        "member_id": mid,
        "order": {
            "id": int(r[0]),
            "order_sn": r[1],
            "status": int_or_none(r[2]),
            "member_username": r[3],
            "receiver_name": r[4],
            "receiver_phone": r[5],
            "receiver_province": r[6] or None,
            "receiver_city": r[7] or None,
            "receiver_region": r[8] or None,
            "receiver_detail_address": r[9],
            "pay_amount": float_or_none(r[10]),
            "product_sn": r[11],
            "quantity": int_or_none(r[12]),
            "product_name": r[13],
        },
    }


def find_review():
    data = rows(
        "select o.id, o.order_sn, o.status, o.comment_time, i.product_sn, i.product_name, "
        "c.id, c.star, c.content, c.show_status, c.create_time "
        "from oms_order o join oms_order_item i on i.order_id = o.id "
        "left join pms_comment c on c.order_id = o.id and c.order_item_id = i.id "
        "where o.order_sn = " + q(payload["order_sn"]) + " and i.product_sn = " + q(payload["product_sn"]) + " "
        "order by c.id desc limit 1"
    )
    if not data:
        return {"exists": False, "review": None}
    r = data[0]
    return {
        "exists": bool(r[6]),
        "review": {
            "order_id": int(r[0]),
            "order_sn": r[1],
            "order_status": int_or_none(r[2]),
            "comment_time": r[3] or None,
            "product_sn": r[4],
            "product_name": r[5],
            "comment_id": int_or_none(r[6]),
            "star": int_or_none(r[7]),
            "content": r[8] or None,
            "show_status": int_or_none(r[9]),
            "create_time": r[10] or None,
        },
    }


kind = payload["kind"]
if kind == "favorite":
    print(json.dumps(find_favorite(), ensure_ascii=False))
elif kind == "checkout":
    print(json.dumps(find_checkout_order(), ensure_ascii=False))
elif kind == "review":
    print(json.dumps(find_review(), ensure_ascii=False))
else:
    raise RuntimeError("Unsupported Mall probe kind: " + kind)
'''


def _probe(client: Any, payload: dict[str, Any]) -> dict[str, Any]:
    encoded = base64.b64encode(json.dumps(payload, ensure_ascii=False).encode("utf-8")).decode("ascii")
    script = _PROBE_SCRIPT.replace("__PAYLOAD__", encoded)
    return exec_python_json(client, script, timeout=120)


class MallProductFavorited(Criterion):
    def __init__(self, *, member_username: str, product_sn: str, product_name: str | None = None, weight: float = 1.0):
        super().__init__(weight=weight)
        self.member_username = member_username
        self.product_sn = product_sn
        self.product_name = product_name

    @property
    def name(self) -> str:
        return f"MallProductFavorited({self.member_username}:{self.product_sn})"

    def evaluate(self, client) -> Any:
        state = _probe(
            client,
            {
                "kind": "favorite",
                "member_username": self.member_username,
                "product_sn": self.product_sn,
            },
        )
        favorite = state.get("favorite")
        if not state.get("exists"):
            return self._fail(f"favorite not found. Current: {state}")
        if self.product_name and favorite.get("productName") != self.product_name:
            return self._fail(f"favorite product name mismatch. Current: {favorite}")
        return self._pass(f"favorite exists: {favorite}")


class MallCheckoutOrderCreated(Criterion):
    def __init__(
        self,
        *,
        member_username: str,
        product_sn: str,
        quantity: int = 1,
        expected_status: int | None = 0,
        receiver_name: str | None = None,
        weight: float = 1.0,
    ):
        super().__init__(weight=weight)
        self.member_username = member_username
        self.product_sn = product_sn
        self.quantity = quantity
        self.expected_status = expected_status
        self.receiver_name = receiver_name

    @property
    def name(self) -> str:
        return f"MallCheckoutOrderCreated({self.member_username}:{self.product_sn})"

    def evaluate(self, client) -> Any:
        state = _probe(
            client,
            {
                "kind": "checkout",
                "member_username": self.member_username,
                "product_sn": self.product_sn,
            },
        )
        order = state.get("order")
        if not state.get("exists") or not order:
            return self._fail(f"checkout order not found. Current: {state}")
        if order.get("quantity") != self.quantity:
            return self._fail(f"order quantity mismatch. Expected {self.quantity}, current: {order}")
        if self.expected_status is not None and order.get("status") != self.expected_status:
            return self._fail(f"order status mismatch. Expected {self.expected_status}, current: {order}")
        if self.receiver_name and order.get("receiver_name") != self.receiver_name:
            return self._fail(f"receiver mismatch. Expected {self.receiver_name}, current: {order}")
        return self._pass(f"checkout order exists: {order}")


class MallOrderReviewed(Criterion):
    def __init__(
        self,
        *,
        order_sn: str,
        product_sn: str,
        content: str,
        star: int,
        weight: float = 1.0,
    ):
        super().__init__(weight=weight)
        self.order_sn = order_sn
        self.product_sn = product_sn
        self.content = content
        self.star = star

    @property
    def name(self) -> str:
        return f"MallOrderReviewed({self.order_sn})"

    def evaluate(self, client) -> Any:
        state = _probe(
            client,
            {
                "kind": "review",
                "order_sn": self.order_sn,
                "product_sn": self.product_sn,
            },
        )
        review = state.get("review")
        if not state.get("exists") or not review:
            return self._fail(f"review not found. Current: {state}")
        if review.get("star") != self.star:
            return self._fail(f"review star mismatch. Expected {self.star}, current: {review}")
        if review.get("content") != self.content:
            return self._fail(f"review content mismatch. Expected {self.content!r}, current: {review}")
        if not review.get("comment_time"):
            return self._fail(f"order comment_time was not set. Current: {review}")
        return self._pass(f"review exists: {review}")
