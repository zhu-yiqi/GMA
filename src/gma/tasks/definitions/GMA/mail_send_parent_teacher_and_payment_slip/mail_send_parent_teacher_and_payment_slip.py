from __future__ import annotations

from gma.assets import DeviceFileAsset, MailAccountAsset, MailAttachment, MailMessageAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


SLIP_TEXT = "Payment slip for the parent-teacher conference fee.\n"


class MailSendParentTeacherAndPaymentSlipTask(BaseTask):
    apps = {"Mail", "Files"}
    difficulty = "medium"
    category = []
    snapshot = "gma_ready_state"

    account = MailAccountAsset(display_name="Morgan Ellis", email="morgan.ellis@example.com")
    replacement_file = DeviceFileAsset(
        app="Files",
        storage_dir="Download",
        filename="payment-slip.txt",
        mime_type="text/plain",
        text_content=SLIP_TEXT,
    )
    expected_parent_mail = MailMessageAsset(
        mailbox="sent",
        from_name=account.display_name,
        from_email="test@gmail.com",
        to=["vgn@gmail.com"],
        subject="Parent-Teacher Conference",
        body="The school will hold a parent-teacher conference this Friday; please attend on time.",
        read=True,
    )
    expected_payment_mail = MailMessageAsset(
        mailbox="sent",
        from_name=account.display_name,
        from_email="test@gmail.com",
        to=["jin@gmail.com"],
        subject="Payment Slip",
        body="Please find the payment slip attached. Kindly confirm receipt upon receipt.",
        attachments=[MailAttachment(filename="payment-slip.txt", mime_type="text/plain", text_content=SLIP_TEXT)],
        read=True,
    )
    assets = (account, replacement_file)

    goal = (
        "Open Mail and send one email to vgn@gmail.com with subject \"Parent-Teacher Conference\" "
        "and body \"The school will hold a parent-teacher conference this Friday; please attend on time.\" "
        "Then send another email to jin@gmail.com with subject \"Payment Slip\", body "
        "\"Please find the payment slip attached. Kindly confirm receipt upon receipt.\", and attach "
        "the Downloads file \"payment-slip.txt\"."
    )

    def criteria(self):
        return [
            AssetExists(self.expected_parent_mail, task=self),
            AssetExists(self.expected_payment_mail, task=self),
        ]
