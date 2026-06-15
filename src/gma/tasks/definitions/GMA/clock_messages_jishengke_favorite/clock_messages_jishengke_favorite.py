from __future__ import annotations

from gma.apps.meituan import MEITUAN_LOGIN_CITY, MEITUAN_LOGIN_USER_ID, MEITUAN_LOGIN_USERNAME
from gma.assets import AlarmAsset, ContactAsset, MeituanCollectionAsset, MeituanUserAsset, SmsMessageAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask

CONTACTS = (
    ContactAsset(name="Ethan Carter", phone_number="+15552250201"),
    ContactAsset(name="Emily Parker", phone_number="+15552250202"),
    ContactAsset(name="Mason Taylor", phone_number="+15552250203"),
    ContactAsset(name="Sophia Reed", phone_number="+15552250204"),
    ContactAsset(name="Olivia Brooks", phone_number="+15552250205"),
)
MESSAGE = "Do you want to eat Jishengke?"
EXPECTED_SMS = tuple(SmsMessageAsset(address=contact.phone_number, body=MESSAGE, box="sent", read=True) for contact in CONTACTS)


class ClockMessagesJishengkeFavoriteTask(BaseTask):
    apps = {"Clock", "Messages", "Meituan"}
    difficulty = "hard"
    snapshot = "gma_ready_state"
    assets = (
        *CONTACTS,
        MeituanUserAsset(username=MEITUAN_LOGIN_USERNAME, password="123456", user_id=MEITUAN_LOGIN_USER_ID, city=MEITUAN_LOGIN_CITY, status=1),
    )
    user_interaction = "If the agent cannot find an alarm labeled Entertainment, answer exactly: Create that alarm instead. Do not answer unrelated questions."
    goal = (
        "Open Clock. If no alarm labeled Entertainment exists, create an alarm at 3:00 AM labeled Stand-up Comedy. "
        "Then open Messages and send this exact message to Ethan Carter, Emily Parker, Mason Taylor, Sophia Reed, and Olivia Brooks: \"Do you want to eat Jishengke?\" "
        "Finally open Meituan, search for Jishengke, and bookmark the restaurant."
    )

    def criteria(self):
        return [
            AssetExists(AlarmAsset(hour=3, minute=0, label="Stand-up Comedy", enabled=True), task=self),
            *(AssetExists(message, task=self) for message in EXPECTED_SMS),
            AssetExists(MeituanCollectionAsset(user_id=MEITUAN_LOGIN_USER_ID, restaurant_name="Jishengke"), task=self),
        ]
