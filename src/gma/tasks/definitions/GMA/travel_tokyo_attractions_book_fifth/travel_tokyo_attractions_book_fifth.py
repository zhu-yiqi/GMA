from __future__ import annotations

from gma.assets import TravelAttractionBookingAsset, TravelFavoriteAsset
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

FAVORITES = [
    ('Senso-ji Temple','senso-ji-temple-tokyo'),
    ('Tokyo Skytree','tokyo-skytree-tokyo'),
    ('Meiji Shrine','meiji-shrine-tokyo'),
    ('Tsukiji Outer Market','tsukiji-outer-market-tokyo'),
    ('Akihabara Electric Town','akihabara-electric-town-tokyo'),
]

class TravelTokyoAttractionsBookFifthTask(BaseTask):
    apps = {'Travel'}
    difficulty = 'hard'
    snapshot = 'gma_ready_state'
    booking = TravelAttractionBookingAsset(user_email=TRAVEL_USER.email, attraction_name='Akihabara Electric Town', attraction_slug='akihabara-electric-town-tokyo', visit_date_ms=dt_ms(2026,10,10,9), adult_tickets=1, child_tickets=1, visitors=[{'firstName':'Morgan','lastName':'Stone','type':'adult'}, {'firstName':'Emily','lastName':'Parker','type':'child'}], booking_status='confirmed', payment_status='paid')
    assets = (TRAVEL_USER,)

    goal = 'Open Travel, save Senso-ji Temple, Tokyo Skytree, Meiji Shrine, Tsukiji Outer Market, and Akihabara Electric Town from Tokyo attractions, then book Akihabara Electric Town for October 10, 2026 for one adult Morgan Stone and one child Emily Parker. Complete payment so the attraction booking is confirmed.'

    def setup(self, client) -> None:
        open_travel(client)

    def criteria(self):
        return [AssetExists(TravelFavoriteAsset(user_email=TRAVEL_USER.email, target='attraction', attraction_name=name, attraction_slug=slug), task=self) for name, slug in FAVORITES] + [AssetExists(self.booking, task=self)]
