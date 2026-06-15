from __future__ import annotations

from pathlib import Path
from gma.apps.xiaoshiliu import XIAOSHILIU_LOGIN_USER_ID
from gma.assets import ContactAsset, DeviceFileAsset, ImageContentExpectation, SmsMessageAsset, TravelAttractionBookingAsset, TravelFavoriteAsset, TravelReviewAsset, XiaoShiLiuPostAsset
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

REVIEW = 'I highly recommend that everyone come and visit. It has a strong local flavor and the staff are friendly and patient.'
POST_BODY = 'I visited here last time and it was pretty good Tokyo Skytree'
IMAGE_FILENAME = 'scenic-spot.jpeg'
SMS = 'Hello, I have completed the scenic spot review and posted a thread as requested.'

class TravelXslMessagesScenicReviewPostTask(BaseTask):
    apps = {'Travel', 'XiaoShiLiu', 'Gallery', 'Messages'}
    difficulty = 'hard'
    snapshot = 'gma_ready_state'

    seeded_booking = TravelAttractionBookingAsset(user_email=TRAVEL_USER.email, attraction_name='Tokyo Skytree', attraction_slug='tokyo-skytree-tokyo', visit_date_ms=dt_ms(2026,9,30,9), adult_tickets=1, child_tickets=0, visitors=[{'firstName':'Owner','lastName':'Traveler','type':'adult'}], booking_status='completed', payment_status='paid')
    favorite = TravelFavoriteAsset(user_email=TRAVEL_USER.email, target='attraction', attraction_name='Tokyo Skytree', attraction_slug='tokyo-skytree-tokyo')
    review = TravelReviewAsset(user_email=TRAVEL_USER.email, target='attraction', attraction_name='Tokyo Skytree', attraction_slug='tokyo-skytree-tokyo', rating=5, comment=REVIEW, visit_date_ms=dt_ms(2026,9,30,9), is_verified=False)
    image = DeviceFileAsset(app='Gallery', storage_dir='Pictures', filename=IMAGE_FILENAME, mime_type='image/jpeg', source_path=str(Path(__file__).with_name('assets') / IMAGE_FILENAME))
    expected_post = XiaoShiLiuPostAsset(author_user_id=XIAOSHILIU_LOGIN_USER_ID, title='Tourist Attraction', content=POST_BODY, category='Travel', min_image_count=1, expected_images=(ImageContentExpectation(source_path=str(Path(__file__).with_name('assets') / IMAGE_FILENAME)),))
    contact = ContactAsset(name='John', phone_number='+15552012660')
    assets = (TRAVEL_USER, seeded_booking, image, contact)

    goal = f'Open Travel, favorite Tokyo Skytree and write a 5-star review with exactly "{REVIEW}". Then open XiaoShiLiu and create a post in the Travel category, titled "Tourist Attraction", with content "{POST_BODY}", and upload the latest image from Gallery. Open Messages and send John exactly "{SMS}".'

    def setup(self, client) -> None:
        open_travel(client)

    def criteria(self):
        return [AssetExists(self.favorite, task=self), AssetExists(self.review, task=self), AssetExists(self.expected_post, task=self), AssetExists(SmsMessageAsset(address=self.contact.phone_number, body=SMS, box='sent', read=True), task=self)]
