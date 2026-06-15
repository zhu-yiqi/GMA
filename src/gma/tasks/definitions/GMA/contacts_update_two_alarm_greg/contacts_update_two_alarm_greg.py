from __future__ import annotations

from gma.assets import AlarmAsset, ContactAsset
from gma.evaluation import AssetExists, AssetModified
from gma.tasks.base import BaseTask

MASON_BEFORE = ContactAsset(name="Mason Taylor", phone_number="+15552200220", phone_label="Mobile")
GREG_AFTER = ContactAsset(name="Greg Green", phone_number="+15552200220", phone_label="Work Fax", website="www.music.example.com")
LOGAN_BEFORE = ContactAsset(name="Logan Brooks", phone_number="+15552200221", phone_label="Mobile")
LOGAN_AFTER = ContactAsset(name="Logan Brooks", phone_number="5550101026", phone_label="Family", website="www.musicfans.example.com")
ALARM = AlarmAsset(hour=21, minute=0, label="Contact Greg Green", enabled=True, days_of_week=(), vibrate=True)


class ContactsUpdateTwoAlarmGregTask(BaseTask):
    apps = {"Contacts", "Clock"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    category = ["Information-Gathering Tasks"]
    assets = (MASON_BEFORE, LOGAN_BEFORE)
    user_interaction = "If the agent asks what time to set the alarm, answer exactly: 9:00 PM. Do not answer unrelated questions."
    goal = (
        "Open Contacts. Rename Mason Taylor to Greg Green, set the phone label to Work Fax, and add website www.music.example.com. "
        "For Logan Brooks, change the phone number to 5550101026, set the phone label to Family, and add website www.musicfans.example.com. "
        "Then open Clock and create an alarm labeled Contact Greg Green with no repeat and vibration on."
    )

    def criteria(self):
        return [
            AssetModified(MASON_BEFORE, GREG_AFTER, task=self),
            AssetModified(LOGAN_BEFORE, LOGAN_AFTER, task=self),
            AssetExists(ALARM, task=self),
        ]
