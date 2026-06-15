from __future__ import annotations

from gma.assets import ContactAsset, MailAccountAsset, MailMessageAsset
from gma.evaluation import AssetDeleted, AssetExists
from gma.tasks.base import BaseTask


class ContactsLilyMailDateReplyTask(BaseTask):
    apps = {"Contacts", "Mail"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    delete_contact = ContactAsset(name="Grace Bennett", phone_number="5550101016")
    lili_contact = ContactAsset(
        name="Lily",
        phone_number="5550101017",
        phone_label="pager",
        email="fed@gmail.com",
        email_label="work",
    )
    account = MailAccountAsset(display_name="Avery Cole", email="avery.cole@example.com")
    expected_mail = MailMessageAsset(
        mailbox="sent",
        from_name=account.display_name,
        from_email="test@gmail.com",
        to=["fed@gmail.com"],
        subject="Date",
        body="Remember to submit the draft on time.",
        read=True,
    )
    assets = (delete_contact, account)

    goal = (
        "Delete the Grace Bennett contact. Create a Contacts entry named Lily with phone number 5550101017 "
        "labeled \"pager\" and work email \"fed@gmail.com\". Then open Mail and send an email to "
        "Lily's work email with subject \"Date\" and body \"Remember to submit the draft on time.\""
    )

    def criteria(self):
        return [
            AssetDeleted(self.delete_contact, task=self),
            AssetExists(self.lili_contact, task=self),
            AssetExists(self.expected_mail, task=self),
        ]
