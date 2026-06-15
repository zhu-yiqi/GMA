from __future__ import annotations

from gma.apps.xiaoshiliu import XIAOSHILIU_DEFAULT_AVATAR, XIAOSHILIU_LOGIN_USER_ID
from gma.assets import (
    DeviceFileAsset,
    ElementXFileAsset,
    ElementXMessageAsset,
    ElementXRoomAsset,
    ElementXUserAsset,
    XiaoShiLiuCollectionAsset,
    XiaoShiLiuFollowAsset,
    XiaoShiLiuLikeAsset,
    XiaoShiLiuPostAsset,
    XiaoShiLiuUserAsset,
)
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


ROOM_NAME = "study"
ROOM_TOPIC = "Learning"
ROOM_MESSAGE = "Sharing with everyone"
FINAL_MESSAGE = "I'd like to recommend a learning blogger: Campus Study Mentor"
FILE_NAME = "learning_materials.txt"
FILE_TEXT = "Focused study checklist\n1. Review notes\n2. Practice problems\n3. Summarize questions\n"
AUTHOR_ID = "w5-row236-study-mentor"
AUTHOR_NAME = "Campus Study Mentor"
POST_TITLE = "Focused Study Desk Setup"
POST_CONTENT = "My favorite way to prepare for exams is to keep one clean desk and one clear checklist."
IMAGE_FILENAME = "study-desk-focus.jpeg"
IMAGE_URL = f"/assets/{IMAGE_FILENAME}"

class ElementXXslStudyBloggerShareTask(BaseTask):
    apps = {"ElementX", "XiaoShiLiu", "Files"}
    difficulty = "hard"
    category = ['Multi-Step Workflow Tasks']
    snapshot = "gma_ready_state"

    jack = ElementXUserAsset(username="jack", password="password", display_name="Jack")
    source_file = DeviceFileAsset(
        app="Files",
        storage_dir="Download",
        filename=FILE_NAME,
        mime_type="text/plain",
        text_content=FILE_TEXT,
    )
    author = XiaoShiLiuUserAsset(
        user_id=AUTHOR_ID,
        nickname=AUTHOR_NAME,
        email="w5-row236-study-mentor@example.com",
        avatar=XIAOSHILIU_DEFAULT_AVATAR,
        bio="Study planning notes for campus learners.",
        location="Seed Campus",
        verified=False,
        is_active=True,
    )
    study_post = XiaoShiLiuPostAsset(
        author_user_id=AUTHOR_ID,
        title=POST_TITLE,
        content=POST_CONTENT,
        category="Study",
        tags=["study", "planning"],
        image_urls=[IMAGE_URL],
        min_image_count=1,
    )
    assets = (jack, source_file, author, study_post)

    goal = (
        "Open ElementX, create a group room named \"study\" with topic \"Learning\", invite Jack, "
        f"send exactly \"{ROOM_MESSAGE}\", upload \"{FILE_NAME}\" from Downloads, and pin that file. "
        f"Then open XiaoShiLiu, find the Study post titled \"{POST_TITLE}\", like it, save it, "
        "and follow the author of that post. Return to the ElementX room \"study\" and send a message "
        "in the format \"I'd like to recommend a learning blogger: <author name>\"."
    )

    def criteria(self):
        return [
            AssetExists(
                ElementXRoomAsset(
                    name=ROOM_NAME,
                    room_type="group",
                    creator_username="testuser",
                    creator_password="testpass123",
                    members=["jack"],
                    topic=ROOM_TOPIC,
                ),
                task=self,
            ),
            AssetExists(
                ElementXMessageAsset(
                    room=ROOM_NAME,
                    sender_username="testuser",
                    sender_password="testpass123",
                    text=ROOM_MESSAGE,
                ),
                task=self,
            ),
            AssetExists(
                ElementXFileAsset(
                    room=ROOM_NAME,
                    sender_username="testuser",
                    sender_password="testpass123",
                    filename=FILE_NAME,
                    mime_type="text/plain",
                    text_content=FILE_TEXT,
                    pinned=True,
                ),
                task=self,
            ),
            AssetExists(
                XiaoShiLiuLikeAsset(
                    user_id=XIAOSHILIU_LOGIN_USER_ID,
                    post_title=POST_TITLE,
                    post_author_user_id=AUTHOR_ID,
                ),
                task=self,
            ),
            AssetExists(
                XiaoShiLiuCollectionAsset(
                    user_id=XIAOSHILIU_LOGIN_USER_ID,
                    post_title=POST_TITLE,
                    post_author_user_id=AUTHOR_ID,
                ),
                task=self,
            ),
            AssetExists(
                XiaoShiLiuFollowAsset(
                    follower_user_id=XIAOSHILIU_LOGIN_USER_ID,
                    following_user_id=AUTHOR_ID,
                ),
                task=self,
            ),
            AssetExists(
                ElementXMessageAsset(
                    room=ROOM_NAME,
                    sender_username="testuser",
                    sender_password="testpass123",
                    text=FINAL_MESSAGE,
                ),
                task=self,
            ),
        ]
