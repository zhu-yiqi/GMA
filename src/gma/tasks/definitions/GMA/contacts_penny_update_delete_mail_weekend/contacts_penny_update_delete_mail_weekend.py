from __future__ import annotations

from gma.assets import ContactAsset, MailAccountAsset, MailMessageAsset
from gma.evaluation import AssetDeleted, AssetExists, AssetModified
from gma.tasks.base import BaseTask


class ContactsPennyUpdateDeleteMailWeekendTask(BaseTask):
    apps = {"Contacts", "Mail"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    qian_before = ContactAsset(name="Penny Clark", phone_number="5550101018", phone_label="mobile")
    qian_after = ContactAsset(
        name="Penny Clark",
        phone_number="5550101018",
        phone_label="other",
        email="4561789@gmail.com",
        website="https://example.com/weekend",
    )
    delete_contact = ContactAsset(name="Quinn Parker", phone_number="5550101019")
    account = MailAccountAsset(display_name="Casey Morgan", email="casey.morgan@example.com")
    expected_mail = MailMessageAsset(
        mailbox="sent",
        from_name=account.display_name,
        from_email="test@gmail.com",
        to=["4561789@gmail.com"],
        subject="Weekend Date",
        body="Let's watch a movie together this weekend",
        read=True,
    )
    assets = (qian_before, delete_contact, account)

    goal = (
        "Open Contacts. Find Penny Clark, change the phone label to Other, add email "
        "\"4561789@gmail.com\", and add website \"https://example.com/weekend\". Delete the Quinn Parker "
        "contact. Then open Mail and send a message to \"4561789@gmail.com\" with subject "
        "\"Weekend Date\" and body \"Let's watch a movie together this weekend\"."
    )

    def criteria(self):
        return [
            AssetModified(self.qian_before, self.qian_after, task=self),
            AssetDeleted(self.delete_contact, task=self),
            AssetExists(self.expected_mail, task=self),
        ]
