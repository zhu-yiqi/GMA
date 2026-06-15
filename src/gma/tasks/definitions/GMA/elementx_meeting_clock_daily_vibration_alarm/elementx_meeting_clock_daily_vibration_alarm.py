
from __future__ import annotations

from gma.assets import AlarmAsset, ElementXMessageAsset, ElementXRoomAsset, ElementXSessionAsset, ElementXUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


ROOM_ALIAS = "w2-row131-clock-alert"
MEETING_MESSAGE = "Project sync meeting starts at 3:30 PM today."


class ElementXMeetingClockDailyVibrationAlarmTask(BaseTask):
    apps = {"ElementX", "Clock"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    sender = ElementXUserAsset(username="w2-row131-scheduler", password="password", display_name="Morgan Scheduler")
    room = ElementXRoomAsset(name="Clock alert", room_type="group", creator_username="testuser", creator_password="testpass123", members=["w2-row131-scheduler"], alias_localpart=ROOM_ALIAS, topic="Clock alerts")
    latest_message = ElementXMessageAsset(room=ROOM_ALIAS, sender_username="w2-row131-scheduler", sender_password="password", text=MEETING_MESSAGE, created_at_ms=202610011000)
    expected_alarm = AlarmAsset(hour=15, minute=0, label="ElementX Meeting Alarm", enabled=True, days_of_week=("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"), vibrate=True)
    assets = (sender, room, latest_message, ElementXSessionAsset(username="testuser", password="testpass123"))

    goal = (
        "Open ElementX, go to the room \"Clock alert\", and read the latest meeting schedule message. "
        "Then open Clock and create an alarm for 30 minutes before that meeting. Name the alarm exactly \"ElementX Meeting Alarm\", set it to repeat daily, and set the alert method to vibration."
    )

    def criteria(self):
        return [AssetExists(self.expected_alarm, task=self)]
