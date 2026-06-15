from __future__ import annotations

from gma.apps.meituan import MEITUAN_LOGIN_CITY, MEITUAN_LOGIN_USER_ID, MEITUAN_LOGIN_USERNAME
from gma.assets import ElementXMessageAsset, ElementXRoomAsset, ElementXUserAsset, MeituanAddressAsset, MeituanOrderAsset, MeituanOrderFood, MeituanUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask

ROOM = "w4-row232-first-group"
SUMMARY = "Restaurant: KFC; Items: Classic signature breakfast three-piece set, Pork fillet panini 2-piece set; Total: 27.33."
EXPECTED_ORDER = MeituanOrderAsset(user_id=MEITUAN_LOGIN_USER_ID, restaurant_name="KFC", foods=[MeituanOrderFood(food_name="Classic signature breakfast three-piece set", quantity=1), MeituanOrderFood(food_name="Pork fillet panini 2-piece set", quantity=1)], status="Payment successful", address_name="Default KFC Receiver", code=200, delivery_status=1)


class MeituanKfcOrderElementXGroupSummaryTask(BaseTask):
    apps = {"Meituan", "ElementX"}
    difficulty = "hard"
    snapshot = "gma_ready_state"
    assets = (
        MeituanUserAsset(username=MEITUAN_LOGIN_USERNAME, password="123456", user_id=MEITUAN_LOGIN_USER_ID, city=MEITUAN_LOGIN_CITY, status=1),
        MeituanAddressAsset(user_id=MEITUAN_LOGIN_USER_ID, name="Default KFC Receiver", phone="5550101085", address="Default KFC Address", address_detail="Room 232", label="Home", city=MEITUAN_LOGIN_CITY),
        ElementXUserAsset(username="w4-row232-member", password="password", display_name="First Group Member"),
        ElementXRoomAsset(name="First Group", room_type="group", creator_username="testuser", creator_password="testpass123", members=["w4-row232-member"], alias_localpart=ROOM, topic="Food summaries"),
    )
    goal = (
        "Open Meituan, enter KFC, add Classic signature breakfast three-piece set and Pork fillet panini 2-piece set to the cart, and use the default address and delivery time, and pay with Alipay. "
        "Then open ElementX and send this exact message to the first group chat: \"Restaurant: KFC; Items: Classic signature breakfast three-piece set, Pork fillet panini 2-piece set; Total: 27.33.\""
    )

    def criteria(self):
        return [AssetExists(EXPECTED_ORDER, task=self), AssetExists(ElementXMessageAsset(room=ROOM, sender_username="testuser", sender_password="testpass123", text=SUMMARY), task=self)]
