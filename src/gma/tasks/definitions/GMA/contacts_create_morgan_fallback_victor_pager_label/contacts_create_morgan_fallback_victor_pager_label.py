from __future__ import annotations

from gma.assets import ContactAsset
from gma.evaluation import AssetExists, AssetModified
from gma.tasks.base import BaseTask


class ContactsCreateMorganFallbackVictorPagerLabelTask(BaseTask):
    apps = {"Contacts"}
    difficulty = "medium"
    category = ['Invalid-Instruction Tasks']
    snapshot = "gma_ready_state"

    reliable_before = ContactAsset(name="Tyler Reed", phone_number="5550101014", phone_label="mobile")
    reliable_after = ContactAsset(name="Tyler Reed", phone_number="5550101014", phone_label="pager")
    expected_wu = ContactAsset(
        name="Morgan Blake",
        phone_number="5550101015",
        phone_label="car",
        website="www.ccc.com",
    )
    assets = (reliable_before,)

    user_interaction = (
        "If the agent says Victor Hayes cannot be found, answer exactly: "
        "Use Tyler Reed instead. Do not answer unrelated questions."
    )

    goal = (
        "Create a new Contacts entry named Morgan Blake with phone number 5550101015 labeled "
        "\"car\" and website \"www.ccc.com\". Then find Victor Hayes and change that contact's "
        "phone label to the custom label \"pager\"."
    )

    def criteria(self):
        return [
            AssetExists(self.expected_wu, task=self),
            AssetModified(self.reliable_before, self.reliable_after, task=self),
        ]
