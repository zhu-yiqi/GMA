from __future__ import annotations

from gma.apps.xiaoshiliu import XIAOSHILIU_DEFAULT_AVATAR, XIAOSHILIU_LOGIN_USER_ID
from gma.assets import XiaoShiLiuCollectionAsset, XiaoShiLiuCommentAsset, XiaoShiLiuFollowAsset, XiaoShiLiuPostAsset, XiaoShiLiuUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


FOOD_AUTHOR_ID = "w4-row188-campus-bites"
TECH_AUTHOR_ID = "w4-row188-desk-tech"
TRAVEL_AUTHOR_ID = "w4-row188-weekend-walker"
FOOD_MAIN_TITLE = "Campus Lunch Bowl Worth Repeating"
FOOD_SECOND_TITLE = "Small Cafe Dessert Break"
FOOD_THIRD_TITLE = "Noodle Counter After Class"
TECH_TITLE = "Compact Desk Tech Setup"
TRAVEL_TITLE = "Morning Walks in a New City"

FOOD_AUTHOR = XiaoShiLiuUserAsset(user_id=FOOD_AUTHOR_ID, nickname="Campus Bites", email="campus-bites-row188@example.com", avatar=XIAOSHILIU_DEFAULT_AVATAR)
TECH_AUTHOR = XiaoShiLiuUserAsset(user_id=TECH_AUTHOR_ID, nickname="Desk Tech", email="desk-tech-row188@example.com", avatar=XIAOSHILIU_DEFAULT_AVATAR)
TRAVEL_AUTHOR = XiaoShiLiuUserAsset(user_id=TRAVEL_AUTHOR_ID, nickname="Weekend Walker", email="weekend-walker-row188@example.com", avatar=XIAOSHILIU_DEFAULT_AVATAR)
FOOD_MAIN = XiaoShiLiuPostAsset(author_user_id=FOOD_AUTHOR_ID, title=FOOD_MAIN_TITLE, content="A balanced campus lunch bowl that is quick enough between two classes.", category="Food", tags=["food"], image_urls=["/assets/xiaoshiliu-food-author-tech-travel-actions-food-campus-bowl.png"], min_image_count=1, created_at_ms=1790845800000)
FOOD_SECOND = XiaoShiLiuPostAsset(author_user_id=FOOD_AUTHOR_ID, title=FOOD_SECOND_TITLE, content="A simple dessert and drink stop for a quiet afternoon reset.", category="Food", tags=["food"], image_urls=["/assets/xiaoshiliu-food-author-tech-travel-actions-food-author-dessert.png"], min_image_count=1, created_at_ms=1790845500000)
FOOD_THIRD = XiaoShiLiuPostAsset(author_user_id=FOOD_AUTHOR_ID, title=FOOD_THIRD_TITLE, content="A warm noodle bowl that works well after a late seminar.", category="Food", tags=["food"], image_urls=["/assets/xiaoshiliu-food-author-tech-travel-actions-food-author-noodles.png"], min_image_count=1, created_at_ms=1790845200000)
TECH_POST = XiaoShiLiuPostAsset(author_user_id=TECH_AUTHOR_ID, title=TECH_TITLE, content="A small laptop and tablet setup for focused dorm-room study sessions.", category="Technology", tags=["tech"], image_urls=["/assets/xiaoshiliu-food-author-tech-travel-actions-tech-desk-note.png"], min_image_count=1, created_at_ms=1790846100000)
TRAVEL_POST = XiaoShiLiuPostAsset(author_user_id=TRAVEL_AUTHOR_ID, title=TRAVEL_TITLE, content="A quiet first morning route through side streets, coffee shops, and a small plaza.", category="Travel", tags=["travel"], image_urls=["/assets/xiaoshiliu-food-author-tech-travel-actions-travel-morning-street.png"], min_image_count=1, created_at_ms=1790846400000)

EXPECTED_COLLECTIONS = (
    XiaoShiLiuCollectionAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=FOOD_MAIN_TITLE, post_author_user_id=FOOD_AUTHOR_ID),
    XiaoShiLiuCollectionAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=FOOD_SECOND_TITLE, post_author_user_id=FOOD_AUTHOR_ID),
    XiaoShiLiuCollectionAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=FOOD_THIRD_TITLE, post_author_user_id=FOOD_AUTHOR_ID),
)
EXPECTED_TECH_FOLLOW = XiaoShiLiuFollowAsset(follower_user_id=XIAOSHILIU_LOGIN_USER_ID, following_user_id=TECH_AUTHOR_ID)
EXPECTED_TRAVEL_COMMENT = XiaoShiLiuCommentAsset(post_title=TRAVEL_TITLE, post_author_user_id=TRAVEL_AUTHOR_ID, author_user_id=XIAOSHILIU_LOGIN_USER_ID, content="I really want to go.")

class XiaoShiLiuFoodAuthorTechTravelActionsTask(BaseTask):
    apps = {"XiaoShiLiu"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (FOOD_AUTHOR, TECH_AUTHOR, TRAVEL_AUTHOR, FOOD_MAIN, FOOD_SECOND, FOOD_THIRD, TECH_POST, TRAVEL_POST)
    goal = (
        "Open XiaoShiLiu. In Food, open the first note, \"Campus Lunch Bowl Worth Repeating\", go to the author's profile, "
        "and save all three posts by Campus Bites. Then follow the author of the first Technology note, \"Compact Desk Tech Setup\". "
        "Finally, go to Travel and comment \"I really want to go.\" on the first Travel note, \"Morning Walks in a New City\"."
    )

    def criteria(self):
        return [
            *(AssetExists(asset, task=self) for asset in EXPECTED_COLLECTIONS),
            AssetExists(EXPECTED_TECH_FOLLOW, task=self),
            AssetExists(EXPECTED_TRAVEL_COMMENT, task=self),
        ]
