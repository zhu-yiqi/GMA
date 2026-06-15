from __future__ import annotations

from gma.apps.xiaoshiliu import XIAOSHILIU_DEFAULT_AVATAR, XIAOSHILIU_LOGIN_USER_ID
from gma.assets import (
    XiaoShiLiuCollectionAsset,
    XiaoShiLiuCommentAsset,
    XiaoShiLiuFollowAsset,
    XiaoShiLiuLikeAsset,
    XiaoShiLiuPostAsset,
    XiaoShiLiuUserAsset,
)
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


MUSIC_AUTHOR_ID = "w4-row186-library-playlists"
TRAVEL_AUTHOR_ID = "w4-row186-budget-backpacker"
STYLE_COMMENTER_ID = "w4-row186-daily-style-guide"
STUDY_TITLE = "Study Playlist: Best Songs for the Library"
XIAMEN_TITLE = "Budget Trip to Portland: 3 Days Under $150"
STYLE_COMMENT = "Pack a light jacket for the evening waterfront walk."

MUSIC_AUTHOR = XiaoShiLiuUserAsset(user_id=MUSIC_AUTHOR_ID, nickname="Library Playlists", email="library-playlists-row186@example.com", avatar=XIAOSHILIU_DEFAULT_AVATAR)
TRAVEL_AUTHOR = XiaoShiLiuUserAsset(user_id=TRAVEL_AUTHOR_ID, nickname="Budget Backpacker", email="budget-backpacker-row186@example.com", avatar=XIAOSHILIU_DEFAULT_AVATAR)
STYLE_COMMENTER = XiaoShiLiuUserAsset(user_id=STYLE_COMMENTER_ID, nickname="Daily Style Guide", email="daily-style-guide-row186@example.com", avatar=XIAOSHILIU_DEFAULT_AVATAR)
STUDY_POST = XiaoShiLiuPostAsset(author_user_id=MUSIC_AUTHOR_ID, title=STUDY_TITLE, content="A quiet playlist for long reading blocks, library review sessions, and slow evening notes.", category="Music", tags=["music", "study"], image_urls=["/assets/xiaoshiliu-music-travel-comment-follow-save-study-playlist-library.png"], min_image_count=1, created_at_ms=1790845200000)
XIAMEN_POST = XiaoShiLiuPostAsset(author_user_id=TRAVEL_AUTHOR_ID, title=XIAMEN_TITLE, content="A compact three-day Portland route with hostel stays, ferry rides, and simple street food stops under a tight budget.", category="Travel", tags=["travel", "budget"], image_urls=["/assets/xiaoshiliu-music-travel-comment-follow-save-portland-budget-trip.png"], min_image_count=1, created_at_ms=1790845500000)
SEEDED_STYLE_COMMENT = XiaoShiLiuCommentAsset(post_title=XIAMEN_TITLE, post_author_user_id=TRAVEL_AUTHOR_ID, author_user_id=STYLE_COMMENTER_ID, content=STYLE_COMMENT, created_at_ms=1790845800000)

EXPECTED_STUDY_COMMENT = XiaoShiLiuCommentAsset(post_title=STUDY_TITLE, post_author_user_id=MUSIC_AUTHOR_ID, author_user_id=XIAOSHILIU_LOGIN_USER_ID, content="I like this playlist!")
EXPECTED_XIAMEN_COMMENT = XiaoShiLiuCommentAsset(post_title=XIAMEN_TITLE, post_author_user_id=TRAVEL_AUTHOR_ID, author_user_id=XIAOSHILIU_LOGIN_USER_ID, content="Really great!")
EXPECTED_REPLY = XiaoShiLiuCommentAsset(post_title=XIAMEN_TITLE, post_author_user_id=TRAVEL_AUTHOR_ID, author_user_id=XIAOSHILIU_LOGIN_USER_ID, content="Good", parent_content=STYLE_COMMENT, parent_author_user_id=STYLE_COMMENTER_ID)
EXPECTED_COMMENT_LIKE = XiaoShiLiuLikeAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, target_type="comment", post_title=XIAMEN_TITLE, post_author_user_id=TRAVEL_AUTHOR_ID, comment_content=STYLE_COMMENT, comment_author_user_id=STYLE_COMMENTER_ID)
EXPECTED_FOLLOW = XiaoShiLiuFollowAsset(follower_user_id=XIAOSHILIU_LOGIN_USER_ID, following_user_id=TRAVEL_AUTHOR_ID)
EXPECTED_COLLECTION = XiaoShiLiuCollectionAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=XIAMEN_TITLE, post_author_user_id=TRAVEL_AUTHOR_ID)

class XiaoShiLiuMusicTravelCommentFollowSaveTask(BaseTask):
    apps = {"XiaoShiLiu"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (MUSIC_AUTHOR, TRAVEL_AUTHOR, STYLE_COMMENTER, STUDY_POST, XIAMEN_POST, SEEDED_STYLE_COMMENT)
    goal = (
        "Open XiaoShiLiu. In the Music section, find \"Study Playlist: Best Songs for the Library\" and comment \"I like this playlist!\". "
        "Then go to the Travel section, find \"Budget Trip to Portland: 3 Days Under $150\", comment \"Really great!\", "
        "reply \"Good\" to Daily Style Guide's comment \"Pack a light jacket for the evening waterfront walk.\", "
        "like that comment, follow the post author, and save the post."
    )

    def criteria(self):
        return [
            AssetExists(EXPECTED_STUDY_COMMENT, task=self),
            AssetExists(EXPECTED_XIAMEN_COMMENT, task=self),
            AssetExists(EXPECTED_REPLY, task=self),
            AssetExists(EXPECTED_COMMENT_LIKE, task=self),
            AssetExists(EXPECTED_FOLLOW, task=self),
            AssetExists(EXPECTED_COLLECTION, task=self),
        ]
