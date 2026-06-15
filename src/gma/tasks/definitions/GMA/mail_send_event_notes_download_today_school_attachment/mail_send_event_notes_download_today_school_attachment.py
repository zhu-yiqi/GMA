from __future__ import annotations

from gma.assets import DeviceFileAsset, MailAccountAsset, MailAttachment, MailMessageAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


SCHOOL_ATTACHMENT_TEXT = "School event attachment for planning notes.\n"


class MailSendEventNotesDownloadTodaySchoolAttachmentTask(BaseTask):
    apps = {"Mail", "Files"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    account = MailAccountAsset(display_name="Avery Cole", email="avery.chen@example.com")
    previous_school_mail = MailMessageAsset(
        mailbox="inbox",
        from_name="School Office",
        from_email="school.office@example.com",
        to=[account.email],
        subject="School Update",
        body="The school update has no attachment.",
        timestamp_ms=1790758800000,
        read=False,
    )
    current_school_mail = MailMessageAsset(
        mailbox="inbox",
        from_name="School Office",
        from_email="school.office@example.com",
        to=[account.email],
        subject="School Materials",
        body="The school materials are attached here.",
        attachments=[
            MailAttachment(
                filename="school-event-notes.txt",
                mime_type="text/plain",
                text_content=SCHOOL_ATTACHMENT_TEXT,
            )
        ],
        timestamp_ms=1790845200000,
        read=False,
    )
    expected_first_mail = MailMessageAsset(
        mailbox="sent",
        from_name=account.display_name,
        from_email="test@gmail.com",
        to=["dag@gmail.com"],
        subject="Event Arrangement",
        body="You are responsible for arranging visitors.",
        read=True,
    )
    expected_second_mail = MailMessageAsset(
        mailbox="sent",
        from_name=account.display_name,
        from_email="test@gmail.com",
        to=["amx@gmail.com"],
        subject="Event Arrangement",
        body="You are responsible for distributing props to everyone.",
        read=True,
    )
    expected_file = DeviceFileAsset(
        app="Files",
        storage_dir="Download",
        filename="school-event-notes.txt",
        mime_type="text/plain",
        text_content=SCHOOL_ATTACHMENT_TEXT,
    )
    assets = (account, previous_school_mail, current_school_mail)

    goal = (
        "Open Mail and send an email to dag@gmail.com with subject "
        '"Event Arrangement" and body "You are responsible for arranging visitors." '
        "Send another email to amx@gmail.com with subject "
        '"Event Arrangement" and body "You are responsible for distributing props to everyone." '
        "Then download the attachment from the school inbox email dated today."
    )

    def criteria(self):
        return [
            AssetExists(self.expected_first_mail, task=self),
            AssetExists(self.expected_second_mail, task=self),
            AssetExists(self.expected_file, task=self),
        ]
