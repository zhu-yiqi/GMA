from __future__ import annotations

from gma.assets import DeviceFileAsset, MailAccountAsset, MailAttachment, MailMessageAsset, MailReplyReference
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


INVITATION_TEXT = "Opening ceremony invitation details.\n"
REPLY_TEXT = "Received."


class MailSendInvitationAttachmentReplyLatestTask(BaseTask):
    apps = {"Mail", "Files"}
    difficulty = "medium"
    category = []
    snapshot = "gma_ready_state"

    account = MailAccountAsset(display_name="Riley Bennett", email="riley.bennett@example.com")
    source_file = DeviceFileAsset(
        app="Files",
        storage_dir="Download",
        filename="invitation.txt",
        mime_type="text/plain",
        text_content=INVITATION_TEXT,
    )
    earlier_mail = MailMessageAsset(
        mailbox="inbox",
        from_name="Nora Fields",
        from_email="nora.fields@example.com",
        to=[account.email],
        subject="Project Check-in",
        body="Please keep this note for your records.",
        timestamp_ms=202609301100,
        read=False,
    )
    recent_mail = MailMessageAsset(
        mailbox="inbox",
        from_name="Mia Parker",
        from_email="mia.parker@example.com",
        to=[account.email],
        subject="Receipt Confirmation",
        body="Please confirm receipt.",
        timestamp_ms=202610011220,
        read=False,
    )
    expected_sent_mail = MailMessageAsset(
        mailbox="sent",
        from_name=account.display_name,
        from_email="test@gmail.com",
        to=["cxz@gmail.com"],
        subject="Invitation",
        body="We sincerely invite you to attend the opening ceremony this Friday",
        attachments=[MailAttachment(filename="invitation.txt", mime_type="text/plain", text_content=INVITATION_TEXT)],
        read=True,
    )
    expected_reply = MailMessageAsset(
        mailbox="sent",
        from_name=account.display_name,
        from_email="test@gmail.com",
        to=[recent_mail.from_email],
        subject="RE: Receipt Confirmation",
        body=REPLY_TEXT,
        read=True,
        reply_to=MailReplyReference(from_email=recent_mail.from_email, subject=recent_mail.subject),
    )
    assets = (account, source_file, earlier_mail, recent_mail)

    goal = (
        "Open Mail and send an email to cxz@gmail.com with subject \"Invitation\", body "
        "\"We sincerely invite you to attend the opening ceremony this Friday\", and attach the "
        "Downloads file \"invitation.txt\". Then reply to the most recent inbox email with exactly "
        "\"Received.\""
    )

    def criteria(self):
        return [
            AssetExists(self.expected_sent_mail, task=self),
            AssetExists(self.expected_reply, task=self),
        ]
