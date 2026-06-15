from __future__ import annotations

from gma.assets import CalendarEventAsset, TravelHotelBookingAsset
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

HOTEL = 'Jordaan Boutique Inn'
HOTEL_SLUG = 'jordaan-boutique-inn-luxury-lat52-3575-lon4-8759'

class TravelCalendarAmsterdamBusinessTripTask(BaseTask):
    apps = {'Travel', 'Calendar'}
    difficulty = 'hard'
    snapshot = 'gma_ready_state'
    booking = TravelHotelBookingAsset(user_email=TRAVEL_USER.email, hotel_name=HOTEL, hotel_slug=HOTEL_SLUG, check_in_ms=dt_ms(2026,10,17,15), check_out_ms=dt_ms(2026,10,27,11), guest_first_name='Jordan', guest_last_name='Miller', guest_phone='5550101005', guest_count=1, room_count=1, guests=[{'first_name':'Jordan','last_name':'Miller','email':'jordan.miller@example.com','phone':'5550101005','guest_type':'adult'}], room_selections=[{'room_type':'Standard Room','count':1}], booking_status='confirmed', payment_status='paid')
    event = CalendarEventAsset(title='Business Trip', start_ms=dt_ms(2026,10,17,9), end_ms=dt_ms(2026,10,17,9), description=f'Business trip to Amsterdam. Hotel: {HOTEL}', reminder_minutes=(60,))
    assets = (TRAVEL_USER,)

    goal = f'Open Travel and book Jordaan Boutique Inn in Amsterdam from October 17, 2026 to October 27, 2026 for one adult guest Jordan Miller, using email "jordan.miller@example.com" and US phone number "5550101005". Choose one Standard Room and complete payment so the hotel booking is confirmed. Then create a Calendar event titled "Business Trip" at 9:00 AM on October 17, 2026, description "Business trip to Amsterdam. Hotel: {HOTEL}", and set a reminder one hour before.'

    def setup(self, client) -> None:
        open_travel(client)

    def criteria(self):
        return [AssetExists(self.booking, task=self), AssetExists(self.event, task=self)]
