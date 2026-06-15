from __future__ import annotations

from gma.apps.meituan import MEITUAN_LOGIN_CITY, MEITUAN_LOGIN_USER_ID, MEITUAN_LOGIN_USERNAME
from gma.assets import ElementXMessageAsset, ElementXRoomAsset, ElementXUserAsset, MeituanCommentAsset, MeituanUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask

ROOM = "riley-park-pizza"
ADDRESS = "88 Harbor Road"
MESSAGE = "The store I just searched looks good. I've sent you the address: 88 Harbor Road."


class MeituanPizzaHutElementXAddressTask(BaseTask):
    apps = {"Meituan", "ElementX"}
    difficulty = "hard"
    category = ["Conditional Tasks", "Multi-Step Workflow Tasks"]
    snapshot = "gma_ready_state"
    assets = (
        MeituanUserAsset(username=MEITUAN_LOGIN_USERNAME, password="123456", user_id=MEITUAN_LOGIN_USER_ID, city=MEITUAN_LOGIN_CITY, status=1),
        MeituanCommentAsset(user_id=MEITUAN_LOGIN_USER_ID, user_name="Default User", restaurant_name="Pizza Hut", content="Good pizza and quick delivery.", food_score=5, delivery_score=5),
        ElementXUserAsset(username=ROOM, password="password", display_name="Riley Park"),
        ElementXRoomAsset(name="Riley Park", room_type="dm", creator_username="testuser", creator_password="testpass123", members=[ROOM], alias_localpart=ROOM),
    )
    goal = (
        'Open Meituan, search for Pizza Hut, and check its rating and address. If the store rating is at least 3.5, open ElementX '
        'and send Riley Park a message in exactly this format: "The store I just searched looks good. I\'ve sent you the address: <address>." '
        'If the store rating is below 3.5, do not send a message.'
    )

    def criteria(self):
        return [AssetExists(ElementXMessageAsset(room=ROOM, sender_username="testuser", sender_password="testpass123", text=MESSAGE), task=self)]
