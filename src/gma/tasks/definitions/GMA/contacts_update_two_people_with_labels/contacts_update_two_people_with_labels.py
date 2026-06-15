from __future__ import annotations

from gma.assets import ContactAsset
from gma.evaluation import AssetModified
from gma.tasks.base import BaseTask


class ContactsUpdateTwoPeopleWithLabelsTask(BaseTask):
    apps = {"Contacts"}
    difficulty = "medium"
    category = ['Information-Gathering Tasks']
    snapshot = "gma_ready_state"

    first_before = ContactAsset(
        name="Noah Parker",
        phone_number="+15552017601",
        phone_label="mobile",
    )
    first_after = ContactAsset(
        name="Liam Parker",
        phone_number="+15552017601",
        phone_label="Work Fax",
        website="www.aaa.com",
    )
    second_before = ContactAsset(
        name="Morgan Lane",
        phone_number="+15552017602",
        phone_label="mobile",
    )
    second_after = ContactAsset(
        name="Morgan Lane",
        phone_number="5550101027",
        phone_label="home",
        website="www.ccc.com",
    )
    assets = (first_before, second_before)

    user_interaction = (
        "You are the user who asked for two Contacts edits. If the agent asks "
        "which phone label to use for Morgan Lane, answer: Use the Home label."
    )

    goal = (
        "Open Contacts. For Noah Parker, rename the contact to Liam Parker, "
        "set the phone label to the Work Fax label, and add the website "
        "\"www.aaa.com\". For Morgan Lane, change the phone number to "
        "5550101027, set the phone label, and add the website \"www.ccc.com\"."
    )

    def criteria(self):
        return [
            AssetModified(self.first_before, self.first_after, task=self),
            AssetModified(self.second_before, self.second_after, task=self),
        ]
