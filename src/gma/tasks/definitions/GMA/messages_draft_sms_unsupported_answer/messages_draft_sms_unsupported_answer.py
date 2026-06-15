from __future__ import annotations

from gma.assets import SmsMessageAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


PHONE = "5550101024"
BODY = "I'll send the details later."


class MessagesDraftSmsUnsupportedAnswerTask(BaseTask):
    apps = {"Messages"}
    difficulty = "hard"
    snapshot = "gma_ready_state"
    user_interaction = (
        "If the agent reports that scheduled or draft SMS messages are not supported and asks what to do, answer exactly: "
        "Send it immediately instead. Do not answer unrelated questions."
    )
    assets = ()
    goal = f'Open Messages and schedule an SMS to {PHONE} for 6:00 PM saying "{BODY}"'

    def criteria(self):
        return [AssetExists(SmsMessageAsset(address=PHONE, body=BODY, box="sent", read=True), task=self)]
