from __future__ import annotations

from gma.assets import ContactAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


class ContactsCreateGaryBennettTwoEntriesTask(BaseTask):
    apps = {"Contacts"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    primary_contact = ContactAsset(
        name="Gary Bennett",
        phone_number="5550101010",
        phone_label="other",
        email="dce@gmail.com",
        email_label="home",
    )
    secondary_contact = ContactAsset(
        name="Gary Bennett",
        phone_number="5550101011",
        phone_label="Company Main",
        email="sxd@gmail.com",
        email_label="work",
    )

    goal = (
        "Open Contacts and create two supported entries named Gary Bennett. In the first entry, set phone "
        "5550101010 with the Other label and email \"dce@gmail.com\" with the Home label. In the "
        "second entry, set phone 5550101011 with the custom label \"Company Main\" and email "
        "\"sxd@gmail.com\" with the Work label."
    )

    def criteria(self):
        return [
            AssetExists(self.primary_contact, task=self),
            AssetExists(self.secondary_contact, task=self),
        ]
