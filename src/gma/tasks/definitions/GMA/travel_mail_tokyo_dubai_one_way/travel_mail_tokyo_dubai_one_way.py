from __future__ import annotations

from gma.assets import MailAccountAsset, MailMessageAsset, TravelFlightBookingAsset
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

MAIL_BODY = 'We are going to Dubai together on October 8, 2026.'

class TravelMailTokyoDubaiOneWayTask(BaseTask):
    apps = {'Travel', 'Mail'}
    difficulty = 'hard'
    category = []
    snapshot = 'gma_ready_state'

    booking = TravelFlightBookingAsset(user_email=TRAVEL_USER.email, from_airport='HND', to_airport='DXB', departure_date_ms=dt_ms(2026,10,8,12), flight_code='JL1541', passenger_first_name='Morgan', passenger_last_name='Taylor', passenger_email='2789456@gmail.com', passenger_phone='5550101119', passenger_phone_dial_code='+1', passenger_gender='female', passenger_country='United States', passenger_birth_ms=dt_ms(2003,5,18), passport_number='1112223334445', passport_expiry_ms=dt_ms(2030,10,26), passenger_count=1, seat_class='business', payment_status='paid', ticket_status='confirmed')
    account = MailAccountAsset(display_name='Morgan Taylor', email='morgan.taylor@example.com')
    expected_mail = MailMessageAsset(mailbox='sent', from_name=account.display_name, from_email='test@gmail.com', to=['456123@gmail.com'], subject='Dubai Travel Dates', body=MAIL_BODY, read=True)
    assets = (TRAVEL_USER, account)
    user_interaction = None

    goal = f'Open Travel and book Japan Airlines flight JL1541, a one-way business-class flight from Tokyo Haneda (HND) to Dubai (DXB) on October 8, 2026, for Morgan Taylor. Use date of birth May 18, 2003, passport "1112223334445", passport expiry October 26, 2030, nationality United States, gender Female, email "2789456@gmail.com", and phone "+1 5550101119". There is no seat, meal, or baggage preference. Complete payment so the flight booking is confirmed. Then send 456123@gmail.com an email with subject "Dubai Travel Dates" and body "{MAIL_BODY}".'

    def setup(self, client) -> None:
        open_travel(client)

    def criteria(self):
        return [AssetExists(self.booking, task=self), AssetExists(self.expected_mail, task=self)]
