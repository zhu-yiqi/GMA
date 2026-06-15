from __future__ import annotations

from gma.assets import ElementXMessageAsset, ElementXRoomAsset, ElementXUserAsset, MailAccountAsset, MailMessageAsset, TravelReviewAsset
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

HOTEL = 'Thames Riverside Inn'
HOTEL_SLUG = 'thames-riverside-inn-luxury-lat51-4892-lon-0-1273'
ADDRESS = '378 Main St, London, England, 58908, United Kingdom'
REVIEW = 'The environment is excellent and I will definitely stay there again.'
GROUP_ALIAS = 'w5-row275-hotel-group'
GROUP_MESSAGE = f'The relevant hotel has been contacted. Address: {ADDRESS} @room'
MAIL_BODY = 'Thames Riverside Inn hotel is performing well in all aspects and is suitable for long-term cooperation'

class TravelMailElementXThamesHotelReviewTask(BaseTask):
    apps = {'Travel', 'Mail', 'ElementX'}
    difficulty = 'hard'
    snapshot = 'gma_ready_state'

    review = TravelReviewAsset(user_email=TRAVEL_USER.email, target='hotel', hotel_name=HOTEL, hotel_slug=HOTEL_SLUG, rating=5, comment=REVIEW)
    account = MailAccountAsset(display_name='Harper Lewis', email='harper.lewis@example.com')
    expected_mail = MailMessageAsset(mailbox='sent', from_name=account.display_name, from_email='test@gmail.com', to=['sdf@gmail.com'], subject='Hotel Evaluation', body=MAIL_BODY, read=True)
    member = ElementXUserAsset(username='w5-row275-hotel-member', password='password', display_name='Hotel Group Member')
    room = ElementXRoomAsset(name='Hotel Cooperation Group', room_type='group', creator_username='testuser', creator_password='testpass123', members=['w5-row275-hotel-member'], alias_localpart=GROUP_ALIAS, topic='Hotel cooperation')
    assets = (TRAVEL_USER, account, member, room)

    goal = f'Open Travel and write a 5-star review for Thames Riverside Inn with exactly "{REVIEW}". Read the hotel address. Open Mail and send sdf@gmail.com an email with subject "Hotel Evaluation" and body "{MAIL_BODY}". Open ElementX and send Hotel Cooperation Group a room-mentioned message in exactly this format: "The relevant hotel has been contacted. Address: <address> @room".'

    def setup(self, client) -> None:
        open_travel(client)

    def criteria(self):
        return [AssetExists(self.review, task=self), AssetExists(self.expected_mail, task=self), AssetExists(ElementXMessageAsset(room=GROUP_ALIAS, sender_username='testuser', sender_password='testpass123', text=GROUP_MESSAGE, mentions_room=True), task=self)]
