from __future__ import annotations

from gma.assets import ContactAsset, SmsMessageAsset
from gma.evaluation import AssetExists, AssetModified
from gma.tasks.base import BaseTask

BEFORE_CONTACT = ContactAsset(name="Alex Chen", phone_number="5550101098", phone_label="mobile")
AFTER_CONTACT = ContactAsset(name="Alex Chen Work Phone", phone_number="5550101099", phone_label="mobile", email="123456@gmail.com", website="https://www.nps.gov/mora/")
UNREAD_MESSAGE = SmsMessageAsset(address="+15550149001", body="Please use this work phone number for the contact update: 5550101099.", box="inbox", read=False, timestamp_ms=202610010910)
OLDER_UNREAD = SmsMessageAsset(address="+15550149002", body="Older unread note without the target phone number.", box="inbox", read=False, timestamp_ms=202610010900)
EXPECTED_MESSAGE = SmsMessageAsset(address=AFTER_CONTACT.phone_number, body="I updated your work phone number.", box="sent", read=True)


class MessagesContactsUpdateFromUnreadPhoneTask(BaseTask):
    apps = {"Messages", "Contacts"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (BEFORE_CONTACT, UNREAD_MESSAGE, OLDER_UNREAD)
    goal = (
        "Open Messages, read the latest unread text, and copy the phone number from it. "
        "Then open Contacts, find Alex Chen, rename the contact to \"Alex Chen Work Phone\", "
        "replace the phone number with the copied number, add the email \"123456@gmail.com\", "
        "and add the website \"https://www.nps.gov/mora/\". After saving the contact, send Alex Chen Work Phone "
        "this exact text message: \"I updated your work phone number.\""
    )

    def criteria(self):
        return [AssetModified(BEFORE_CONTACT, AFTER_CONTACT, task=self), AssetExists(EXPECTED_MESSAGE, task=self)]
