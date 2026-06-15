from __future__ import annotations

from gma.assets import ElementXMessageAsset, ElementXRoomAsset, ElementXUserAsset, TravelAttractionBookingAsset, TravelFavoriteAsset
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

ROOM_ALIAS = 'happy-home-row280'
MESSAGE = 'Tickets for attractions have been booked: Meiji Shrine'

class TravelElementXPopularDestinationTicketsTask(BaseTask):
    apps = {'Travel', 'ElementX'}
    difficulty = 'hard'
    snapshot = 'gma_ready_state'

    favorite = TravelFavoriteAsset(user_email=TRAVEL_USER.email, target='attraction', attraction_name='Senso-ji Temple', attraction_slug='senso-ji-temple-tokyo')
    booking = TravelAttractionBookingAsset(user_email=TRAVEL_USER.email, attraction_name='Meiji Shrine', attraction_slug='meiji-shrine-tokyo', visit_date_ms=dt_ms(2026,10,30,9), adult_tickets=2, child_tickets=1, visitors=[{'firstName':'Jordan','lastName':'Miller','type':'adult'}, {'firstName':'Olivia','lastName':'Grant','type':'adult'}, {'firstName':'Daisy','lastName':'Miller','type':'child'}], booking_status='confirmed', payment_status='paid')
    member = ElementXUserAsset(username='w5-row280-family-member', password='password', display_name='Happy Home Member')
    room = ElementXRoomAsset(name='Happy Home', room_type='group', creator_username='testuser', creator_password='testpass123', members=['w5-row280-family-member'], alias_localpart=ROOM_ALIAS, topic='Family travel')
    assets = (TRAVEL_USER, member, room)

    goal = f'Open Travel, use Tokyo as the first popular destination, save the free attraction Senso-ji Temple, then book Meiji Shrine for October 30, 2026 for adults Jordan Miller and Olivia Grant and child Daisy Miller. Complete payment so the attraction booking is confirmed. Open ElementX and send Happy Home exactly "{MESSAGE}".'

    def setup(self, client) -> None:
        open_travel(client)

    def criteria(self):
        return [AssetExists(self.favorite, task=self), AssetExists(self.booking, task=self), AssetExists(ElementXMessageAsset(room=ROOM_ALIAS, sender_username='testuser', sender_password='testpass123', text=MESSAGE), task=self)]
