from __future__ import annotations

from gma.assets import AlarmAsset, ElementXMessageAsset, ElementXRoomAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


MEETING_ALARM = AlarmAsset(
    hour=10,
    minute=0,
    label="Morning Meeting",
    enabled=True,
    days_of_week=("monday", "tuesday", "wednesday", "thursday"),
    vibrate=False,
)
WORK_GROUP_ALIAS = "work_group"
NOTICE = "From October 7 to December 15, morning meetings will be held at 10:00 AM every day. Please attend on time."


class ClockElementXMorningMeetingNoticeTask(BaseTask):
    apps = {"Clock", "ElementX"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (
        ElementXRoomAsset(
            name="Work Group",
            room_type="group",
            creator_username="testuser",
            creator_password="testpass123",
            alias_localpart=WORK_GROUP_ALIAS,
            topic="Work coordination group for meeting notices.",
        ),
    )
    goal = (
        "Create a Clock alarm labeled Morning Meeting for 10:00 AM, repeating Monday through "
        "Thursday, with vibration off. Then open ElementX, find the Work Group room, and send "
        "exactly this message: \"From October 7 to December 15, morning meetings will be held at "
        "10:00 AM every day. Please attend on time.\""
    )

    def criteria(self):
        return [
            AssetExists(MEETING_ALARM, task=self),
            AssetExists(
                ElementXMessageAsset(
                    room=WORK_GROUP_ALIAS,
                    sender_username="testuser",
                    sender_password="testpass123",
                    text=NOTICE,
                ),
                task=self,
            ),
        ]
