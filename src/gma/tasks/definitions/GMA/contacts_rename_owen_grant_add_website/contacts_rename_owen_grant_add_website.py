from __future__ import annotations

from gma.assets import ContactAsset
from gma.evaluation import AssetModified
from gma.tasks.base import BaseTask


class ContactsRenameOwenGrantAddWebsiteTask(BaseTask):
    apps = {"Contacts"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    before_contact = ContactAsset(
        name="Owen Grant",
        phone_number="+15552011313",
    )
    after_contact = ContactAsset(
        name="Noah Grant",
        phone_number="+15552011313",
        website="www.aaa.com",
    )
    assets = (before_contact,)

    goal = (
        "Open Contacts, find Owen Grant, rename the contact to Noah Grant, "
        "and add the website \"www.aaa.com\"."
    )

    def criteria(self):
        return [AssetModified(self.before_contact, self.after_contact, task=self)]
