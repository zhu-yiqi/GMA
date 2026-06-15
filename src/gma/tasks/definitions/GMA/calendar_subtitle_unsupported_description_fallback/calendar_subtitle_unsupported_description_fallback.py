from __future__ import annotations

from datetime import UTC, datetime

from gma.assets import CalendarEventAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


def dt_ms(year: int, month: int, day: int, hour: int, minute: int = 0) -> int:
    return int(datetime(year, month, day, hour, minute, tzinfo=UTC).timestamp() * 1000)


class CalendarSubtitleUnsupportedDescriptionFallbackTask(BaseTask):
    apps = {"Calendar"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    user_interaction = (
        "If the agent reports that Calendar event subtitles are not supported and asks what to do, answer exactly: "
        "Write \"Bring acoustic guitar\" in the event description instead. Do not answer unrelated questions."
    )
    assets = ()
    goal = (
        'Open Calendar and create an event titled "Daily Music Practice" on October 2, 2026 '
        'from 9:00 AM to 10:00 AM with subtitle "Bring acoustic guitar".'
    )
    expected_event = CalendarEventAsset(
        title="Daily Music Practice",
        start_ms=dt_ms(2026, 10, 2, 9),
        end_ms=dt_ms(2026, 10, 2, 10),
        description="Bring acoustic guitar",
        timezone="UTC",
    )

    def criteria(self):
        return [AssetExists(self.expected_event, task=self)]
