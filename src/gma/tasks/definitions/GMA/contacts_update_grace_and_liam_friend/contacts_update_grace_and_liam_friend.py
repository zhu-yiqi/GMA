from __future__ import annotations

from gma.assets import ContactAsset
from gma.evaluation import AssetModified
from gma.tasks.base import BaseTask


class ContactsUpdateGraceAndLiamFriendTask(BaseTask):
    apps = {"Contacts"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    grace_before = ContactAsset(
        name="Grace Bennett",
        phone_number="5550101028",
        phone_label="mobile",
        email="old.grace@example.com",
        email_label="work",
    )
    grace_after = ContactAsset(
        name="Grace Bennett",
        phone_number="5550101028",
        phone_label="Work Fax",
    )
    liam_before = ContactAsset(name="Liam Cartern", phone_number="5550101029", phone_label="mobile")
    darin_after = ContactAsset(
        name="Darin Lin",
        phone_number="5550101029",
        phone_label="home",
        email="vgy@gmail.com",
        label="friend",
    )
    assets = (grace_before, liam_before)

    goal = (
        "Open Contacts. For Grace Bennett, remove the email address if possible and set the phone label "
        "to the Work Fax label. Then find Liam Cartern, rename him to Darin Lin, set his "
        "phone label to Home, add email \"vgy@gmail.com\", and assign the contact label \"friend\". "
        "If the friend label is already present, answer that no label action is needed."
    )

    def criteria(self):
        return [
            AssetModified(self.grace_before, self.grace_after, task=self),
            AssetModified(self.liam_before, self.darin_after, task=self),
        ]
