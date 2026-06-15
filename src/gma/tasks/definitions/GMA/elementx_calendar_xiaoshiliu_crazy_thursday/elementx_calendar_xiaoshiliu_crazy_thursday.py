from __future__ import annotations

from gma.apps.elementx import elementx_user_id
from gma.apps.xiaoshiliu import XIAOSHILIU_DEFAULT_AVATAR, XIAOSHILIU_LOGIN_USER_ID
from gma.assets import CalendarEventAsset, ElementXMessageAsset, ElementXRoomAsset, ElementXUserAsset, XiaoShiLiuCollectionAsset, XiaoShiLiuLikeAsset, XiaoShiLiuPostAsset, XiaoShiLiuUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask
from datetime import UTC, datetime

from gma.apps.travel import (
    TRAVEL_LOGIN_EMAIL,
    TRAVEL_LOGIN_FIRST_NAME,
    TRAVEL_LOGIN_LAST_NAME,
    TRAVEL_LOGIN_PASSWORD,
    TRAVEL_LOGIN_USERNAME,
    login_travel_app,
)
from gma.assets import TravelUserAsset

TRAVEL_USER = TravelUserAsset(
    email=TRAVEL_LOGIN_EMAIL,
    username=TRAVEL_LOGIN_USERNAME,
    password=TRAVEL_LOGIN_PASSWORD,
    first_name=TRAVEL_LOGIN_FIRST_NAME,
    last_name=TRAVEL_LOGIN_LAST_NAME,
)


def dt_ms(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> int:
    return int(datetime(year, month, day, hour, minute, tzinfo=UTC).timestamp() * 1000)


def open_travel(client) -> None:
    login_travel_app(
        client,
        email=TRAVEL_LOGIN_EMAIL,
        username=TRAVEL_LOGIN_USERNAME,
        password=TRAVEL_LOGIN_PASSWORD,
        ensure_user=False,
    )


USER01 = "jordan-lee"
ROOM_ALIAS = "jordan-lee-crazy-thursday"
MESSAGE = "I plan to search for information about Crazy Thursday and set an alarm for this Thursday. Do you have any other ideas?"
EVENT = CalendarEventAsset(title="Crazy Thursday", start_ms=dt_ms(2026, 10, 1, 8), end_ms=dt_ms(2026, 10, 1, 8), location="Denver, Colorado", timezone="UTC")
AUTHOR_IDS = ["w4-row206-a", "w4-row206-b", "w4-row206-c"]
POSTS = (
    XiaoShiLiuPostAsset(author_user_id=AUTHOR_IDS[0], title="Crazy Thursday Meal Ideas", content="A popular meal idea list with several lunch options.", category="Food", tags=["crazy-thursday"], image_urls=["/assets/elementx-calendar-xiaoshiliu-crazy-thursday-crazy-a.png"], min_image_count=1, created_at_ms=1790845800000),
    XiaoShiLiuPostAsset(author_user_id=AUTHOR_IDS[1], title="Crazy Thursday Group Plan", content="A group plan post with the strongest save count among tied like counts.", category="Food", tags=["crazy-thursday"], image_urls=["/assets/elementx-calendar-xiaoshiliu-crazy-thursday-crazy-b.png"], min_image_count=1, created_at_ms=1790845500000),
    XiaoShiLiuPostAsset(author_user_id=AUTHOR_IDS[2], title="Crazy Thursday Snack Notes", content="A smaller snack note for the same search.", category="Food", tags=["crazy-thursday"], image_urls=["/assets/elementx-calendar-xiaoshiliu-crazy-thursday-crazy-c.png"], min_image_count=1, created_at_ms=1790845200000),
)
AUTHORS = tuple(XiaoShiLiuUserAsset(user_id=uid, nickname=f"Crazy Thursday Author {idx + 1}", email=f"crazy-row206-{idx}@example.com", avatar=XIAOSHILIU_DEFAULT_AVATAR) for idx, uid in enumerate(AUTHOR_IDS))
SEEDED_INTERACTIONS = tuple(
    XiaoShiLiuLikeAsset(user_id=f"w4-row206-like-{idx}", post_title=POSTS[0].title, post_author_user_id=AUTHOR_IDS[0]) for idx in range(4)
) + tuple(
    XiaoShiLiuLikeAsset(user_id=f"w4-row206-like-b-{idx}", post_title=POSTS[1].title, post_author_user_id=AUTHOR_IDS[1]) for idx in range(4)
) + tuple(
    XiaoShiLiuLikeAsset(user_id=f"w4-row206-like-c-{idx}", post_title=POSTS[2].title, post_author_user_id=AUTHOR_IDS[2]) for idx in range(2)
) + tuple(
    XiaoShiLiuCollectionAsset(user_id=f"w4-row206-save-a-{idx}", post_title=POSTS[0].title, post_author_user_id=AUTHOR_IDS[0]) for idx in range(1)
) + tuple(
    XiaoShiLiuCollectionAsset(user_id=f"w4-row206-save-b-{idx}", post_title=POSTS[1].title, post_author_user_id=AUTHOR_IDS[1]) for idx in range(3)
)
EXPECTED_MESSAGE = ElementXMessageAsset(room=elementx_user_id(USER01), sender_username="testuser", sender_password="testpass123", text=MESSAGE)
EXPECTED_LIKE = XiaoShiLiuLikeAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=POSTS[1].title, post_author_user_id=AUTHOR_IDS[1])

class ElementXCalendarXiaoShiLiuCrazyThursdayTask(BaseTask):
    apps = {"ElementX", "Calendar", "XiaoShiLiu"}
    difficulty = "hard"
    snapshot = "gma_ready_state"
    assets = (ElementXUserAsset(username=USER01, display_name="Jordan Lee"), ElementXRoomAsset(name="Jordan Lee", room_type="dm", creator_username="testuser", creator_password="testpass123", members=[USER01], alias_localpart=ROOM_ALIAS), *AUTHORS, *POSTS, *SEEDED_INTERACTIONS)
    goal = (
        "Open ElementX, find the conversation with Jordan Lee, and send \"I plan to search for information about Crazy Thursday and set an alarm for this Thursday. Do you have any other ideas?\". "
        "Then create a Calendar event titled \"Crazy Thursday\" at Denver, Colorado for Thursday, October 1, 2026 at 8:00 AM. "
        "Finally search XiaoShiLiu for \"Crazy Thursday\" and like the most-liked post among the top three; if likes tie, choose the one with more saves."
    )

    def criteria(self):
        return [AssetExists(EXPECTED_MESSAGE, task=self), AssetExists(EVENT, task=self), AssetExists(EXPECTED_LIKE, task=self)]
