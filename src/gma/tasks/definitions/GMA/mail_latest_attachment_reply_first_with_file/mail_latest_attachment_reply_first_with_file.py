from __future__ import annotations

from gma.assets import DeviceFileAsset, MailAccountAsset, MailAttachment, MailMessageAsset, MailReplyReference
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


LATEST_ATTACHMENT_TEXT = "Latest version attachment: final edits and approval notes.\n"
OLDER_ATTACHMENT_TEXT = "Older version attachment: draft edits only.\n"


class MailLatestAttachmentReplyFirstWithFileTask(BaseTask):
    apps = {"Mail", "Files"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    account = MailAccountAsset(display_name="Cameron Ellis", email="cameron.ellis@example.com")
    first_mail = MailMessageAsset(mailbox="inbox", from_name="Pat Green", from_email="pat.green@example.com", to=[account.email], subject="Need Latest Version", body="Please send me the latest version when you have it.", timestamp_ms=202610011300, read=False)
    target_attachment_mail = MailMessageAsset(
        mailbox="inbox",
        from_name="Quinn Davis",
        from_email="quinn.davis@example.com",
        to=[account.email],
        subject="Latest Version Attachment",
        body="The latest version is attached.",
        attachments=[MailAttachment(filename="latest-version.txt", mime_type="text/plain", text_content=LATEST_ATTACHMENT_TEXT)],
        timestamp_ms=202609301300,
        read=False,
    )
    older_attachment_mail = MailMessageAsset(
        mailbox="inbox",
        from_name="Rowan Bell",
        from_email="rowan.bell@example.com",
        to=[account.email],
        subject="Older Version Attachment",
        body="This older version is attached for reference.",
        attachments=[MailAttachment(filename="older-version.txt", mime_type="text/plain", text_content=OLDER_ATTACHMENT_TEXT)],
        timestamp_ms=202609291300,
        read=True,
    )
    expected_file = DeviceFileAsset(app="Files", storage_dir="Download", filename="latest-version.txt", mime_type="text/plain", text_content=LATEST_ATTACHMENT_TEXT)
    expected_reply = MailMessageAsset(
        mailbox="sent",
        from_name=account.display_name,
        from_email="test@gmail.com",
        to=[first_mail.from_email],
        subject="RE: Need Latest Version",
        body="This is the latest version, please review.",
        attachments=[MailAttachment(filename="latest-version.txt", mime_type="text/plain", text_content=LATEST_ATTACHMENT_TEXT)],
        read=True,
        reply_to=MailReplyReference(from_email=first_mail.from_email, subject=first_mail.subject),
    )
    assets = (account, older_attachment_mail, target_attachment_mail, first_mail)

    goal = (
        'Open Mail, find the newest inbox email that has an attachment, and download that attachment '
        'to Downloads. Then reply to the inbox email titled "Need Latest Version" with exactly '
        '"This is the latest version, please review." and attach the downloaded file.'
    )

    def criteria(self):
        return [AssetExists(self.expected_file, task=self), AssetExists(self.expected_reply, task=self)]
