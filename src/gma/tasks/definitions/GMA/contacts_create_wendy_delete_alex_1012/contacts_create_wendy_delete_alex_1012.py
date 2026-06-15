from __future__ import annotations

from gma.assets import ContactAsset
from gma.evaluation import AssetDeleted, AssetExists
from gma.tasks.base import BaseTask


class ContactsCreateWendyDeleteAlex1012Task(BaseTask):
    apps = {"Contacts"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    delete_target = ContactAsset(name="Alex Parker", phone_number="5550101012")
    keep_target = ContactAsset(name="Alex Parker", phone_number="5550101013")
    expected_contact = ContactAsset(
        name="Wendy Parker",
        phone_number="5550101130",
        phone_label="Callback",
        email="mnb@gmail.com",
        email_label="Mobile",
    )
    assets = (delete_target, keep_target)

    user_interaction = (
        "If the agent asks which Alex Parker to delete, answer exactly: "
        "Delete the one whose phone number ends in 1012. Do not answer unrelated questions."
    )

    goal = (
        "Create a new Contacts entry named Wendy Parker with mobile number 5550101130 labeled "
        "\"Callback\" and email \"mnb@gmail.com\" labeled \"Mobile\". Then delete the "
        "Alex Parker contact whose phone number ends in 1012."
    )

    def criteria(self):
        return [
            AssetExists(self.expected_contact, task=self),
            AssetDeleted(self.delete_target, task=self),
            AssetExists(self.keep_target, task=self),
        ]
