from __future__ import annotations

from gma.assets import MailAccountAsset, MailMessageAsset, MailReplyReference
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


class MailReplyToLatestInboxUpdateTask(BaseTask):
    apps = {"Mail"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    account = MailAccountAsset(
        display_name="Jordan Patel",
        email="jordan.patel@example.com",
    )
    older_mail = MailMessageAsset(
        mailbox="inbox",
        from_name="Lena Ortiz",
        from_email="lena.ortiz@example.com",
        to=[account.email],
        subject="Parking Pass",
        body="The visitor parking pass is ready at the front desk.",
        timestamp_ms=202610010820,
        read=True,
    )
    middle_mail = MailMessageAsset(
        mailbox="inbox",
        from_name="Miles Reed",
        from_email="miles.reed@example.com",
        to=[account.email],
        subject="Coffee Order",
        body="I moved the coffee order pickup to 9:30 AM.",
        timestamp_ms=202610010900,
        read=True,
    )
    latest_mail = MailMessageAsset(
        mailbox="inbox",
        from_name="Priya Shah",
        from_email="priya.shah@example.com",
        to=[account.email],
        subject="Venue Headcount",
        body="Can you confirm the revised room count?",
        timestamp_ms=202610010940,
        read=False,
    )
    expected_reply = MailMessageAsset(
        mailbox="sent",
        from_name=account.display_name,
        from_email="test@gmail.com",
        to=[latest_mail.from_email],
        subject="RE: Venue Headcount",
        body="Got it.",
        read=True,
        reply_to=MailReplyReference(
            from_email=latest_mail.from_email,
            subject=latest_mail.subject,
        ),
    )
    assets = (account, older_mail, middle_mail, latest_mail)

    goal = (
        "Open Mail, reply to the newest email in the inbox, "
        "and send exactly this reply body: \"Got it.\""
    )

    def criteria(self):
        return [AssetExists(self.expected_reply, task=self)]
