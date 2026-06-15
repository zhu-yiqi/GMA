from __future__ import annotations

from gma.apps.elementx import elementx_user_id
from gma.apps.mall import MALL_LOGIN_CITY, MALL_LOGIN_NICKNAME, MALL_LOGIN_PHONE, MALL_LOGIN_USERNAME
from gma.assets import AlarmAsset, ElementXMessageAsset, ElementXRoomAsset, ElementXUserAsset, MallCartItemAsset, MallMemberAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask

ROOM = "jordan-lee-hp"
DM_ROOM = elementx_user_id(ROOM)
PRODUCT_SN = "fr0041TU"
MESSAGE = "I'm going to set an alarm; it will remind me to buy a phone. You can also contact me if you have anything else."


class ElementXMallHpLaptopAlarmTask(BaseTask):
    apps = {"ElementX", "Mall", "Clock"}
    difficulty = "hard"
    snapshot = "gma_ready_state"
    assets = (
        ElementXUserAsset(username=ROOM, password="password", display_name="Jordan Lee"),
        ElementXRoomAsset(name="Jordan Lee", room_type="dm", creator_username="testuser", creator_password="testpass123", members=[ROOM], alias_localpart=ROOM),
        MallMemberAsset(username=MALL_LOGIN_USERNAME, password="123456", nickname=MALL_LOGIN_NICKNAME, phone=MALL_LOGIN_PHONE, city=MALL_LOGIN_CITY, status=1),
    )
    goal = (
        "Open ElementX and send Jordan Lee this exact message: \"I'm going to set an alarm; it will remind me to buy a phone. "
        "You can also contact me if you have anything else.\" Then open Mall, search for HP StarBook Pro 14-inch AI laptop, and add one to the cart. "
        "Finally open Clock and create a 9:00 PM alarm with no repeat and vibration on."
    )

    def criteria(self):
        return [
            AssetExists(ElementXMessageAsset(room=DM_ROOM, sender_username="testuser", sender_password="testpass123", text=MESSAGE), task=self),
            AssetExists(MallCartItemAsset(member_username=MALL_LOGIN_USERNAME, product_sn=PRODUCT_SN, quantity=1, delete_status=False), task=self),
            AssetExists(AlarmAsset(hour=21, minute=0, enabled=True, days_of_week=(), vibrate=True), task=self),
        ]
