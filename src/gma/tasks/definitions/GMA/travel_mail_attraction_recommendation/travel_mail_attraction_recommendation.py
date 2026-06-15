from __future__ import annotations

from gma.assets import MailAccountAsset, MailMessageAsset, TravelAttractionBookingAsset, TravelFavoriteAsset
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

ATTRACTION = 'Dubai Marina Walk'
ADDRESS = 'Dubai UAE'
MAIL_BODY = f'I recommend a fun attraction to you, {ATTRACTION}, {ADDRESS}'

class TravelMailAttractionRecommendationTask(BaseTask):
    apps = {'Travel', 'Mail'}
    difficulty = 'hard'
    snapshot = 'gma_ready_state'

    seeded_booking = TravelAttractionBookingAsset(user_email=TRAVEL_USER.email, attraction_name=ATTRACTION, attraction_slug='dubai-marina-walk-dubai', visit_date_ms=dt_ms(2026,10,14,9), adult_tickets=1, child_tickets=0, visitors=[{'firstName':'Owner','lastName':'Traveler','type':'adult'}], booking_status='confirmed', payment_status='paid')
    favorite = TravelFavoriteAsset(user_email=TRAVEL_USER.email, target='attraction', attraction_name=ATTRACTION, attraction_slug='dubai-marina-walk-dubai')
    account = MailAccountAsset(display_name='Ava Brooks', email='ava.brooks@example.com')
    expected_mail = MailMessageAsset(mailbox='sent', from_name=account.display_name, from_email='test@gmail.com', to=['olivia.brooks.travel@gmail.com'], subject='Attraction Recommendation', body=MAIL_BODY, read=True)
    assets = (TRAVEL_USER, seeded_booking, account)

    goal = 'Open Travel, locate the October 14, 2026 attraction booking for Dubai Marina Walk, read its address, and favorite the attraction. Then open Mail and send olivia.brooks.travel@gmail.com an email with subject "Attraction Recommendation" and a body in exactly this format: "I recommend a fun attraction to you, Dubai Marina Walk, <address>".'

    def setup(self, client) -> None:
        open_travel(client)
        client.press_home()

    def criteria(self):
        return [AssetExists(self.favorite, task=self), AssetExists(self.expected_mail, task=self)]
