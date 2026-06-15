from __future__ import annotations

from gma.apps.xiaoshiliu import XIAOSHILIU_DEFAULT_AVATAR, XIAOSHILIU_LOGIN_USER_ID
from gma.assets import AlarmAsset, XiaoShiLiuCollectionAsset, XiaoShiLiuLikeAsset, XiaoShiLiuPostAsset, XiaoShiLiuUserAsset
from gma.evaluation import AssetExists, AssetModified
from gma.tasks.base import BaseTask


ALARM_A_BEFORE = AlarmAsset(hour=7, minute=0, label="A", enabled=True, days_of_week=("monday",), vibrate=True)
ALARM_A_AFTER = AlarmAsset(hour=7, minute=0, label="Morning Study", enabled=True, days_of_week=(), vibrate=False)
ALARM_B_BEFORE = AlarmAsset(hour=13, minute=0, label="B", enabled=True, days_of_week=("tuesday",), vibrate=True)
ALARM_B_AFTER = AlarmAsset(hour=13, minute=0, label="Afternoon Study", enabled=True, days_of_week=("tuesday",), vibrate=True)
AUTHOR_ID = "w4-row223-study-author"
ALGO_POSTS = tuple(
    XiaoShiLiuPostAsset(author_user_id=AUTHOR_ID, title=f"Introduction to Algorithms Note {i}", content="Study notes for Introduction to Algorithms.", category="Study", tags=["Introduction to Algorithms"], image_urls=["/assets/clock-study-alarms-xsl-actions-algorithms.png"], min_image_count=1, created_at_ms=1790845500000 - i * 60000)
    for i in range(1, 4)
)
LIT_POSTS = tuple(
    XiaoShiLiuPostAsset(author_user_id=AUTHOR_ID, title=f"Literature Reading Note {i}", content="A short literature reading reflection.", category="Study", tags=["literature"], image_urls=["/assets/clock-study-alarms-xsl-actions-literature.png"], min_image_count=1, created_at_ms=1790845200000 - i * 60000)
    for i in range(1, 4)
)
COLLECTIONS = tuple(XiaoShiLiuCollectionAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=post.title, post_author_user_id=AUTHOR_ID) for post in ALGO_POSTS)
LIKES = tuple(XiaoShiLiuLikeAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=post.title, post_author_user_id=AUTHOR_ID) for post in LIT_POSTS)

class ClockStudyAlarmsXslActionsTask(BaseTask):
    apps = {"Clock", "XiaoShiLiu"}
    difficulty = "hard"
    snapshot = "gma_ready_state"
    assets = (ALARM_A_BEFORE, ALARM_B_BEFORE, XiaoShiLiuUserAsset(user_id=AUTHOR_ID, nickname="Study Prompt Desk", email="study-row223@example.com", avatar=XIAOSHILIU_DEFAULT_AVATAR), *ALGO_POSTS, *LIT_POSTS)
    goal = (
        "Open Clock. Change alarm A to label Morning Study, remove its repeat cycle, and turn vibration off. "
        "Change alarm B to label Afternoon Study. Then open XiaoShiLiu, search for \"Introduction to Algorithms\" and save all matching notes. "
        "Also search for \"Literature Reading Note\" and like all matching Study posts."
    )

    def criteria(self):
        return [
            AssetModified(ALARM_A_BEFORE, ALARM_A_AFTER, task=self),
            AssetModified(ALARM_B_BEFORE, ALARM_B_AFTER, task=self),
            *(AssetExists(collection, task=self) for collection in COLLECTIONS),
            *(AssetExists(like, task=self) for like in LIKES),
        ]
