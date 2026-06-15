from __future__ import annotations

from gma.apps.elementx import elementx_user_id
from gma.assets import ElementXMessageAsset, ElementXRoomAsset, ElementXUserAsset, TravelHotelBookingAsset, TravelReviewAsset
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

HOTEL = 'Fishing Creek Lodge'
HOTEL_SLUG = 'fishing-creek-lodge-budget-lat30.40016-lon-97.726486'
PRICE = '88.00 USD'
MESSAGE = f'I found the hotel reservation from last time; I think this one is good-you can take a look. {HOTEL}, price {PRICE}.'
OLIVIA_BROOKS = 'olivia-brooks-row271'
DM_ROOM = elementx_user_id(OLIVIA_BROOKS)

class TravelElementXAustinHotelReviewTask(BaseTask):
    apps = {'Travel', 'ElementX'}
    difficulty = 'hard'
    snapshot = 'gma_ready_state'

    seeded_booking = TravelHotelBookingAsset(user_email=TRAVEL_USER.email, hotel_name=HOTEL, hotel_slug=HOTEL_SLUG, check_in_ms=dt_ms(2026,9,29,15), check_out_ms=dt_ms(2026,9,30,11), guest_first_name='Owner', guest_last_name='Traveler', guest_count=1, room_count=1, room_selections=[{'room_type':'Budget Room','room_number':'1','bed_options':'2 Queen Beds','count':1}], total_price=88, booking_status='completed', payment_status='paid')
    review = TravelReviewAsset(user_email=TRAVEL_USER.email, target='hotel', hotel_name=HOTEL, hotel_slug=HOTEL_SLUG, rating=5, comment='Good')
    user = ElementXUserAsset(username=OLIVIA_BROOKS, password='password', display_name='Olivia Brooks')
    assets = (TRAVEL_USER, seeded_booking, user)

    goal = 'Open Travel, find the hotel from my existing hotel booking, and write a 5-star review for that hotel with comment "Good". Then open ElementX and send Olivia Brooks a message using exactly this format with the hotel name and total price from that booking, keeping exactly two digits after the decimal point for the price: "I found the hotel reservation from last time; I think this one is good-you can take a look. <hotel name>, price <total price> USD."'

    def setup(self, client) -> None:
        open_travel(client)
        client.press_home()

    def criteria(self):
        return [AssetExists(self.review, task=self), AssetExists(ElementXRoomAsset(name='Olivia Brooks', room_type='dm', creator_username='testuser', creator_password='testpass123', members=[OLIVIA_BROOKS]), task=self), AssetExists(ElementXMessageAsset(room=DM_ROOM, sender_username='testuser', sender_password='testpass123', text=MESSAGE), task=self)]
