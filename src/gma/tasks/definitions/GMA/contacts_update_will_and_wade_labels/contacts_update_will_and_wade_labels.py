from __future__ import annotations

from gma.assets import ContactAsset
from gma.evaluation import AssetModified
from gma.tasks.base import BaseTask


class ContactsUpdateWillAndWadeLabelsTask(BaseTask):
    apps = {"Contacts"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    wu_before = ContactAsset(name="Will Bennett", phone_number="5550101033", phone_label="mobile")
    wu_after = ContactAsset(
        name="Leo Parker",
        phone_number="5550101033",
        phone_label="mobile",
        email="jhg@gmail.com",
        email_label="Mobile",
    )
    wei_before = ContactAsset(name="Wade Parker", phone_number="5550101034", phone_label="mobile", email="old.wei@example.com")
    wei_after = ContactAsset(
        name="Wade Parker",
        phone_number="5550101035",
        phone_label="Home Fax",
        email="mki@gmail.com",
        email_label="Entertainment",
    )
    assets = (wu_before, wei_before)

    goal = (
        "Open Contacts. Rename Will Bennett to Leo Parker and add email \"jhg@gmail.com\" with the "
        "Mobile label. Then find Wade Parker, update his phone number to 5550101035 with the Home Fax "
        "label, and update his email to \"mki@gmail.com\" with the custom label \"Entertainment\"."
    )

    def criteria(self):
        return [
            AssetModified(self.wu_before, self.wu_after, task=self),
            AssetModified(self.wei_before, self.wei_after, task=self),
        ]
