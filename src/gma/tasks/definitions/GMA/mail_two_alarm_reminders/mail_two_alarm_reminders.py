from __future__ import annotations

from gma.assets import AlarmAsset, MailAccountAsset, MailMessageAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask

ACCOUNT = MailAccountAsset(display_name="Mason Lee", email="mason.lee@example.com")
EXPECTED_MAIL = MailMessageAsset(mailbox="sent", from_name=ACCOUNT.display_name, from_email="test@gmail.com", to=["dag@gmail.com"], subject="Watching the game", body="You're responsible for buying the tickets.", read=True)
NIGHT_ALARM = AlarmAsset(hour=20, minute=0, label="Email amx@gmail.com Dinner together tonight", enabled=True, days_of_week=(), vibrate=True)
AFTERNOON_ALARM = AlarmAsset(hour=14, minute=0, label="Email cft@gmail.com Event schedule", enabled=True, days_of_week=(), vibrate=True)


class MailTwoAlarmRemindersTask(BaseTask):
    apps = {"Mail", "Clock"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (ACCOUNT,)
    user_interaction = "If the agent asks what time the evening alarm should be, answer exactly: 8:00 PM. Do not answer unrelated questions."
    goal = (
        "Open Mail and send an email to dag@gmail.com with subject \"Watching the game\" and body \"You're responsible for buying the tickets.\" "
        "Then open Clock and create a vibrating evening alarm labeled \"Email amx@gmail.com Dinner together tonight\". "
        "Also create a vibrating 2:00 PM alarm labeled \"Email cft@gmail.com Event schedule\"."
    )

    def criteria(self):
        return [AssetExists(EXPECTED_MAIL, task=self), AssetExists(NIGHT_ALARM, task=self), AssetExists(AFTERNOON_ALARM, task=self)]
