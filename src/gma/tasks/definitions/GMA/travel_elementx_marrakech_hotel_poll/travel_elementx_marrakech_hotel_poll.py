from __future__ import annotations

from gma.assets import ElementXMessageAsset, ElementXPollAsset, ElementXRoomAsset, ElementXUserAsset, TravelFavoriteAsset
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

ROOM_ALIAS = 'lets-go-now-row267'
MESSAGE = 'I checked the hotels in Marrakech, and two of them look quite good-please vote'
FAVORITES = [
    ('Medina Riad Hotel','medina-riad-hotel-boutique-lat31-6586-lon-7-9835'),
    ('Jemaa el-Fnaa Suites','jemaa-el-fnaa-suites-luxury-lat31-6464-lon-8-0109'),
    ('Majorelle Garden Inn','majorelle-garden-inn-resort-lat31-6064-lon-7-959'),
    ('Atlas Mountain View Hotel','atlas-mountain-view-hotel-budget-lat31-6503-lon-7-9591'),
    ('Kasbah Heritage Lodge','kasbah-heritage-lodge-business-lat31-6474-lon-8-0038'),
]

class TravelElementXMarrakechHotelPollTask(BaseTask):
    apps = {'Travel', 'ElementX'}
    difficulty = 'hard'
    snapshot = 'gma_ready_state'
    member = ElementXUserAsset(username='w5-row267-travel-member', password='password', display_name='Marrakech Travel Member')
    room = ElementXRoomAsset(name="Let's Go Now", room_type='group', creator_username='testuser', creator_password='testpass123', members=['w5-row267-travel-member'], alias_localpart=ROOM_ALIAS, topic='Marrakech hotels')
    assets = (TRAVEL_USER, member, room)

    goal = f'Open Travel, favorite Medina Riad Hotel, Jemaa el-Fnaa Suites, Majorelle Garden Inn, Atlas Mountain View Hotel, and Kasbah Heritage Lodge in Marrakech. Then open ElementX, send exactly "{MESSAGE}" in Let\'s Go Now, and create a poll titled "Hotel Selection" with options Majorelle Garden Inn and Kasbah Heritage Lodge.'

    def setup(self, client) -> None:
        open_travel(client)

    def criteria(self):
        criteria = [AssetExists(TravelFavoriteAsset(user_email=TRAVEL_USER.email, target='hotel', hotel_name=name, hotel_slug=slug), task=self) for name, slug in FAVORITES]
        criteria.append(AssetExists(ElementXMessageAsset(room=ROOM_ALIAS, sender_username='testuser', sender_password='testpass123', text=MESSAGE), task=self))
        criteria.append(AssetExists(ElementXPollAsset(room=ROOM_ALIAS, sender_username='testuser', sender_password='testpass123', question='Hotel Selection', options=['Majorelle Garden Inn', 'Kasbah Heritage Lodge']), task=self))
        return criteria
