from __future__ import annotations

from gma.assets import ContactAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


AVERY_WALKER = ContactAsset(
    name="Avery Walker",
    phone_number="5550101009",
    phone_label="work",
)


class ContactsCreateAveryWalkerTask(BaseTask):
    apps = {"Contacts"}
    difficulty = "easy"
    snapshot = "gma_ready_state"
    assets = ()
    goal = "Create a contact named 'Avery Walker' with phone number 5550101009 and set the phone label to Work."

    def criteria(self):
        return [AssetExists(AVERY_WALKER, task=self)]
