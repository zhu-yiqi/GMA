from __future__ import annotations

from gma.apps.xiaoshiliu import XIAOSHILIU_DEFAULT_AVATAR, XIAOSHILIU_LOGIN_USER_ID
from gma.assets import XiaoShiLiuCommentAsset, XiaoShiLiuPostAsset, XiaoShiLiuUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


AUTHOR_ID = "w1-template-author"
TARGET_TITLE = "My iPad Digital Note Templates"
TARGET_IMAGE = "xiaoshiliu-comment-ipad-templates-all-grown-up-ipad-templates.png"

class XiaoShiLiuCommentIpadTemplatesAllGrownUpTask(BaseTask):
    apps = {"XiaoShiLiu"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    author = XiaoShiLiuUserAsset(
        user_id=AUTHOR_ID,
        nickname="Template Studio",
        email="template-studio-w1@example.com",
        avatar=XIAOSHILIU_DEFAULT_AVATAR,
        bio="Digital planning templates for study routines.",
        location="Seed Campus",
    )
    target_post = XiaoShiLiuPostAsset(
        author_user_id=AUTHOR_ID,
        title=TARGET_TITLE,
        content="A clean set of digital note layouts for weekly classes.",
        category="Study",
        tags=["study", "templates"],
        image_urls=[f"/assets/{TARGET_IMAGE}"],
        min_image_count=1,
        created_at_ms=1790812800000,
    )
    expected_comment = XiaoShiLiuCommentAsset(
        post_title=TARGET_TITLE,
        post_author_user_id=AUTHOR_ID,
        author_user_id=XIAOSHILIU_LOGIN_USER_ID,
        content="You are all grown up.",
    )
    assets = (author, target_post)

    goal = (
        "Open XiaoShiLiu, search for \"My iPad Digital Note Templates\", "
        "and comment exactly \"You are all grown up.\""
    )

    def criteria(self):
        return [AssetExists(self.expected_comment, task=self)]
