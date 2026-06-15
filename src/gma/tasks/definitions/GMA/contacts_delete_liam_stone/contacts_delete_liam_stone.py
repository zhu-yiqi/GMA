from __future__ import annotations

from gma.assets import ContactAsset
from gma.evaluation import AssetDeleted
from gma.tasks.base import BaseTask


LIAM_STONE = ContactAsset(
    name="Liam Stone",
    phone_number="+15550190010",
)


class ContactsDeleteLiamStoneTask(BaseTask):
    apps = {"Contacts"}
    difficulty = "easy"
    snapshot = "gma_ready_state"
    assets = (LIAM_STONE,)
    goal = "Delete the contact named 'Liam Stone'."

    def criteria(self):
        return [AssetDeleted(LIAM_STONE, task=self)]
