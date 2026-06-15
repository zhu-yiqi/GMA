from __future__ import annotations

from gma.apps.xiaoshiliu import XIAOSHILIU_DEFAULT_AVATAR, XIAOSHILIU_LOGIN_USER_ID
from gma.assets import XiaoShiLiuCollectionAsset, XiaoShiLiuLikeAsset, XiaoShiLiuPostAsset, XiaoShiLiuUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


AUTHOR_ID = "w4-study-notes-author"
AUTHOR = XiaoShiLiuUserAsset(user_id=AUTHOR_ID, nickname="Study Notes Pro", email="study-notes-pro@example.com", avatar=XIAOSHILIU_DEFAULT_AVATAR, bio="Shares practical digital study materials.", location="Seed Campus")
TARGET_POST = XiaoShiLiuPostAsset(author_user_id=AUTHOR_ID, title="My iPad Digital Note Templates", content="A clean set of weekly review layouts for tablet note taking.", category="Study", tags=["study", "templates"], image_urls=["/assets/xiaoshiliu-save-ipad-note-templates-ipad-templates.png"], min_image_count=1, created_at_ms=1790818200000)
DISTRACTOR_POST = XiaoShiLiuPostAsset(author_user_id=AUTHOR_ID, title="Five-Minute Reading Checklist", content="A small routine for reviewing textbook chapters.", category="Study", tags=["study", "reading"], image_urls=["/assets/xiaoshiliu-save-ipad-note-templates-reading-desk.png"], min_image_count=1, created_at_ms=1790731800000)
EXPECTED_COLLECTION = XiaoShiLiuCollectionAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=TARGET_POST.title, post_author_user_id=AUTHOR_ID)
EXPECTED_LIKE = XiaoShiLiuLikeAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=TARGET_POST.title, post_author_user_id=AUTHOR_ID)

class XiaoShiLiuSaveIpadNoteTemplatesTask(BaseTask):
    apps = {"XiaoShiLiu"}
    difficulty = "easy"
    snapshot = "gma_ready_state"
    assets = (AUTHOR, DISTRACTOR_POST, TARGET_POST)
    goal = 'Open XiaoShiLiu, find "My iPad Digital Note Templates" in Study, then save it and like it.'

    def criteria(self):
        return [AssetExists(EXPECTED_COLLECTION, task=self), AssetExists(EXPECTED_LIKE, task=self)]
