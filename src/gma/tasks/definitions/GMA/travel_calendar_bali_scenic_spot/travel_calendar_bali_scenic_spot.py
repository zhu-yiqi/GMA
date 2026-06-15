from __future__ import annotations

from gma.assets import CalendarEventAsset, TravelAttractionBookingAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask
from datetime import UTC, datetime

from gma.apps.travel import (
    TRAVEL_LOGIN_EMAIL,
    TRAVEL_LOGIN_FIRST_NAME,
    TRAVEL_LOGIN_LAST_NAME,
    TRAVEL_LOGIN_PASSWORD,
    TRAVEL_LOGIN_USERNAME,
    login_travel_app,
)
from gma.assets import TravelUserAsset

TRAVEL_USER = TravelUserAsset(
    email=TRAVEL_LOGIN_EMAIL,
    username=TRAVEL_LOGIN_USERNAME,
    password=TRAVEL_LOGIN_PASSWORD,
    first_name=TRAVEL_LOGIN_FIRST_NAME,
    last_name=TRAVEL_LOGIN_LAST_NAME,
)


def dt_ms(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> int:
    return int(datetime(year, month, day, hour, minute, tzinfo=UTC).timestamp() * 1000)


def open_travel(client) -> None:
    login_travel_app(
        client,
        email=TRAVEL_LOGIN_EMAIL,
        username=TRAVEL_LOGIN_USERNAME,
        password=TRAVEL_LOGIN_PASSWORD,
        ensure_user=False,
    )

class TravelCalendarBaliScenicSpotTask(BaseTask):
    apps = {'Travel', 'Calendar'}
    difficulty = 'hard'
    snapshot = 'gma_ready_state'

    booking = TravelAttractionBookingAsset(user_email=TRAVEL_USER.email, attraction_name='Tegallalang Rice Terraces', attraction_slug='tegallalang-rice-terraces-bali', visit_date_ms=dt_ms(2026,10,15,9), adult_tickets=1, child_tickets=2, visitors=[{'firstName':'Jordan','lastName':'Miller','type':'adult'}, {'firstName':'Mason','lastName':'Taylor','type':'child'}, {'firstName':'Emily','lastName':'Parker','type':'child'}], booking_status='confirmed', payment_status='paid')
    event = CalendarEventAsset(title='Bali Scenic Spot Visit', start_ms=dt_ms(2026,10,15,8), end_ms=dt_ms(2026,10,15,16), timezone='UTC')
    assets = (TRAVEL_USER,)

    goal = 'Open Travel and book one adult ticket and two child tickets for Tegallalang Rice Terraces in Bali on October 15, 2026. Use adult Jordan Miller and children Mason Taylor and Emily Parker. Complete payment so the attraction booking is confirmed. Then create a Calendar event titled "Bali Scenic Spot Visit" on October 15, 2026 from 8:00 AM to 4:00 PM.'

    def setup(self, client) -> None:
        open_travel(client)

    def criteria(self):
        return [AssetExists(self.booking, task=self), AssetExists(self.event, task=self)]
