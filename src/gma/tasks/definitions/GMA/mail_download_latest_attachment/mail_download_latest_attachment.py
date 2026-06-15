from __future__ import annotations

from gma.assets import DeviceFileAsset, MailAccountAsset, MailAttachment, MailMessageAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


TARGET_ATTACHMENT_TEXT = "Venue map: use the north entrance and room B12.\n"
OLDER_ATTACHMENT_TEXT = "Old invoice reference: INV-2041.\n"


class MailDownloadLatestAttachmentTask(BaseTask):
    apps = {"Mail", "Files"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    account = MailAccountAsset(
        display_name="Riley Adams",
        email="riley.adams@example.com",
    )
    older_attachment_mail = MailMessageAsset(
        mailbox="inbox",
        from_name="Nora Fields",
        from_email="nora.fields@example.com",
        to=[account.email],
        subject="Old Invoice Copy",
        body="The older invoice copy is attached for reference.",
        attachments=[
            MailAttachment(
                filename="old-invoice.txt",
                mime_type="text/plain",
                text_content=OLDER_ATTACHMENT_TEXT,
            )
        ],
        timestamp_ms=202610010845,
        read=True,
    )
    target_mail = MailMessageAsset(
        mailbox="inbox",
        from_name="Sam Keller",
        from_email="sam.keller@example.com",
        to=[account.email],
        subject="Venue Map Attachment",
        body="Please use the attached venue map for check-in.",
        attachments=[
            MailAttachment(
                filename="venue-map.txt",
                mime_type="text/plain",
                text_content=TARGET_ATTACHMENT_TEXT,
            )
        ],
        timestamp_ms=202610010935,
        read=False,
    )
    newer_plain_mail = MailMessageAsset(
        mailbox="inbox",
        from_name="Ivy Brooks",
        from_email="ivy.brooks@example.com",
        to=[account.email],
        subject="No Attachment Update",
        body="No file is needed for this update.",
        timestamp_ms=202610010950,
        read=False,
    )
    expected_file = DeviceFileAsset(
        app="Files",
        storage_dir="Download",
        filename="venue-map.txt",
        mime_type="text/plain",
        text_content=TARGET_ATTACHMENT_TEXT,
    )
    assets = (account, older_attachment_mail, target_mail, newer_plain_mail)

    goal = (
        "Open Mail, find the newest inbox email that includes an attachment, "
        "and download its attachment to Downloads."
    )

    def criteria(self):
        return [AssetExists(self.expected_file, task=self)]
