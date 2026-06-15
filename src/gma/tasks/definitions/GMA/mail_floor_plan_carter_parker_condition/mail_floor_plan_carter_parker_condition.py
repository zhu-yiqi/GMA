from __future__ import annotations

from gma.assets import DeviceFileAsset, MailAccountAsset, MailAttachment, MailMessageAsset, MailReplyReference
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


HOUSE_TEXT = "House plan notes: two bedrooms, south-facing balcony, fair price range.\n"


class MailFloorPlanCarterParkerConditionTask(BaseTask):
    apps = {"Mail", "Files"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    account = MailAccountAsset(display_name="Riley Morgan", email="riley.morgan@example.com")
    first_mail = MailMessageAsset(mailbox="inbox", from_name="Jordan Ellis", from_email="client.one@example.com", to=[account.email], subject="Viewing Time", body="Can we visit the apartment this afternoon?", timestamp_ms=202610011100, read=False)
    second_mail = MailMessageAsset(mailbox="inbox", from_name="Carter Cole", from_email="carter.cole@example.com", to=[account.email], subject="Looking for a Listing", body="Please help me find a suitable listing.", timestamp_ms=202610011050, read=False)
    third_mail = MailMessageAsset(mailbox="inbox", from_name="Avery Grant", from_email="client.three@example.com", to=[account.email], subject="Budget Range", body="My budget range has changed slightly.", timestamp_ms=202610011040, read=False)
    fourth_mail = MailMessageAsset(mailbox="inbox", from_name="Parker Reed", from_email="client.four@example.com", to=[account.email], subject="Parking Question", body="Is parking included?", timestamp_ms=202610011030, read=False)
    fifth_mail = MailMessageAsset(mailbox="inbox", from_name="Taylor West", from_email="taylor.west@example.com", to=[account.email], subject="Follow-up Needed", body="Please confirm whether you received my request.", timestamp_ms=202610011020, read=False)
    source_file = DeviceFileAsset(app="Files", storage_dir="Download", filename="floor-plan-notes.txt", mime_type="text/plain", source_path="assets/floor-plan-notes.txt")
    expected_sent_mail = MailMessageAsset(
        mailbox="sent",
        from_name=account.display_name,
        from_email="test@gmail.com",
        to=["amx@gmail.com"],
        subject="Floor Plan Sharing",
        body="Please review this floor plan; the price is very reasonable.",
        attachments=[MailAttachment(filename="floor-plan-notes.txt", mime_type="text/plain", text_content=HOUSE_TEXT)],
        read=True,
    )
    expected_carter_reply = MailMessageAsset(
        mailbox="sent",
        from_name=account.display_name,
        from_email="test@gmail.com",
        to=[second_mail.from_email],
        subject="RE: Looking for a Listing",
        body="I'll find it for you right away.",
        read=True,
        reply_to=MailReplyReference(from_email=second_mail.from_email, subject=second_mail.subject),
    )
    expected_taylor_reply = MailMessageAsset(
        mailbox="sent",
        from_name=account.display_name,
        from_email="test@gmail.com",
        to=[fifth_mail.from_email],
        subject="RE: Follow-up Needed",
        body="Okay, okay.",
        read=True,
        reply_to=MailReplyReference(from_email=fifth_mail.from_email, subject=fifth_mail.subject),
    )
    assets = (account, fifth_mail, fourth_mail, third_mail, second_mail, first_mail, source_file)

    goal = (
        "Open Mail and send an email to amx@gmail.com with subject "
        '"Floor Plan Sharing", body "Please review this floor plan; the price is very reasonable.", '
        "and attach the Downloads file \"floor-plan-notes.txt\". Also reply to Carter's email with exactly "
        '"I\'ll find it for you right away." If the fifth inbox email is from Taylor, reply to it with exactly '
        '"Okay, okay."'
    )

    def criteria(self):
        return [
            AssetExists(self.expected_sent_mail, task=self),
            AssetExists(self.expected_carter_reply, task=self),
            AssetExists(self.expected_taylor_reply, task=self),
        ]
