from __future__ import annotations

from gma.assets import ElementXMessageAsset, ElementXRoomAsset, ElementXUserAsset, TravelHotelBookingAsset
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

HOTEL = 'Canal Ring Hotel'
HOTEL_SLUG = 'canal-ring-hotel-boutique-lat52-3473-lon4-8781'
ROOM_ALIAS = 'lets-go-now-row263'
MESSAGE = f'I have booked the hotel for my stay in Amsterdam: {HOTEL}'

class TravelElementXAmsterdamHotelPinnedTask(BaseTask):
    apps = {'Travel', 'ElementX'}
    difficulty = 'hard'
    snapshot = 'gma_ready_state'

    booking = TravelHotelBookingAsset(user_email=TRAVEL_USER.email, hotel_name=HOTEL, hotel_slug=HOTEL_SLUG, check_in_ms=dt_ms(2026,10,2,15), check_out_ms=dt_ms(2026,10,5,11), guest_first_name='Jordan', guest_last_name='Miller', guest_phone='5550101005', guest_count=2, room_count=1, guests=[{'first_name':'Jordan','last_name':'Miller','email':'jordan.miller@example.com','phone':'5550101005','guest_type':'adult'}, {'first_name':'Sam','last_name':'Parker','guest_type':'adult'}], room_selections=[{'room_type':'Family Room','room_number':'1','bed_options':'2 Double Beds','count':1}], booking_status='confirmed', payment_status='paid')
    member = ElementXUserAsset(username='w5-row263-travel-member', password='password', display_name='Travel Member')
    room = ElementXRoomAsset(name="Let's Go Now", room_type='group', creator_username='testuser', creator_password='testpass123', members=['w5-row263-travel-member'], alias_localpart=ROOM_ALIAS, topic='Travel plans')
    assets = (TRAVEL_USER, member, room)

    goal = f'Open Travel and book {HOTEL} in Amsterdam from October 2, 2026 to October 5, 2026 for two adult guests Jordan Miller and Sam Parker. Use email "jordan.miller@example.com", country code "+1", and phone number "5550101005" for Jordan Miller. Choose one Family Room with "2 Double Beds", and complete payment. Then open ElementX, send exactly "{MESSAGE}" in Let\'s Go Now, and pin that message.'

    def setup(self, client) -> None:
        open_travel(client)

    def criteria(self):
        return [AssetExists(self.booking, task=self), AssetExists(ElementXMessageAsset(room=ROOM_ALIAS, sender_username='testuser', sender_password='testpass123', text=MESSAGE, pinned=True), task=self)]
