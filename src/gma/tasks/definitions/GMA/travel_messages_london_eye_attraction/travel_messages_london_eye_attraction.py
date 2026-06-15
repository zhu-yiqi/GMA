from __future__ import annotations

from gma.assets import ContactAsset, SmsMessageAsset, TravelAttractionBookingAsset
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

SMS = "I booked the London Eye ticket for October 10."

class TravelMessagesLondonEyeAttractionTask(BaseTask):
    apps = {'Travel', 'Messages'}
    difficulty = 'hard'
    snapshot = 'gma_ready_state'

    booking = TravelAttractionBookingAsset(user_email=TRAVEL_USER.email, attraction_name='London Eye', attraction_slug='london-eye-london', visit_date_ms=dt_ms(2026,10,10,9), adult_tickets=1, child_tickets=0, visitors=[{'firstName':'Ryan','lastName':'Walker','type':'adult'}], booking_status='confirmed', payment_status='paid')
    contact = ContactAsset(name='Jordan Miller', phone_number='+15552012650')
    assets = (TRAVEL_USER, contact)
    user_interaction = None

    goal = f'Open Travel and book one adult ticket for the London Eye in London on October 10, 2026 for Ryan Walker. Complete payment so the attraction booking is confirmed. Then open Messages and send Jordan Miller exactly "{SMS}".'

    def setup(self, client) -> None:
        open_travel(client)

    def criteria(self):
        return [AssetExists(self.booking, task=self), AssetExists(SmsMessageAsset(address=self.contact.phone_number, body=SMS, box='sent', read=True), task=self)]
