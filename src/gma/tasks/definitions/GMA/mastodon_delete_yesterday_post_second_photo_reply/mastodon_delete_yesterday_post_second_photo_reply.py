
from __future__ import annotations

from gma.assets import DeviceFileAsset, MastodonMediaAttachment, MastodonMediaStatusAsset, MastodonSessionAsset, MastodonStatusAsset
from gma.evaluation import AssetDeleted, AssetExists
from gma.tasks.base import BaseTask


MAIN_USER = "owner"
FIRST_YESTERDAY = "First yesterday note about campus errands."
SECOND_YESTERDAY = "Second yesterday note for cleanup."
POST_TEXT = "Good morning"
REPLY_TEXT = "The sunshine is really nice today."
FIRST_PHOTO = "mastodon-delete-yesterday-post-second-photo-reply-phone-gallery-1.png"
SECOND_PHOTO = "mastodon-delete-yesterday-post-second-photo-reply-phone-gallery-2.png"
EXPECTED_PHOTO = FIRST_PHOTO


class MastodonDeleteYesterdayPostSecondPhotoReplyTask(BaseTask):
    apps = {"Mastodon", "Gallery"}
    difficulty = "medium"
    category = ['Information-Gathering Tasks']
    snapshot = "gma_ready_state"
    user_interaction = (
        "If the agent asks which of the posts from yesterday to delete, answer exactly: "
        "Delete the second one, the post that says \"Second yesterday note for cleanup.\" "
        "Do not answer unrelated questions."
    )

    first_yesterday_post = MastodonStatusAsset(username=MAIN_USER, text=FIRST_YESTERDAY, visibility="public", created_at_ms=202609300900)
    second_yesterday_post = MastodonStatusAsset(username=MAIN_USER, text=SECOND_YESTERDAY, visibility="public", created_at_ms=202609301300)
    first_photo = DeviceFileAsset(app="Gallery", storage_dir="DCIM/Camera", filename=FIRST_PHOTO, mime_type="image/png", source_path=f"assets/{FIRST_PHOTO}")
    second_photo = DeviceFileAsset(app="Gallery", storage_dir="DCIM/Camera", filename=SECOND_PHOTO, mime_type="image/png", source_path=f"assets/{SECOND_PHOTO}")
    expected_status = MastodonMediaStatusAsset(
        username=MAIN_USER,
        text=POST_TEXT,
        visibility="public",
        media_attachments=(MastodonMediaAttachment(filename=EXPECTED_PHOTO, mime_type="image/png", source_path=f"assets/{EXPECTED_PHOTO}"),),
    )
    expected_reply = MastodonStatusAsset(username=MAIN_USER, text=REPLY_TEXT, visibility="public", reply_to_username=MAIN_USER, reply_to_text=POST_TEXT)
    assets = (first_yesterday_post, second_yesterday_post, first_photo, second_photo, MastodonSessionAsset(username=MAIN_USER))

    goal = (
        "Open Mastodon and delete the post you made yesterday. "
        "Then publish a new public post with exactly \"Good morning\", attach the second photo from the phone gallery, "
        "and after it posts successfully reply to your new post with exactly \"The sunshine is really nice today.\""
    )

    def criteria(self):
        return [
            AssetDeleted(self.second_yesterday_post, task=self),
            AssetExists(self.expected_status, task=self),
            AssetExists(self.expected_reply, task=self),
        ]
