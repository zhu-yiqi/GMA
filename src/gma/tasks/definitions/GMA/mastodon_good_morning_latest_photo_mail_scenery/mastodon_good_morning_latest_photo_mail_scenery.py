
from __future__ import annotations

from gma.assets import (
    DeviceFileAsset,
    MailAccountAsset,
    MailAttachment,
    MailMessageAsset,
    MastodonBookmarkAsset,
    MastodonMediaAttachment,
    MastodonMediaStatusAsset,
    MastodonSessionAsset,
)
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


MAIN_USER = "owner"
POST_TEXT = "Good morning"
SCENERY_ATTACHMENT_TEXT = "Scenery attachment notes for the morning photo task.\n"
LATEST_PHOTO = "mastodon-good-morning-latest-photo-mail-scenery-phone-gallery-3.png"


class MastodonGoodMorningLatestPhotoMailSceneryTask(BaseTask):
    apps = {"Mastodon", "Gallery", "Mail", "Files"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    older_photo = DeviceFileAsset(app="Gallery", storage_dir="DCIM/Camera", filename="mastodon-good-morning-latest-photo-mail-scenery-phone-gallery-1.png", mime_type="image/png", source_path="assets/mastodon-good-morning-latest-photo-mail-scenery-phone-gallery-1.png")
    middle_photo = DeviceFileAsset(app="Gallery", storage_dir="DCIM/Camera", filename="mastodon-good-morning-latest-photo-mail-scenery-phone-gallery-2.png", mime_type="image/png", source_path="assets/mastodon-good-morning-latest-photo-mail-scenery-phone-gallery-2.png")
    latest_photo = DeviceFileAsset(app="Gallery", storage_dir="DCIM/Camera", filename=LATEST_PHOTO, mime_type="image/png", source_path="assets/mastodon-good-morning-latest-photo-mail-scenery-phone-gallery-3.png")
    attachment_file = DeviceFileAsset(app="Files", storage_dir="Download", filename="morning-scenery-notes.txt", mime_type="text/plain", source_path="assets/morning-scenery-notes.txt")
    mail_account = MailAccountAsset(display_name="Riley Morgan", email="riley.morgan@example.com")
    expected_status = MastodonMediaStatusAsset(
        username=MAIN_USER,
        text=POST_TEXT,
        visibility="public",
        media_attachments=(MastodonMediaAttachment(filename=LATEST_PHOTO, mime_type="image/png", source_path="assets/mastodon-good-morning-latest-photo-mail-scenery-phone-gallery-3.png"),),
    )
    expected_bookmark = MastodonBookmarkAsset(actor_username=MAIN_USER, target_username=MAIN_USER, target_text=POST_TEXT)
    expected_mail = MailMessageAsset(
        mailbox="sent",
        from_name=mail_account.display_name,
        from_email="test@gmail.com",
        to=["sam.rivera@example.com"],
        subject="Scenery",
        body="",
        attachments=[MailAttachment(filename="morning-scenery-notes.txt", mime_type="text/plain", text_content=SCENERY_ATTACHMENT_TEXT)],
        read=True,
    )
    assets = (older_photo, middle_photo, latest_photo, attachment_file, mail_account, MastodonSessionAsset(username=MAIN_USER))

    goal = (
        "Open Mastodon and publish a public post with exactly \"Good morning\". "
        "Attach the latest photo from the phone gallery, then bookmark that post. "
        "Open Mail and send an email to sam.rivera@example.com with subject \"Scenery\", "
        "no body text, and attach the Downloads file \"morning-scenery-notes.txt\"."
    )

    def criteria(self):
        return [
            AssetExists(self.expected_status, task=self),
            AssetExists(self.expected_bookmark, task=self),
            AssetExists(self.expected_mail, task=self),
        ]
