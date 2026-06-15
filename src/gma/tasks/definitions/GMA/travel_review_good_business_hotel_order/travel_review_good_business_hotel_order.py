from __future__ import annotations

from datetime import UTC, datetime

from gma.apps.travel import (
    TRAVEL_LOGIN_EMAIL,
    TRAVEL_LOGIN_FIRST_NAME,
    TRAVEL_LOGIN_LAST_NAME,
    TRAVEL_LOGIN_PASSWORD,
    TRAVEL_LOGIN_USERNAME,
    login_travel_app,
)
from gma.assets import TravelAttractionBookingAsset, TravelHotelBookingAsset, TravelReviewAsset, TravelUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


def ms(year: int, month: int, day: int, hour: int = 12) -> int:
    return int(datetime(year, month, day, hour, 0, tzinfo=UTC).timestamp() * 1000)


def open_travel_app(client, email: str, username: str) -> None:
    login_travel_app(client, email=email, username=username, password=TRAVEL_LOGIN_PASSWORD, ensure_user=False)


LOGIN_EMAIL = TRAVEL_LOGIN_EMAIL
LOGIN_USERNAME = TRAVEL_LOGIN_USERNAME
HOTEL_SLUG = "good-business-hotel-suite-lat33.923931-lon-84.34153"
HOTEL_NAME = "Good Business Hotel"
REVIEW_TEXT = "Not bad, I'll definitely come back next time."


class TravelReviewGoodBusinessHotelOrderTask(BaseTask):
    apps = {"Travel"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    login_user = TravelUserAsset(
        email=LOGIN_EMAIL,
        username=LOGIN_USERNAME,
        password=TRAVEL_LOGIN_PASSWORD,
        first_name=TRAVEL_LOGIN_FIRST_NAME,
        last_name=TRAVEL_LOGIN_LAST_NAME,
        phone="5550101122",
    )
    seeded_booking = TravelHotelBookingAsset(
        user_email=LOGIN_EMAIL,
        hotel_name=HOTEL_NAME,
        hotel_slug=HOTEL_SLUG,
        check_in_ms=ms(2026, 9, 29, 15),
        check_out_ms=ms(2026, 9, 30, 11),
        guest_first_name="Nora",
        guest_last_name="Hayes",
        guest_count=1,
        room_count=1,
        room_selections=[{"room_type": "Budget Room", "room_number": "1", "bed_options": "2 Queen Beds", "count": 1}],
        booking_status="completed",
        payment_status="paid",
    )
    expected_review = TravelReviewAsset(
        user_email=LOGIN_EMAIL,
        target="hotel",
        hotel_name=HOTEL_NAME,
        hotel_slug=HOTEL_SLUG,
        rating=3,
        comment=REVIEW_TEXT,
    )
    assets = (login_user, seeded_booking)

    goal = (
        "Open Travel and review the hotel from my last completed Good Business Hotel order. "
        "Give it 3 stars and write exactly \"Not bad, I'll definitely come back next time.\""
    )

    def setup(self, client) -> None:
        open_travel_app(client, LOGIN_EMAIL, LOGIN_USERNAME)

    def criteria(self):
        return [AssetExists(self.expected_review, task=self)]
