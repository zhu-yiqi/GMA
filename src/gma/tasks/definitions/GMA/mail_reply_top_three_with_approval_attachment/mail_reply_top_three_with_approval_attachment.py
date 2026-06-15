from __future__ import annotations

from gma.assets import DeviceFileAsset, MailAccountAsset, MailAttachment, MailMessageAsset, MailReplyReference
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


FILE_TEXT = "Approval notes for the approval reply.\n"


class MailReplyTopThreeWithApprovalAttachmentTask(BaseTask):
    apps = {"Mail", "Files"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    account = MailAccountAsset(display_name="Taylor Brooks", email="taylor.brooks@example.com")
    first_mail = MailMessageAsset(
        mailbox="inbox",
        from_name="Nora Fields",
        from_email="nora.fields@example.com",
        to=[account.email],
        subject="Need Confirmation",
        body="Please confirm you received this message.",
        timestamp_ms=1790850600000,
        read=False,
    )
    second_mail = MailMessageAsset(
        mailbox="inbox",
        from_name="Liam Stone",
        from_email="liam.stone@example.com",
        to=[account.email],
        subject="Meeting Attendance",
        body="Can you attend tomorrow's meeting?",
        timestamp_ms=1790850000000,
        read=False,
    )
    third_mail = MailMessageAsset(
        mailbox="inbox",
        from_name="Mia Wong",
        from_email="mia.wong@example.com",
        to=[account.email],
        subject="Quick Approval",
        body="Please send back the file when you reply.",
        timestamp_ms=1790849400000,
        read=False,
    )
    source_file = DeviceFileAsset(app="Files", storage_dir="Download", filename="approval-notes.txt", mime_type="text/plain", source_path="assets/approval-notes.txt")
    expected_first_reply = MailMessageAsset(
        mailbox="sent",
        from_name=account.display_name,
        from_email="test@gmail.com",
        to=[first_mail.from_email],
        subject="RE: Need Confirmation",
        body="Email received; I will contact you if needed.",
        read=True,
        reply_to=MailReplyReference(from_email=first_mail.from_email, subject=first_mail.subject),
    )
    expected_second_reply = MailMessageAsset(
        mailbox="sent",
        from_name=account.display_name,
        from_email="test@gmail.com",
        to=[second_mail.from_email],
        subject="RE: Meeting Attendance",
        body="I will attend on time.",
        read=True,
        reply_to=MailReplyReference(from_email=second_mail.from_email, subject=second_mail.subject),
    )
    expected_third_reply = MailMessageAsset(
        mailbox="sent",
        from_name=account.display_name,
        from_email="test@gmail.com",
        to=[third_mail.from_email],
        subject="RE: Quick Approval",
        body="OK.",
        attachments=[MailAttachment(filename="approval-notes.txt", mime_type="text/plain", text_content=FILE_TEXT)],
        read=True,
        reply_to=MailReplyReference(from_email=third_mail.from_email, subject=third_mail.subject),
    )
    assets = (account, third_mail, second_mail, first_mail, source_file)

    goal = (
        'Open Mail and work through the three newest inbox emails. Reply to the newest email with '
        '"Email received; I will contact you if needed." Reply to the next-newest email with '
        '"I will attend on time." Reply to the oldest of those three emails with "OK." and attach the '
        'Downloads file "approval-notes.txt" to that reply.'
    )

    def criteria(self):
        return [
            AssetExists(self.expected_first_reply, task=self),
            AssetExists(self.expected_second_reply, task=self),
            AssetExists(self.expected_third_reply, task=self),
        ]
