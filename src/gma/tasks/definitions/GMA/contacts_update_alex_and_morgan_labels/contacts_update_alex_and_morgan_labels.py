from __future__ import annotations

from gma.assets import ContactAsset
from gma.evaluation import AssetModified
from gma.tasks.base import BaseTask


class ContactsUpdateAlexAndMorganLabelsTask(BaseTask):
    apps = {"Contacts"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    first_before = ContactAsset(name="Alex Parker", phone_number="5550101036", phone_label="mobile")
    first_after = ContactAsset(
        name="Alex Reed",
        phone_number="5550101036",
        phone_label="Work Fax",
        website="www.aaa.com",
    )
    second_before = ContactAsset(name="Morgan Blake", phone_number="5550101037", phone_label="mobile")
    second_after = ContactAsset(
        name="Morgan Blake",
        phone_number="5550101027",
        phone_label="home",
        website="www.ccc.com",
    )
    assets = (first_before, second_before)

    user_interaction = (
        "If the agent asks which phone label to use for Morgan Blake, answer exactly: "
        "Use the Home label. Do not answer unrelated questions."
    )

    goal = (
        "Open Contacts. Rename Alex Parker to Alex Reed, set Alex Reed's phone label to the custom label "
        "\"Work Fax\", and add the website \"www.aaa.com\". For Morgan Blake, change the phone "
        "number to 5550101027, set the phone label, and add the website \"www.ccc.com\"."
    )

    def criteria(self):
        return [
            AssetModified(self.first_before, self.first_after, task=self),
            AssetModified(self.second_before, self.second_after, task=self),
        ]
