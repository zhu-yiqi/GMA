from __future__ import annotations

from gma.apps.xiaoshiliu import XIAOSHILIU_LOGIN_USER_ID
from gma.assets import (
    AlarmAsset,
    XiaoShiLiuCollectionAsset,
    XiaoShiLiuPostAsset,
    XiaoShiLiuUserAsset,
)
from gma.evaluation import AssetExists, AssetModified
from gma.tasks.base import BaseTask


ALARM_BEFORE = AlarmAsset(
    hour=10,
    minute=0,
    label="Morning Meeting",
    enabled=True,
    days_of_week=("monday", "tuesday", "wednesday", "thursday"),
    vibrate=False,
)
ALARM_AFTER = AlarmAsset(
    hour=19,
    minute=0,
    label="Concert",
    enabled=True,
    days_of_week=("saturday",),
    vibrate=True,
)
AUTHOR_ID = "concert-ticket-guide-author"
AUTHOR = XiaoShiLiuUserAsset(
    user_id=AUTHOR_ID,
    password="123456",
    nickname="Concert Guide Author",
    email="concert-guide-author@example.com",
    avatar="/assets/avatar-ClIy5dZi.png",
    bio="Shares practical concert planning notes.",
    location="Campus Arts Center",
)
IMAGE_FILENAMES = (
    "001-concert-ticket-guide-01.png",
    "002-concert-ticket-guide-02.png",
    "003-concert-ticket-guide-03.png",
    "004-concert-ticket-guide-04.png",
    "005-concert-ticket-guide-05.png",
    "006-concert-ticket-guide-06.png",
    "007-concert-ticket-guide-07.png",
    "008-concert-ticket-guide-08.png",
    "009-concert-ticket-guide-09.png",
    "010-concert-ticket-guide-10.png",
)
POST_TITLES = (
    "How to Grab Concert Tickets: Queue Prep",
    "How to Grab Concert Tickets: Seat Map Notes",
    "How to Grab Concert Tickets: Account Checklist",
    "How to Grab Concert Tickets: Payment Setup",
    "How to Grab Concert Tickets: Device Backup",
    "How to Grab Concert Tickets: Timing Practice",
    "How to Grab Concert Tickets: Group Plan",
    "How to Grab Concert Tickets: Refresh Strategy",
    "How to Grab Concert Tickets: Cafe Countdown",
    "How to Grab Concert Tickets: Final Reminder",
)
POSTS = tuple(
    XiaoShiLiuPostAsset(
        author_user_id=AUTHOR_ID,
        title=title,
        content="Practical notes for preparing before a concert ticket release.",
        category="Music",
        tags=["concert", "tickets", "planning"],
        image_urls=[f"/assets/{filename}"],
        min_image_count=1,
        created_at_ms=1790845200000 - index * 60000,
    )
    for index, (title, filename) in enumerate(zip(POST_TITLES, IMAGE_FILENAMES))
)
COLLECTIONS = tuple(
    XiaoShiLiuCollectionAsset(
        user_id=XIAOSHILIU_LOGIN_USER_ID,
        post_title=post.title,
        post_author_user_id=AUTHOR_ID,
    )
    for post in POSTS
)

class ClockConcertAlarmCollectTicketPostsTask(BaseTask):
    apps = {"Clock", "XiaoShiLiu"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (ALARM_BEFORE, AUTHOR, *POSTS)
    goal = (
        "Find the Clock alarm labeled Morning Meeting. Change its label to Concert, set it "
        "for 7:00 PM, make it repeat every Saturday, and turn vibration on. Then open "
        "XiaoShiLiu, search for \"How to Grab Concert Tickets\", and bookmark every note "
        "shown in the search results."
    )

    def criteria(self):
        return [
            AssetModified(ALARM_BEFORE, ALARM_AFTER, task=self),
            *(AssetExists(collection, task=self) for collection in COLLECTIONS),
        ]
