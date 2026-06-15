from __future__ import annotations

from gma.assets import ContactAsset, SmsMessageAsset
from gma.evaluation import AssetExists, AssetModified
from gma.tasks.base import BaseTask


class ContactsUpdateMasonDeleteLiamEmailMessageTask(BaseTask):
    apps = {"Contacts", "Messages"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    mason_before = ContactAsset(
        name="Mason Brooks",
        phone_number="5550101020",
        phone_label="mobile",
        email="old.ming@example.com",
        email_label="home",
    )
    mason_after = ContactAsset(
        name="Mason Brooks",
        phone_number="5550101021",
        phone_label="car",
        email="vbn@gmail.com",
        email_label="work",
    )
    liam_before = ContactAsset(
        name="Liam Carter",
        phone_number="5550101022",
        email="old.liam@example.com",
        email_label="work",
    )
    liam_after = ContactAsset(name="Liam Carter", phone_number="5550101022")
    expected_message = SmsMessageAsset(
        address=liam_before.phone_number,
        body="What is your new email address?",
        box="sent",
        read=True,
    )
    assets = (mason_before, liam_before)

    goal = (
        "Open Contacts. Update Mason Brooks's phone number to 5550101021 with the custom label "
        "\"car\", and update his email to \"vbn@gmail.com\" with the Work label. Then find Liam Carter, "
        "remove his email address, and send him exactly this text message: \"What is your new email address?\""
    )

    def criteria(self):
        return [
            AssetModified(self.mason_before, self.mason_after, task=self),
            AssetModified(self.liam_before, self.liam_after, task=self),
            AssetExists(self.expected_message, task=self),
        ]
