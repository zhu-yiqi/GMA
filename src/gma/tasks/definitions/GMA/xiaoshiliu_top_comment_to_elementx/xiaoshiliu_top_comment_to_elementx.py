from __future__ import annotations

from gma.apps.xiaoshiliu import XIAOSHILIU_DEFAULT_AVATAR, XIAOSHILIU_LOGIN_USER_ID
from gma.assets import ElementXMessageAsset, ElementXRoomAsset, ElementXUserAsset, XiaoShiLiuCollectionAsset, XiaoShiLiuCommentAsset, XiaoShiLiuFollowAsset, XiaoShiLiuLikeAsset, XiaoShiLiuPostAsset, XiaoShiLiuUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


MUSIC_AUTHOR_ID = "w4-row200-guitar-author"
FOOD_AUTHOR_ID = "w4-row200-coffee-author"
COMMENTER_ID = "w4-row200-menu-commenter"
ROOM_ALIAS = "w4-row200-first-room"
ROOM_NAME = "First Shared Room"
GUITAR_TITLE = "Learning Guitar from Scratch: Two Months In"
FOOD_TITLE = "Secret Menu at the Campus Coffee Shop"
TOP_COMMENT = "The cinnamon cold brew is the best hidden order."

MUSIC_AUTHOR = XiaoShiLiuUserAsset(user_id=MUSIC_AUTHOR_ID, nickname="Guitar Journal", email="guitar-journal-row200@example.com", avatar=XIAOSHILIU_DEFAULT_AVATAR)
FOOD_AUTHOR = XiaoShiLiuUserAsset(user_id=FOOD_AUTHOR_ID, nickname="Coffee Insider", email="coffee-insider-row200@example.com", avatar=XIAOSHILIU_DEFAULT_AVATAR)
COMMENTER = XiaoShiLiuUserAsset(user_id=COMMENTER_ID, nickname="Menu Scout", email="menu-scout-row200@example.com", avatar=XIAOSHILIU_DEFAULT_AVATAR)
GUITAR_POST = XiaoShiLiuPostAsset(author_user_id=MUSIC_AUTHOR_ID, title=GUITAR_TITLE, content="Two months of chord practice, sore fingertips, and small wins on acoustic guitar.", category="Music", tags=["music", "guitar"], image_urls=["/assets/xiaoshiliu-top-comment-to-elementx-guitar-practice.png"], min_image_count=1, created_at_ms=1790845200000)
FOOD_POST = XiaoShiLiuPostAsset(author_user_id=FOOD_AUTHOR_ID, title=FOOD_TITLE, content="A few campus coffee shop combinations that are not printed on the menu but are easy to order.", category="Food", tags=["food", "coffee"], image_urls=["/assets/xiaoshiliu-top-comment-to-elementx-secret-menu.png"], min_image_count=1, created_at_ms=1790845500000)
SEEDED_COMMENT = XiaoShiLiuCommentAsset(post_title=FOOD_TITLE, post_author_user_id=FOOD_AUTHOR_ID, author_user_id=COMMENTER_ID, content=TOP_COMMENT, created_at_ms=1790845800000)

EXPECTED_GUITAR_LIKE = XiaoShiLiuLikeAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=GUITAR_TITLE, post_author_user_id=MUSIC_AUTHOR_ID)
EXPECTED_GUITAR_COLLECTION = XiaoShiLiuCollectionAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=GUITAR_TITLE, post_author_user_id=MUSIC_AUTHOR_ID)
EXPECTED_GUITAR_COMMENT = XiaoShiLiuCommentAsset(post_title=GUITAR_TITLE, post_author_user_id=MUSIC_AUTHOR_ID, author_user_id=XIAOSHILIU_LOGIN_USER_ID, content="Good")
EXPECTED_FOLLOW = XiaoShiLiuFollowAsset(follower_user_id=XIAOSHILIU_LOGIN_USER_ID, following_user_id=FOOD_AUTHOR_ID)
EXPECTED_MESSAGE = ElementXMessageAsset(room=ROOM_ALIAS, sender_username="testuser", sender_password="testpass123", text=TOP_COMMENT)

class XiaoShiLiuTopCommentToElementXTask(BaseTask):
    apps = {"XiaoShiLiu", "ElementX"}
    difficulty = "hard"
    snapshot = "gma_ready_state"
    assets = (
        MUSIC_AUTHOR,
        FOOD_AUTHOR,
        COMMENTER,
        GUITAR_POST,
        FOOD_POST,
        SEEDED_COMMENT,
        ElementXUserAsset(username="w4-row200-roommate", password="password", display_name="Roommate"),
        ElementXRoomAsset(name=ROOM_NAME, room_type="group", creator_username="testuser", creator_password="testpass123", members=["w4-row200-roommate"], alias_localpart=ROOM_ALIAS),
    )
    goal = (
        "Open XiaoShiLiu, find \"Learning Guitar from Scratch: Two Months In\" in Music, like and save it, then comment \"Good\". "
        "Next find \"Secret Menu at the Campus Coffee Shop\" in Food, follow its author, read the top-level comment, "
        "then open ElementX and send that exact comment to First Shared Room."
    )

    def criteria(self):
        return [
            AssetExists(EXPECTED_GUITAR_LIKE, task=self),
            AssetExists(EXPECTED_GUITAR_COLLECTION, task=self),
            AssetExists(EXPECTED_GUITAR_COMMENT, task=self),
            AssetExists(EXPECTED_FOLLOW, task=self),
            AssetExists(EXPECTED_MESSAGE, task=self),
        ]
