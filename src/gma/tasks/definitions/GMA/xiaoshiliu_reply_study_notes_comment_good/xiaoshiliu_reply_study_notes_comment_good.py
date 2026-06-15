from __future__ import annotations

from gma.apps.xiaoshiliu import XIAOSHILIU_DEFAULT_AVATAR, XIAOSHILIU_LOGIN_USER_ID
from gma.assets import XiaoShiLiuCommentAsset, XiaoShiLiuPostAsset, XiaoShiLiuUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


COMMENTER_ID = "w1-study-notes-pro"
TARGET_TITLE = "Desk Setup Notes"
TARGET_IMAGE = "xiaoshiliu-reply-study-notes-comment-good-study-desk.png"

class XiaoShiLiuReplyStudyNotesCommentGoodTask(BaseTask):
    apps = {"XiaoShiLiu"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    commenter = XiaoShiLiuUserAsset(
        user_id=COMMENTER_ID,
        nickname="Study Notes Pro",
        email="study-notes-pro-w1@example.com",
        avatar=XIAOSHILIU_DEFAULT_AVATAR,
        bio="Practical templates and study routines.",
        location="Seed Campus",
    )
    seeded_post = XiaoShiLiuPostAsset(
        author_user_id=XIAOSHILIU_LOGIN_USER_ID,
        title=TARGET_TITLE,
        content="A quick look at today's study desk arrangement.",
        category="Study",
        tags=["study", "desk"],
        image_urls=[f"/assets/{TARGET_IMAGE}"],
        min_image_count=1,
        created_at_ms=1790811000000,
    )
    parent_comment = XiaoShiLiuCommentAsset(
        post_title=TARGET_TITLE,
        post_author_user_id=XIAOSHILIU_LOGIN_USER_ID,
        author_user_id=COMMENTER_ID,
        content="This layout looks organized.",
        created_at_ms=1790811600000,
    )
    expected_reply = XiaoShiLiuCommentAsset(
        post_title=TARGET_TITLE,
        post_author_user_id=XIAOSHILIU_LOGIN_USER_ID,
        author_user_id=XIAOSHILIU_LOGIN_USER_ID,
        content="Good",
        parent_content="This layout looks organized.",
        parent_author_user_id=COMMENTER_ID,
    )
    assets = (commenter, seeded_post, parent_comment)

    goal = (
        "Open XiaoShiLiu, go to my profile page, open the first post under Post, "
        "find the comment by Study Notes Pro, and reply exactly \"Good\"."
    )

    def criteria(self):
        return [AssetExists(self.expected_reply, task=self)]
