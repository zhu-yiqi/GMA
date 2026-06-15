from __future__ import annotations

from gma.assets import DeviceFileAsset, MailAccountAsset, MailAttachment, MailMessageAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


ATTACHMENT_TEXT = "Draft talking points for the vendor follow-up call.\n"


class MailSendWorkNoteWithAttachmentTask(BaseTask):
    apps = {"Mail", "Files"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    account = MailAccountAsset(
        display_name="Casey Rowan",
        email="casey.rowan@example.com",
    )
    source_file = DeviceFileAsset(
        app="Files",
        storage_dir="Download",
        filename="project-brief.txt",
        mime_type="text/plain",
        source_path="assets/project-brief.txt",
    )
    expected_mail = MailMessageAsset(
        mailbox="sent",
        from_name=account.display_name,
        from_email="test@gmail.com",
        to=["ccc@gmail.com"],
        subject="Work",
        body="Remember to reply.",
        attachments=[
            MailAttachment(
                filename="project-brief.txt",
                mime_type="text/plain",
                text_content=ATTACHMENT_TEXT,
            )
        ],
        read=True,
    )
    assets = (account, source_file)

    goal = (
        "Open Mail and send an email to ccc@gmail.com with subject \"Work\", "
        "body \"Remember to reply.\", and attach the Downloads file "
        "\"project-brief.txt\"."
    )

    def criteria(self):
        return [AssetExists(self.expected_mail, task=self)]
