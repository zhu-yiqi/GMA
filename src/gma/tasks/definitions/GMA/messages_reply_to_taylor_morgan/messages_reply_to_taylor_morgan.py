from __future__ import annotations

from gma.assets import ContactAsset, SmsMessageAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


class MessagesReplyToTaylorMorganTask(BaseTask):
    apps = {"Messages"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    contact = ContactAsset(
        name="Taylor Morgan",
        phone_number="+15552011616",
    )
    seed_message = SmsMessageAsset(
        address=contact.phone_number,
        body="Please confirm you saw the revised delivery note.",
        box="inbox",
        read=True,
        timestamp_ms=202610010935,
    )
    expected_reply = SmsMessageAsset(
        address=contact.phone_number,
        body="I know.",
        box="sent",
        read=True,
    )
    assets = (contact, seed_message)

    goal = "Open Messages and send Taylor Morgan exactly \"I know.\""

    def criteria(self):
        return [AssetExists(self.expected_reply, task=self)]
