from __future__ import annotations

from gma.assets import DeviceFileAsset, MastodonMediaAttachment, MastodonMediaStatusAsset, MastodonSessionAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


MAIN_USER = "owner"
LATEST_PHOTO = "sunny_cafe_latest.png"
POST_TEXT = "The weather is really nice today"


class MastodonPostLatestGalleryPhotoWeatherTask(BaseTask):
    apps = {"Mastodon", "Gallery"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    older_photo = DeviceFileAsset(
        app="Gallery",
        storage_dir="DCIM/Camera",
        filename="morning_books.png",
        mime_type="image/png",
        source_path="assets/morning_books.png",
    )
    middle_photo = DeviceFileAsset(
        app="Gallery",
        storage_dir="DCIM/Camera",
        filename="desk_sunlight.png",
        mime_type="image/png",
        source_path="assets/desk_sunlight.png",
    )
    latest_photo = DeviceFileAsset(
        app="Gallery",
        storage_dir="DCIM/Camera",
        filename=LATEST_PHOTO,
        mime_type="image/png",
        source_path="assets/sunny_cafe_latest.png",
    )
    expected_status = MastodonMediaStatusAsset(
        username=MAIN_USER,
        text=POST_TEXT,
        visibility="public",
        media_attachments=(
            MastodonMediaAttachment(
                filename=LATEST_PHOTO,
                mime_type="image/png",
                source_path="assets/sunny_cafe_latest.png",
            ),
        ),
    )
    assets = (older_photo, middle_photo, latest_photo, MastodonSessionAsset(username=MAIN_USER))

    goal = (
        "Open Mastodon and publish a public post with exactly "
        '"The weather is really nice today". Attach the latest photo from the phone gallery.'
    )

    def criteria(self):
        return [AssetExists(self.expected_status, task=self)]
