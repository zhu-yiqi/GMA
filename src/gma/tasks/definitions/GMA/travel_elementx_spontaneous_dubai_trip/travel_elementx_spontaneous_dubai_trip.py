from __future__ import annotations

from gma.apps.elementx import elementx_user_id
from gma.assets import ElementXMessageAsset, ElementXRoomAsset, ElementXUserAsset, TravelFlightBookingAsset
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

DM_USER = 'jack-row278'
DM_ROOM = elementx_user_id(DM_USER)
MESSAGE = "I'm starting my spontaneous trip."

class TravelElementXSpontaneousDubaiTripTask(BaseTask):
    apps = {'Travel', 'ElementX'}
    difficulty = 'hard'
    snapshot = 'gma_ready_state'

    outbound = TravelFlightBookingAsset(user_email=TRAVEL_USER.email, from_airport='LHR', to_airport='DXB', flight_code='BA2579', departure_date_ms=dt_ms(2026,10,10,12), passenger_first_name='Evan', passenger_last_name='Carter', passenger_email='254536854@gmail.com', passenger_phone='5550101116', passenger_phone_dial_code='+1', passenger_gender='female', passenger_country='United States', passenger_birth_ms=dt_ms(1990,6,18), passport_number='6536549879861', passport_expiry_ms=dt_ms(2028,11,20), passenger_count=1, seat_class='economy', payment_status='paid', ticket_status='confirmed')
    user = ElementXUserAsset(username=DM_USER, password='password', display_name='Jack')
    assets = (TRAVEL_USER, user)
    user_interaction = 'If the agent asks for the departure airport, respond: Heathrow Airport (LHR).'

    goal = f'Open Travel and book a one-way economy ticket on British Airways flight BA2579 from Heathrow (LHR) to Dubai (DXB), departing October 10, 2026, for Evan Carter. Use date of birth June 18, 1990, passport "6536549879861", passport expiry November 20, 2028, nationality United States, gender Female, email "254536854@gmail.com", country code "+1", and phone number "5550101116". There is no seat, meal, or baggage preference. Complete payment so the flight booking is confirmed. Then open ElementX and send Jack exactly "{MESSAGE}".'

    def setup(self, client) -> None:
        open_travel(client)

    def criteria(self):
        return [AssetExists(self.outbound, task=self), AssetExists(ElementXRoomAsset(name='Jack', room_type='dm', creator_username='testuser', creator_password='testpass123', members=[DM_USER]), task=self), AssetExists(ElementXMessageAsset(room=DM_ROOM, sender_username='testuser', sender_password='testpass123', text=MESSAGE), task=self)]
