from __future__ import annotations

from gma.apps.xiaoshiliu import XIAOSHILIU_DEFAULT_AVATAR, XIAOSHILIU_LOGIN_USER_ID
from gma.assets import (
    DeviceFileAsset,
    ImageContentExpectation,
    XiaoShiLiuCollectionAsset,
    XiaoShiLiuCommentAsset,
    XiaoShiLiuFollowAsset,
    XiaoShiLiuLikeAsset,
    XiaoShiLiuPostAsset,
    XiaoShiLiuUserAsset,
)
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


STUDY_AUTHOR_ID = "exam-coach-author"
FITNESS_AUTHOR_ID = "morning-runner-author"
PHOTO_AUTHOR_ID = "rain-photographer-author"
STUDY_TITLE = "How I Scored 85 on the Graduate English Exam"
FITNESS_TITLE = "One Month of Morning Runs: My Transformation"
PHOTO_TITLE = "Stunning Reflections After the Rain"
NEW_POST_TITLE = "Campus Weekend Plan"
NEW_POST_CONTENT = "Study first, run in the morning, and take photos after the rain."
UPLOAD_IMAGE_FILES = (
    "travel-guide-photo-1.png",
    "travel-guide-photo-2.png",
    "travel-guide-photo-3.png",
)

UPLOAD_IMAGES = tuple(
    DeviceFileAsset(
        app="Gallery",
        storage_dir="Pictures",
        filename=filename,
        mime_type="image/png",
        source_path=f"assets/{filename}",
    )
    for filename in UPLOAD_IMAGE_FILES
)
STUDY_AUTHOR = XiaoShiLiuUserAsset(
    user_id=STUDY_AUTHOR_ID,
    nickname="Exam Coach",
    email="exam-coach@example.com",
    avatar=XIAOSHILIU_DEFAULT_AVATAR,
)
FITNESS_AUTHOR = XiaoShiLiuUserAsset(
    user_id=FITNESS_AUTHOR_ID,
    nickname="Morning Runner",
    email="morning-runner@example.com",
    avatar=XIAOSHILIU_DEFAULT_AVATAR,
)
PHOTO_AUTHOR = XiaoShiLiuUserAsset(
    user_id=PHOTO_AUTHOR_ID,
    nickname="Rain Photographer",
    email="rain-photographer@example.com",
    avatar=XIAOSHILIU_DEFAULT_AVATAR,
)
STUDY_POST = XiaoShiLiuPostAsset(
    author_user_id=STUDY_AUTHOR_ID,
    title=STUDY_TITLE,
    content="A practical review routine for vocabulary, writing drills, and exam-day pacing.",
    category="Study",
    tags=["study", "exam"],
    image_urls=["/assets/study-english-exam.png"],
    min_image_count=1,
    created_at_ms=1790845200000,
)
FITNESS_POST = XiaoShiLiuPostAsset(
    author_user_id=FITNESS_AUTHOR_ID,
    title=FITNESS_TITLE,
    content="Four weeks of short morning runs, easy stretching, and better sleep habits.",
    category="Fitness",
    tags=["fitness", "running"],
    image_urls=["/assets/morning-runs.png"],
    min_image_count=1,
    created_at_ms=1790845500000,
)
PHOTO_POST = XiaoShiLiuPostAsset(
    author_user_id=PHOTO_AUTHOR_ID,
    title=PHOTO_TITLE,
    content="A rainy walk produced clean reflections across campus paths and windows.",
    category="Photography",
    tags=["photography", "rain"],
    image_urls=["/assets/rain-reflections.png"],
    min_image_count=1,
    created_at_ms=1790845800000,
)
EXPECTED_NEW_POST = XiaoShiLiuPostAsset(
    author_user_id=XIAOSHILIU_LOGIN_USER_ID,
    title=NEW_POST_TITLE,
    content=NEW_POST_CONTENT,
    category="Travel",
    min_image_count=3,
    expected_images=tuple(ImageContentExpectation(source_path=f"assets/{filename}") for filename in UPLOAD_IMAGE_FILES),
)
EXPECTED_STUDY_LIKE = XiaoShiLiuLikeAsset(
    user_id=XIAOSHILIU_LOGIN_USER_ID,
    post_title=STUDY_TITLE,
    post_author_user_id=STUDY_AUTHOR_ID,
)
EXPECTED_STUDY_FOLLOW = XiaoShiLiuFollowAsset(
    follower_user_id=XIAOSHILIU_LOGIN_USER_ID,
    following_user_id=STUDY_AUTHOR_ID,
)
EXPECTED_FITNESS_LIKE = XiaoShiLiuLikeAsset(
    user_id=XIAOSHILIU_LOGIN_USER_ID,
    post_title=FITNESS_TITLE,
    post_author_user_id=FITNESS_AUTHOR_ID,
)
EXPECTED_PHOTO_COLLECTION = XiaoShiLiuCollectionAsset(
    user_id=XIAOSHILIU_LOGIN_USER_ID,
    post_title=PHOTO_TITLE,
    post_author_user_id=PHOTO_AUTHOR_ID,
)
EXPECTED_PHOTO_COMMENT = XiaoShiLiuCommentAsset(
    post_title=PHOTO_TITLE,
    post_author_user_id=PHOTO_AUTHOR_ID,
    author_user_id=XIAOSHILIU_LOGIN_USER_ID,
    content="Good",
)

class XiaoShiLiuMultiCategoryEngagementPostTask(BaseTask):
    apps = {"XiaoShiLiu", "Gallery"}
    difficulty = "hard"
    snapshot = "gma_ready_state"
    assets = (*UPLOAD_IMAGES, STUDY_AUTHOR, FITNESS_AUTHOR, PHOTO_AUTHOR, STUDY_POST, FITNESS_POST, PHOTO_POST)
    goal = (
        "Open XiaoShiLiu and create an image post titled \"Campus Weekend Plan\" "
        "with content \"Study first, run in the morning, and take photos after the rain.\" "
        "Choose Travel as the category and upload all three images from Gallery. "
        "Then like \"How I Scored 85 on the Graduate English Exam\" in Study and follow its author, "
        "like \"One Month of Morning Runs: My Transformation\" in Fitness, save \"Stunning Reflections After the Rain\" in Photography, "
        "and comment \"Good\" on that Photography post."
    )

    def criteria(self):
        return [
            AssetExists(EXPECTED_NEW_POST, task=self),
            AssetExists(EXPECTED_STUDY_LIKE, task=self),
            AssetExists(EXPECTED_STUDY_FOLLOW, task=self),
            AssetExists(EXPECTED_FITNESS_LIKE, task=self),
            AssetExists(EXPECTED_PHOTO_COLLECTION, task=self),
            AssetExists(EXPECTED_PHOTO_COMMENT, task=self),
        ]
