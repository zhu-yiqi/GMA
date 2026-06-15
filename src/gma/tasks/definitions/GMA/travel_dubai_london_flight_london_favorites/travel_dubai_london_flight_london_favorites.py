from __future__ import annotations

from gma.assets import TravelFavoriteAsset, TravelFlightBookingAsset
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
    ('Tower of London', 'tower-of-london-london'),
    ('British Museum', 'british-museum-london'),
    ('Buckingham Palace', 'buckingham-palace-london'),
]

class TravelDubaiLondonFlightLondonFavoritesTask(BaseTask):
    apps = {'Travel'}
    difficulty = 'hard'
    category = ['Information-Gathering Tasks']
    snapshot = 'gma_ready_state'

    booking = TravelFlightBookingAsset(user_email=TRAVEL_USER.email, from_airport='DXB', to_airport='LHR', departure_date_ms=dt_ms(2026,10,5,12), flight_code='EK2922', passenger_first_name='Evan', passenger_last_name='Carter', passenger_email='254536854@gmail.com', passenger_phone='5550101116', passenger_phone_dial_code='+1', passenger_gender='female', passenger_country='United States', passenger_birth_ms=dt_ms(1990,6,18), passport_number='6536549879861', passport_expiry_ms=dt_ms(2028,11,20), passenger_count=1, seat_class='economy', payment_status='paid', ticket_status='confirmed')
    assets = (TRAVEL_USER,)

    goal = 'Open Travel and book an economy flight from Dubai (DXB) to London (LHR) on October 5, 2026 for Evan Carter. Use date of birth June 18, 1990, passport "6536549879861", passport expiry November 20, 2028, nationality United States, passenger gender Female, email "254536854@gmail.com", and US phone number "5550101116". There is no seat, meal, or baggage preference. Complete payment so the flight booking is confirmed. Then save Tower of London, British Museum, and Buckingham Palace.'
    user_interaction = 'If the agent asks which flight to book, answer: Use flight EK2922.'

    def setup(self, client) -> None:
        open_travel(client)

    def criteria(self):
        return [AssetExists(self.booking, task=self)] + [AssetExists(TravelFavoriteAsset(user_email=TRAVEL_USER.email, target='attraction', attraction_name=name, attraction_slug=slug), task=self) for name, slug in FAVORITES]
