from __future__ import annotations

from gma.assets import ContactAsset, SmsMessageAsset
from gma.evaluation import AssetExists, AssetModified
from gma.tasks.base import BaseTask

TARGET_BEFORE = ContactAsset(name="Ryan Walker", phone_number="+15550101486", phone_label="Mobile")
TARGET_AFTER = ContactAsset(name="Emily Parker", phone_number="+15550101486", phone_label="Mobile", label="Friend")
DISTRACTOR = ContactAsset(name="Ryan Walker", phone_number="+15550102000", phone_label="Mobile")
EXPECTED_SMS = SmsMessageAsset(address=TARGET_AFTER.phone_number, body="What shall we eat after work today?", box="sent", read=True)


class ContactsRenameRyan1486MessageTask(BaseTask):
    apps = {"Contacts", "Messages"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (TARGET_BEFORE, DISTRACTOR)
    goal = (
        "Open Contacts and find the Ryan Walker contact whose phone number ends in 1486. Rename that contact to Emily Parker, "
        "set the contact label to Friend, and send that contact this exact message: \"What shall we eat after work today?\""
    )

    def criteria(self):
        return [AssetModified(TARGET_BEFORE, TARGET_AFTER, task=self), AssetExists(EXPECTED_SMS, task=self)]
