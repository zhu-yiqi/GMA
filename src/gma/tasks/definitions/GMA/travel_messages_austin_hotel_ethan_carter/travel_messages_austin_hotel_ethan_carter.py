from __future__ import annotations

from gma.assets import ContactAsset, SmsMessageAsset, TravelHotelBookingAsset
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
SMS = f'I have booked the hotel: {HOTEL}'

class TravelMessagesAustinHotelEthanCarterTask(BaseTask):
    apps = {'Travel', 'Messages'}
    difficulty = 'hard'
    snapshot = 'gma_ready_state'

    booking = TravelHotelBookingAsset(user_email=TRAVEL_USER.email, hotel_name=HOTEL, hotel_slug=HOTEL_SLUG, check_in_ms=dt_ms(2026,10,1,15), check_out_ms=dt_ms(2026,10,2,11), guest_first_name='Nathan', guest_last_name='Cooper', guest_phone='5550101001', guest_count=2, room_count=1, guests=[{'first_name':'Nathan','last_name':'Cooper','email':'nathan.cooper@example.com','phone':'5550101001','guest_type':'adult'}, {'first_name':'Maya','last_name':'Cooper','guest_type':'adult'}], room_selections=[{'room_type':'Budget Room','bed_options':'1 King Bed','count':1}], booking_status='confirmed', payment_status='paid')
    contact = ContactAsset(name='Ethan Carter', phone_number='+15552012770')
    assets = (TRAVEL_USER, contact)

    goal = f'Open Travel and book Fishing Creek Lodge in Austin for October 1, 2026 to October 2, 2026. Book one room for two adult guests, Nathan Cooper and Maya Cooper, use Nathan Cooper\'s email "nathan.cooper@example.com" and phone "+1 5550101001", choose one Budget Room with "1 King Bed", and complete payment so the hotel booking is confirmed. Then open Messages and send Ethan Carter exactly "{SMS}".'

    def setup(self, client) -> None:
        open_travel(client)

    def criteria(self):
        return [AssetExists(self.booking, task=self), AssetExists(SmsMessageAsset(address=self.contact.phone_number, body=SMS, box='sent', read=True), task=self)]
