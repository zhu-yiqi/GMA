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
from gma.assets import TravelAttractionBookingAsset, TravelUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


LOGIN_EMAIL = TRAVEL_LOGIN_EMAIL
LOGIN_USERNAME = TRAVEL_LOGIN_USERNAME
LOGIN_PASSWORD = TRAVEL_LOGIN_PASSWORD


def ms(year: int, month: int, day: int, hour: int = 12) -> int:
    return int(datetime(year, month, day, hour, 0, tzinfo=UTC).timestamp() * 1000)


def open_travel_app(client) -> None:
    login_travel_app(client, email=LOGIN_EMAIL, username=LOGIN_USERNAME, password=LOGIN_PASSWORD, ensure_user=False)


class TravelBookUbudMonkeyForestTicketsTask(BaseTask):
    apps = {"Travel"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    login_user = TravelUserAsset(
        email=LOGIN_EMAIL,
        username=LOGIN_USERNAME,
        password=LOGIN_PASSWORD,
        first_name=TRAVEL_LOGIN_FIRST_NAME,
        last_name=TRAVEL_LOGIN_LAST_NAME,
        phone="5550101115",
    )
    expected_booking = TravelAttractionBookingAsset(
        user_email=LOGIN_EMAIL,
        attraction_name="Ubud Monkey Forest",
        attraction_slug="ubud-monkey-forest-bali",
        visit_date_ms=ms(2026, 10, 6, 9),
        adult_tickets=1,
        child_tickets=1,
        visitors=[
            {"firstName": "Avery", "lastName": "Cooper", "type": "adult"},
            {"firstName": "Noah", "lastName": "Bennett", "type": "child"},
        ],
        payment_status="paid",
        booking_status="confirmed",
    )
    assets = (login_user,)

    goal = (
        "Open Travel and purchase tickets for Ubud Monkey Forest in Bali on October 6, 2026. "
        "Buy one adult ticket and one child ticket. Use visitor 1 name \"Avery Cooper\" and visitor 2 "
        "name \"Noah Bennett\". Complete payment so the booking is confirmed."
    )

    def setup(self, client) -> None:
        open_travel_app(client)

    def criteria(self):
        return [AssetExists(self.expected_booking, task=self)]
