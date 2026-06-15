from __future__ import annotations

from pathlib import Path
from gma.apps.xiaoshiliu import XIAOSHILIU_LOGIN_USER_ID
from gma.assets import ContactAsset, DeviceFileAsset, ImageContentExpectation, SmsMessageAsset, TravelFlightBookingAsset, XiaoShiLiuPostAsset
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

POST_TEXT = 'What are some fun attractions in Atlanta?'
SMS = "I'm going to Atlanta on October 2, 2026 - let's hang out if you're free. Here's my flight info: Emirates EK0815 from DXB to ATL."
IMAGE_FILENAME = 'atlanta-attraction.jpeg'

class TravelXslMessagesAtlantaFlightTask(BaseTask):
    apps = {'Travel', 'XiaoShiLiu', 'Gallery', 'Messages'}
    difficulty = 'hard'
    snapshot = 'gma_ready_state'

    booking = TravelFlightBookingAsset(user_email=TRAVEL_USER.email, from_airport='DXB', to_airport='ATL', departure_date_ms=dt_ms(2026,10,2,12), flight_code='EK0815', passenger_first_name='Riley', passenger_last_name='Carter', passenger_email='fad@gmail.com', passenger_phone='5550101007', passenger_phone_dial_code='+1', passenger_gender='female', passenger_country='United States', passenger_birth_ms=dt_ms(1998,6,1), passport_number='1236549874561', passport_expiry_ms=dt_ms(2027,11,9), passenger_count=1, seat_class='first', payment_status='paid', ticket_status='confirmed')
    image = DeviceFileAsset(app='Gallery', storage_dir='Pictures', filename=IMAGE_FILENAME, mime_type='image/jpeg', source_path=str(Path(__file__).with_name('assets') / IMAGE_FILENAME))
    xsl_post = XiaoShiLiuPostAsset(author_user_id=XIAOSHILIU_LOGIN_USER_ID, title='Atlanta Attractions Question', content=POST_TEXT, category='Travel', min_image_count=1, expected_images=(ImageContentExpectation(source_path=str(Path(__file__).with_name('assets') / IMAGE_FILENAME)),))
    contact = ContactAsset(name='Blake', phone_number='+15552012740')
    assets = (TRAVEL_USER, image, contact)
    user_interaction = None

    goal = f'Open Travel and book Emirates flight EK0815, a first-class flight from Dubai (DXB) to Atlanta (ATL) on October 2, 2026 for Riley Carter. Use date of birth June 1, 1998, passport "1236549874561", passport expiry November 9, 2027, nationality United States, gender Female, email "fad@gmail.com", and phone "+1 5550101007". There is no seat, meal, or baggage preference. Complete payment so the flight booking is confirmed. Open XiaoShiLiu and create a post in the Travel category titled "Atlanta Attractions Question" with content "{POST_TEXT}" and upload the latest image from Gallery. Open Messages and send Blake exactly "{SMS}".'

    def setup(self, client) -> None:
        open_travel(client)

    def criteria(self):
        return [AssetExists(self.booking, task=self), AssetExists(self.xsl_post, task=self), AssetExists(SmsMessageAsset(address=self.contact.phone_number, body=SMS, box='sent', read=True), task=self)]
