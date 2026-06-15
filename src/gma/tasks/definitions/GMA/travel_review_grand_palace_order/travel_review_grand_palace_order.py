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
ATTRACTION_SLUG = "grand-palace-bangkok"
ATTRACTION_NAME = "Grand Palace"
REVIEW_TEXT = "The scenery is great and my family had a wonderful time."


class TravelReviewGrandPalaceOrderTask(BaseTask):
    apps = {"Travel"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    login_user = TravelUserAsset(
        email=LOGIN_EMAIL,
        username=LOGIN_USERNAME,
        password=TRAVEL_LOGIN_PASSWORD,
        first_name=TRAVEL_LOGIN_FIRST_NAME,
        last_name=TRAVEL_LOGIN_LAST_NAME,
        phone="5550101123",
    )
    seeded_booking = TravelAttractionBookingAsset(
        user_email=LOGIN_EMAIL,
        attraction_name=ATTRACTION_NAME,
        attraction_slug=ATTRACTION_SLUG,
        visit_date_ms=ms(2026, 9, 30, 9),
        adult_tickets=2,
        child_tickets=0,
        visitors=[
            {"firstName": "Avery", "lastName": "Palace", "type": "adult"},
            {"firstName": "Jordan", "lastName": "Palace", "type": "adult"},
        ],
        booking_status="completed",
        payment_status="paid",
    )
    expected_review = TravelReviewAsset(
        user_email=LOGIN_EMAIL,
        target="attraction",
        attraction_name=ATTRACTION_NAME,
        attraction_slug=ATTRACTION_SLUG,
        rating=4,
        comment=REVIEW_TEXT,
        is_verified=False,
    )
    assets = (login_user, seeded_booking)

    goal = (
        "Open Travel and review the attraction from my last completed attraction order. "
        "Give it 4 stars and write exactly \"The scenery is great and my family had a wonderful time.\""
    )

    def setup(self, client) -> None:
        open_travel_app(client, LOGIN_EMAIL, LOGIN_USERNAME)

    def criteria(self):
        return [AssetExists(self.expected_review, task=self)]
