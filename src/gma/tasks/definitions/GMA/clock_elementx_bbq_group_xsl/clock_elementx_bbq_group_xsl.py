from __future__ import annotations

from gma.apps.xiaoshiliu import XIAOSHILIU_DEFAULT_AVATAR, XIAOSHILIU_LOGIN_USER_ID
from gma.assets import AlarmAsset, ElementXMessageAsset, ElementXRoomAsset, ElementXUserAsset, XiaoShiLiuCollectionAsset, XiaoShiLiuLikeAsset, XiaoShiLiuPostAsset, XiaoShiLiuUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask



ROOM_ALIAS = "w4-row224-dinner-invitation"
MESSAGE = "BBQ at 8 PM on Saturday"
AUTHOR_ID = "w4-row224-bbq-author"
POSTS = tuple(
    XiaoShiLiuPostAsset(author_user_id=AUTHOR_ID, title=f"Brooklyn BBQ Note {i}", content="A Brooklyn BBQ place with likes and useful dinner details.", category="Food", tags=["Brooklyn BBQ"], image_urls=["/assets/clock-elementx-bbq-group-xsl-brooklyn-bbq.png"], min_image_count=1, created_at_ms=1790845200000 - i * 60000)
    for i in range(1, 4)
)
SEEDED_LIKES = tuple(XiaoShiLiuLikeAsset(user_id=f"w4-row224-like-{i}", post_title=post.title, post_author_user_id=AUTHOR_ID) for i, post in enumerate(POSTS, start=1))
COLLECTIONS = tuple(XiaoShiLiuCollectionAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=post.title, post_author_user_id=AUTHOR_ID) for post in POSTS)

class ClockElementXBbqGroupXslTask(BaseTask):
    apps = {"Clock", "ElementX", "XiaoShiLiu"}
    difficulty = "hard"
    category = ['Selection / Optimization Tasks']
    snapshot = "gma_ready_state"
    assets = (
        ElementXUserAsset(username="w4-row224-ethan-carter", password="password", display_name="Ethan Carter"),
        ElementXUserAsset(username="w4-row224-olivia-brooks", password="password", display_name="Olivia Brooks"),
        XiaoShiLiuUserAsset(user_id=AUTHOR_ID, nickname="Brooklyn BBQ Desk", email="bbq-row224@example.com", avatar=XIAOSHILIU_DEFAULT_AVATAR),
        *POSTS,
        *SEEDED_LIKES,
    )
    user_interaction = "If the agent says Ethan Carter cannot be found, answer exactly: Invite Mason Taylor instead. Do not answer unrelated questions."
    goal = (
        "Open Clock and create an 8:00 PM Saturday repeating alarm labeled Weekend BBQ with vibration on. "
        "Then open ElementX, create a group room named Dinner Invitation with topic Dining, invite Ethan Carter and Olivia Brooks, and send this exact message in the group: \"BBQ at 8 PM on Saturday\". "
        "Finally open XiaoShiLiu, search for \"Brooklyn BBQ\", and save the notes that already have likes."
    )

    def criteria(self):
        return [
            AssetExists(AlarmAsset(hour=20, minute=0, label="Weekend BBQ", enabled=True, days_of_week=("saturday",), vibrate=True), task=self),
            AssetExists(ElementXRoomAsset(name="Dinner Invitation", room_type="group", creator_username="testuser", creator_password="testpass123", members=["w4-row224-ethan-carter", "w4-row224-olivia-brooks"], alias_localpart=ROOM_ALIAS, topic="Dining"), task=self),
            AssetExists(ElementXMessageAsset(room="Dinner Invitation", sender_username="testuser", sender_password="testpass123", text=MESSAGE), task=self),
            *(AssetExists(collection, task=self) for collection in COLLECTIONS),
        ]

