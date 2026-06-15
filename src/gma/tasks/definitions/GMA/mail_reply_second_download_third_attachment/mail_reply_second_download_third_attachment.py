from __future__ import annotations

from gma.assets import DeviceFileAsset, MailAccountAsset, MailAttachment, MailMessageAsset, MailReplyReference
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


NEWEST_REPLY_ATTACHMENT_TEXT = "Meeting agenda for tomorrow's discussion.\n"
OLDEST_ATTACHMENT_TEXT = "Detailed review packet from the oldest inbox email.\n"


class MailReplySecondDownloadThirdAttachmentTask(BaseTask):
    apps = {"Mail", "Files"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    user_interaction = (
        "If the agent asks what to write in the reply to the newest inbox email, respond: "
        "Reply with exactly \"Okay, see you tomorrow.\" and attach \"meeting-agenda.txt\". Do not answer unrelated questions."
    )

    account = MailAccountAsset(display_name="Jamie Park", email="jamie.park@example.com")
    middle_mail = MailMessageAsset(mailbox="inbox", from_name="Alex Reed", from_email="alex.reed@example.com", to=[account.email], subject="General Update", body="This is a middle inbox item.", timestamp_ms=202609301300, read=False)
    newest_mail = MailMessageAsset(mailbox="inbox", from_name="Blair Shaw", from_email="blair.shaw@example.com", to=[account.email], subject="Tomorrow Meeting", body="Please confirm tomorrow's meeting.", timestamp_ms=202610011300, read=False)
    oldest_mail = MailMessageAsset(
        mailbox="inbox",
        from_name="Casey Hart",
        from_email="casey.hart@example.com",
        to=[account.email],
        subject="Review Packet",
        body="The packet for careful review is attached.",
        attachments=[MailAttachment(filename="review-packet.txt", mime_type="text/plain", text_content=OLDEST_ATTACHMENT_TEXT)],
        timestamp_ms=202609291300,
        read=False,
    )
    source_file = DeviceFileAsset(app="Files", storage_dir="Download", filename="meeting-agenda.txt", mime_type="text/plain", source_path="assets/meeting-agenda.txt")
    expected_newest_reply = MailMessageAsset(
        mailbox="sent",
        from_name=account.display_name,
        from_email="test@gmail.com",
        to=[newest_mail.from_email],
        subject="RE: Tomorrow Meeting",
        body="Okay, see you tomorrow.",
        attachments=[MailAttachment(filename="meeting-agenda.txt", mime_type="text/plain", text_content=NEWEST_REPLY_ATTACHMENT_TEXT)],
        read=True,
        reply_to=MailReplyReference(from_email=newest_mail.from_email, subject=newest_mail.subject),
    )
    expected_file = DeviceFileAsset(app="Files", storage_dir="Download", filename="review-packet.txt", mime_type="text/plain", text_content=OLDEST_ATTACHMENT_TEXT)
    expected_oldest_reply = MailMessageAsset(
        mailbox="sent",
        from_name=account.display_name,
        from_email="test@gmail.com",
        to=[oldest_mail.from_email],
        subject="RE: Review Packet",
        body="I will review it carefully.",
        read=True,
        reply_to=MailReplyReference(from_email=oldest_mail.from_email, subject=oldest_mail.subject),
    )
    assets = (account, oldest_mail, middle_mail, newest_mail, source_file)

    goal = (
        "Open Mail and reply to the newest inbox email. Then open the oldest inbox email, "
        "download its attachment to Downloads, and reply to that oldest email with exactly "
        '"I will review it carefully."'
    )

    def criteria(self):
        return [AssetExists(self.expected_newest_reply, task=self), AssetExists(self.expected_file, task=self), AssetExists(self.expected_oldest_reply, task=self)]
