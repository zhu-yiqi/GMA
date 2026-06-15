from __future__ import annotations

from gma.assets import ContactAsset, SmsMessageAsset
from gma.evaluation import AssetExists, AssetModified
from gma.tasks.base import BaseTask


class ContactsUpdateWendyMessageLiamFlightTimeTask(BaseTask):
    apps = {"Contacts", "Messages"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    wendy_before = ContactAsset(name="Wendy Parker", phone_number="5550101030", phone_label="mobile")
    wendy_after = ContactAsset(
        name="Wendy Parker",
        phone_number="5550101031",
        phone_label="Company Main",
        email="mnb@gmail.com",
        email_label="work",
    )
    liam_contact = ContactAsset(name="Liam Carter", phone_number="5550101032")
    expected_message = SmsMessageAsset(
        address=liam_contact.phone_number,
        body="What time is your flight?",
        box="sent",
        read=True,
    )
    assets = (wendy_before, liam_contact)

    goal = (
        "Open Contacts, update Wendy Parker's phone number to 5550101031, set the phone label to "
        "the Company Main label, and add email \"mnb@gmail.com\" with the Work label. "
        "Then open Messages and send Liam Carter exactly this message: \"What time is your flight?\""
    )

    def criteria(self):
        return [
            AssetModified(self.wendy_before, self.wendy_after, task=self),
            AssetExists(self.expected_message, task=self),
        ]
