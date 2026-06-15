
from __future__ import annotations

from gma.assets import ElementXMessageAsset, ElementXRoomAsset, ElementXUserAsset, MailAccountAsset, MailMessageAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


ROOM_ALIAS = "w2-row122-gathering"
ROOM_NAME = "Gathering"
DINNER_ADDRESS = "88 Garden Lane, North Campus"


class ElementXCreateGatheringForwardDinnerAddressTask(BaseTask):
    apps = {"ElementX", "Mail"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    account = MailAccountAsset(display_name="Jordan Reed", email="jordan.reed@example.com")
    dinner_mail = MailMessageAsset(mailbox="inbox", from_name="Dinner Host", from_email="host@example.com", to=[account.email], subject="Dinner address for tonight", body=f"Dinner starts soon. Address: {DINNER_ADDRESS}.", timestamp_ms=202610010000, read=False)
    friend = ElementXUserAsset(username="blake_turner", password="password", display_name="Blake Turner")
    expected_room = ElementXRoomAsset(name=ROOM_NAME, room_type="group", creator_username="testuser", creator_password="testpass123", members=["blake_turner"], alias_localpart=ROOM_ALIAS, topic="Cosplay Party")
    expected_question = ElementXMessageAsset(room=ROOM_NAME, sender_username="testuser", sender_password="testpass123", text="What are we eating today?")
    expected_address = ElementXMessageAsset(room=ROOM_NAME, sender_username="testuser", sender_password="testpass123", text=f"Dinner address: {DINNER_ADDRESS}.")
    assets = (account, dinner_mail, friend)

    goal = (
        'Open ElementX and create a new group chat room named "Gathering" with topic "Cosplay Party". '
        'Invite Blake Turner. Send exactly "What are we eating today?" in the room. '
        "Then open Mail, find today's dinner-related email, and forward the address from it to the Gathering room. "
        'Use exactly this format: "Dinner address: <address>."'
    )

    def criteria(self):
        return [AssetExists(self.expected_room, task=self), AssetExists(self.expected_question, task=self), AssetExists(self.expected_address, task=self)]
