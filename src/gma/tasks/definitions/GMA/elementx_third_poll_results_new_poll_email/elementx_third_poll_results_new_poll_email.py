
from __future__ import annotations

from gma.assets import ElementXMessageAsset, ElementXPollAsset, ElementXPollResponse, ElementXRoomAsset, ElementXSessionAsset, ElementXUserAsset, MailAccountAsset, MailMessageAsset
from gma.evaluation import Any, AssetExists
from gma.tasks.base import BaseTask


THIRD_ALIAS = "w2-row125-third-group"
RESULTS_TEXT = "Pizza: 2, Salad: 1"


class ElementXThirdPollResultsNewPollEmailTask(BaseTask):
    apps = {"ElementX", "Mail"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    users = (
        ElementXUserAsset(username="w2-row125-alex", password="password", display_name="Alex"),
        ElementXUserAsset(username="w2-row125-blair", password="password", display_name="Blair"),
        ElementXUserAsset(username="w2-row125-casey", password="password", display_name="Casey"),
    )
    first_room = ElementXRoomAsset(name="First Group", room_type="group", creator_username="testuser", creator_password="testpass123", members=["w2-row125-alex"], alias_localpart="w2-row125-first-group")
    second_room = ElementXRoomAsset(name="Second Group", room_type="group", creator_username="testuser", creator_password="testpass123", members=["w2-row125-blair"], alias_localpart="w2-row125-second-group")
    third_room = ElementXRoomAsset(name="Third Group", room_type="group", creator_username="testuser", creator_password="testpass123", members=["w2-row125-alex", "w2-row125-blair", "w2-row125-casey"], alias_localpart=THIRD_ALIAS)
    previous_poll = ElementXPollAsset(room=THIRD_ALIAS, sender_username="w2-row125-alex", sender_password="password", question="What should we eat today?", options=["Pizza", "Salad"], responses=[ElementXPollResponse(username="w2-row125-alex", option="Pizza"), ElementXPollResponse(username="w2-row125-blair", option="Pizza"), ElementXPollResponse(username="w2-row125-casey", option="Salad")], created_at_ms=202610011000)
    mail_account = MailAccountAsset(display_name="Morgan Ellis", email="morgan.ellis@example.com")
    expected_notice = ElementXMessageAsset(room=THIRD_ALIAS, sender_username="testuser", sender_password="testpass123", text="Remember to arrive on time tomorrow", mentions_room=True)
    expected_notice_with_room_text = ElementXMessageAsset(room=THIRD_ALIAS, sender_username="testuser", sender_password="testpass123", text="Remember to arrive on time tomorrow @room.", mentions_room=True)
    expected_poll = ElementXPollAsset(room=THIRD_ALIAS, sender_username="testuser", sender_password="testpass123", question="What shall we drink tomorrow?", options=["Milk", "Juice"])
    expected_mail = MailMessageAsset(mailbox="sent", from_name=mail_account.display_name, from_email="test@gmail.com", to=["1234@gmail.com"], subject="Last Poll Results", body=RESULTS_TEXT, read=True)
    assets = (*users, first_room, second_room, third_room, previous_poll, mail_account, ElementXSessionAsset(username="testuser", password="testpass123"))

    goal = (
        'Open ElementX, check the results of the last poll in the third group chat room, then send exactly "Remember to arrive on time tomorrow" and mention @everyone. '
        'Create a new poll titled exactly "What shall we drink tomorrow?" with options exactly "Milk" and "Juice". '
        'Then send an email to 1234@gmail.com with subject "Last Poll Results" and a body that reports the poll counts in exactly this format: "Pizza: <count>, Salad: <count>".'
    )

    def criteria(self):
        return [
            Any(
                AssetExists(self.expected_notice, task=self),
                AssetExists(self.expected_notice_with_room_text, task=self),
            ),
            AssetExists(self.expected_poll, task=self),
            AssetExists(self.expected_mail, task=self),
        ]
