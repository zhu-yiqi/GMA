from __future__ import annotations

from gma.apps.xiaoshiliu import XIAOSHILIU_DEFAULT_AVATAR, XIAOSHILIU_LOGIN_USER_ID
from gma.assets import XiaoShiLiuCollectionAsset, XiaoShiLiuCommentAsset, XiaoShiLiuFollowAsset, XiaoShiLiuLikeAsset, XiaoShiLiuPostAsset, XiaoShiLiuUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


YUNNAN_AUTHOR_ID = "w4-row187-yunnan-planner"
HOMEPAGE_AUTHOR_ID = "w4-row187-campus-window"
COMMENTER_ID = "w4-row187-first-commenter"
LAPTOP_AUTHOR_ID = "w4-row187-tech-guide"
YUNNAN_TITLE = "Budget Trip to Colorado: 5 Days Under $350"
HOMEPAGE_TITLE = "Campus Coffee Window"
COMMENTER_COMMENT = "This spot is quiet enough for a short break."
LAPTOP_TITLE = "Laptop Buying Guide for College Students"

YUNNAN_AUTHOR = XiaoShiLiuUserAsset(user_id=YUNNAN_AUTHOR_ID, nickname="Colorado Planner", email="yunnan-planner-row187@example.com", avatar=XIAOSHILIU_DEFAULT_AVATAR)
HOMEPAGE_AUTHOR = XiaoShiLiuUserAsset(user_id=HOMEPAGE_AUTHOR_ID, nickname="Campus Window", email="campus-window-row187@example.com", avatar=XIAOSHILIU_DEFAULT_AVATAR)
COMMENTER = XiaoShiLiuUserAsset(user_id=COMMENTER_ID, nickname="Riley West", email="riley-west-row187@example.com", avatar=XIAOSHILIU_DEFAULT_AVATAR)
LAPTOP_AUTHOR = XiaoShiLiuUserAsset(user_id=LAPTOP_AUTHOR_ID, nickname="Student Tech Guide", email="student-tech-guide-row187@example.com", avatar=XIAOSHILIU_DEFAULT_AVATAR)
YUNNAN_POST = XiaoShiLiuPostAsset(author_user_id=YUNNAN_AUTHOR_ID, title=YUNNAN_TITLE, content="A five-day budget route through markets, tea fields, and mountain views with a simple hostel plan.", category="Travel", tags=["travel", "budget"], image_urls=["/assets/xiaoshiliu-colorado-homepage-laptop-actions-colorado-budget-trip.png"], min_image_count=1, created_at_ms=1790845200000)
HOMEPAGE_POST = XiaoShiLiuPostAsset(author_user_id=HOMEPAGE_AUTHOR_ID, title=HOMEPAGE_TITLE, content="A short campus feed update about a quiet coffee window near the library.", category="Campus Life", tags=["campus"], image_urls=["/assets/xiaoshiliu-colorado-homepage-laptop-actions-homepage-campus-photo.png"], min_image_count=1, created_at_ms=202610011230)
SEEDED_COMMENT = XiaoShiLiuCommentAsset(post_title=HOMEPAGE_TITLE, post_author_user_id=HOMEPAGE_AUTHOR_ID, author_user_id=COMMENTER_ID, content=COMMENTER_COMMENT, created_at_ms=202610011231)
LAPTOP_POST = XiaoShiLiuPostAsset(author_user_id=LAPTOP_AUTHOR_ID, title=LAPTOP_TITLE, content="A practical guide for choosing a reliable college laptop by weight, battery life, and ports.", category="Technology", tags=["tech", "laptop"], image_urls=["/assets/xiaoshiliu-colorado-homepage-laptop-actions-laptop-college-guide.png"], min_image_count=1, created_at_ms=1790845500000)

EXPECTED_YUNNAN_LIKE = XiaoShiLiuLikeAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=YUNNAN_TITLE, post_author_user_id=YUNNAN_AUTHOR_ID)
EXPECTED_YUNNAN_COMMENT = XiaoShiLiuCommentAsset(post_title=YUNNAN_TITLE, post_author_user_id=YUNNAN_AUTHOR_ID, author_user_id=XIAOSHILIU_LOGIN_USER_ID, content="beautiful")
EXPECTED_COMMENTER_FOLLOW = XiaoShiLiuFollowAsset(follower_user_id=XIAOSHILIU_LOGIN_USER_ID, following_user_id=COMMENTER_ID)
EXPECTED_REPLY = XiaoShiLiuCommentAsset(post_title=HOMEPAGE_TITLE, post_author_user_id=HOMEPAGE_AUTHOR_ID, author_user_id=XIAOSHILIU_LOGIN_USER_ID, content="So?", parent_content=COMMENTER_COMMENT, parent_author_user_id=COMMENTER_ID)
EXPECTED_LAPTOP_COLLECTION = XiaoShiLiuCollectionAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=LAPTOP_TITLE, post_author_user_id=LAPTOP_AUTHOR_ID)

class XiaoShiLiuColoradoHomepageLaptopActionsTask(BaseTask):
    apps = {"XiaoShiLiu"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (YUNNAN_AUTHOR, HOMEPAGE_AUTHOR, COMMENTER, LAPTOP_AUTHOR, YUNNAN_POST, HOMEPAGE_POST, SEEDED_COMMENT, LAPTOP_POST)
    goal = (
        "Open XiaoShiLiu, search for \"Budget Trip to Colorado: 5 Days Under $350\", like it, and comment \"beautiful\". "
        "Then open the newest home-feed post, \"Campus Coffee Window\", follow the first commenter Riley West, and reply \"So?\" to that comment. "
        "Finally, find \"Laptop Buying Guide for College Students\" in Technology and save it."
    )

    def criteria(self):
        return [
            AssetExists(EXPECTED_YUNNAN_LIKE, task=self),
            AssetExists(EXPECTED_YUNNAN_COMMENT, task=self),
            AssetExists(EXPECTED_COMMENTER_FOLLOW, task=self),
            AssetExists(EXPECTED_REPLY, task=self),
            AssetExists(EXPECTED_LAPTOP_COLLECTION, task=self),
        ]
