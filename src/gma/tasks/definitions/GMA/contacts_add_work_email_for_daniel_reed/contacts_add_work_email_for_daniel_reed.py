from __future__ import annotations

from gma.assets import ContactAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


class ContactsAddWorkEmailForDanielReedTask(BaseTask):
    apps = {"Contacts"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    seeded_contact = ContactAsset(
        name="Daniel Reed",
        phone_number="+15552011212",
    )
    expected_contact = ContactAsset(
        name="Daniel Reed",
        phone_number="+15552011212",
        email="mnb@gmail.com",
        email_label="work",
    )
    assets = (seeded_contact,)

    goal = (
        "Open Contacts, find Daniel Reed, and add the email address "
        "\"mnb@gmail.com\" with the Work label."
    )

    def criteria(self):
        return [AssetExists(self.expected_contact, task=self)]
