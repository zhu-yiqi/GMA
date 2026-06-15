from __future__ import annotations

from gma.apps.elementx import elementx_user_id
from gma.assets import ContactAsset, ElementXMessageAsset, ElementXRoomAsset, ElementXUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


CONTACT_USERNAME = "xia_tao_w1"
CONTACT_DISPLAY = "Tara Hill"
PHONE_NUMBER = "5550101038"
ROOM_REF = elementx_user_id(CONTACT_USERNAME)


class ElementXCopyTaraHillPhoneToContactTask(BaseTask):
    apps = {"ElementX", "Contacts"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    assets = (
        ElementXUserAsset(username=CONTACT_USERNAME, password="password", display_name=CONTACT_DISPLAY),
        ElementXRoomAsset(
            name=CONTACT_DISPLAY,
            room_type="dm",
            creator_username="testuser",
            creator_password="testpass123",
            members=[CONTACT_USERNAME],
        ),
        ElementXMessageAsset(
            room=ROOM_REF,
            sender_username=CONTACT_USERNAME,
            sender_password="password",
            text=PHONE_NUMBER,
            created_at_ms=202610011230,
        ),
    )
    expected_contact = ContactAsset(
        name=CONTACT_DISPLAY,
        phone_number=PHONE_NUMBER,
        phone_label="work",
        email="krtfdaa@gmail.com",
        email_label="Interviewee",
    )

    goal = (
        "Open ElementX, locate the private chat with Tara Hill, and copy the phone number from the "
        "latest chat message. Then create a Contacts entry named Tara Hill with that copied phone "
        "number labeled Work and email \"krtfdaa@gmail.com\" labeled \"Interviewee\"."
    )

    def criteria(self):
        return [AssetExists(self.expected_contact, task=self)]
