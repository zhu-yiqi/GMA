from __future__ import annotations

from gma.apps.xiaoshiliu import XIAOSHILIU_DEFAULT_AVATAR, XIAOSHILIU_LOGIN_USER_ID
from gma.assets import CalendarEventAsset, ContactAsset, SmsMessageAsset, XiaoShiLiuCollectionAsset, XiaoShiLiuPostAsset, XiaoShiLiuUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask
from datetime import UTC, datetime


def dt_ms(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> int:
    return int(datetime(year, month, day, hour, minute, tzinfo=UTC).timestamp() * 1000)


AUTHOR_ID = "w4-row219-rainier-author"
NEW_CONTACT = ContactAsset(name="Mount Rainier Trail Office", phone_number="5550101006", website="https://www.nps.gov/mora/")
DASHAN = ContactAsset(name="Parker Hill", phone_number="+15552190219")
EXPECTED_SMS = SmsMessageAsset(address=DASHAN.phone_number, body="Depart for hiking Mount Rainier at 6 a.m. on Thursday", box="sent", read=True)
EVENT = CalendarEventAsset(title="Hike Mount Rainier", start_ms=dt_ms(2026, 10, 8, 5), end_ms=dt_ms(2026, 10, 8, 6), description="Hike Mount Rainier", timezone="UTC")
POSTS = tuple(
    XiaoShiLiuPostAsset(author_user_id=AUTHOR_ID, title=f"Mount Rainier Hiking Guide {index:02d}", content="A practical Mount Rainier hiking guide with route, water, and timing notes.", category="Travel", tags=["Mount Rainier hiking guide"], image_urls=["/assets/contacts-parker-rainier-calendar-save-mount-rainier-guide.png"], min_image_count=1, created_at_ms=1790845200000 - index * 60000)
    for index in range(1, 6)
)
COLLECTIONS = tuple(XiaoShiLiuCollectionAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=post.title, post_author_user_id=AUTHOR_ID) for post in POSTS)


class ContactsParkerRainierCalendarSaveTask(BaseTask):
    apps = {"Contacts", "Messages", "XiaoShiLiu", "Calendar"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (
        DASHAN,
        XiaoShiLiuUserAsset(user_id=AUTHOR_ID, nickname="Mount Rainier Guide Desk", email="rainier-row219@example.com", avatar=XIAOSHILIU_DEFAULT_AVATAR),
        *POSTS,
    )
    goal = (
        "Create a new Contacts entry named Mount Rainier Trail Office with phone number 5550101006 and website https://www.nps.gov/mora/. "
        "Then open Messages and send Parker Hill this exact message: \"Depart for hiking Mount Rainier at 6 a.m. on Thursday\". "
        "Open XiaoShiLiu, search for \"Mount Rainier hiking guide\", and save the first five notes. Finally create a Calendar event titled \"Hike Mount Rainier\" "
        "on October 8, 2026 from 5:00 AM to 6:00 AM with description \"Hike Mount Rainier\"."
    )

    def criteria(self):
        return [
            AssetExists(NEW_CONTACT, task=self),
            AssetExists(EXPECTED_SMS, task=self),
            *(AssetExists(collection, task=self) for collection in COLLECTIONS),
            AssetExists(EVENT, task=self),
        ]
