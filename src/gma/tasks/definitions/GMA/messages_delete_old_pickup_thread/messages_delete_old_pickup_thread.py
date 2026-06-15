from __future__ import annotations

from gma.assets import SmsMessageAsset
from gma.evaluation import AssetDeleted
from gma.tasks.base import BaseTask


class MessagesDeleteOldPickupThreadTask(BaseTask):
    apps = {"Messages"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    target_message = SmsMessageAsset(
        address="+15552011414",
        body="Please remove this old pickup reminder.",
        box="inbox",
        read=True,
        timestamp_ms=202610010910,
    )
    assets = (target_message,)

    goal = (
        "Open Messages and delete the conversation from +1 555-201-1414 "
        "that contains the old pickup reminder."
    )

    def criteria(self):
        return [AssetDeleted(self.target_message, task=self)]
