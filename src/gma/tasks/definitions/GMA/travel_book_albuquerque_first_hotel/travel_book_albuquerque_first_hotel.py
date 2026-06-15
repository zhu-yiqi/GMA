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
from gma.assets import TravelHotelBookingAsset, TravelUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


LOGIN_EMAIL = TRAVEL_LOGIN_EMAIL
LOGIN_USERNAME = TRAVEL_LOGIN_USERNAME
LOGIN_PASSWORD = TRAVEL_LOGIN_PASSWORD


def ms(year: int, month: int, day: int, hour: int = 12) -> int:
    return int(datetime(year, month, day, hour, 0, tzinfo=UTC).timestamp() * 1000)


def open_travel_app(client) -> None:
    login_travel_app(client, email=LOGIN_EMAIL, username=LOGIN_USERNAME, password=LOGIN_PASSWORD, ensure_user=False)


class TravelBookAlbuquerqueFirstHotelTask(BaseTask):
    apps = {"Travel"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    login_user = TravelUserAsset(
        email=LOGIN_EMAIL,
        username=LOGIN_USERNAME,
        password=LOGIN_PASSWORD,
        first_name=TRAVEL_LOGIN_FIRST_NAME,
        last_name=TRAVEL_LOGIN_LAST_NAME,
        phone="5550101113",
    )
    expected_booking = TravelHotelBookingAsset(
        user_email=LOGIN_EMAIL,
        hotel_name="Grand Gaming Resort",
        hotel_slug="grand-gaming-resort-resort-and-spa-lat35.1087-lon-106.605949",
        check_in_ms=ms(2026, 10, 2, 15),
        check_out_ms=ms(2026, 10, 3, 11),
        guest_first_name="Ryan",
        guest_last_name="Walker",
        guest_count=1,
        room_count=1,
        guests=[
            {
                "first_name": "Ryan",
                "last_name": "Walker",
                "email": "bhi@gmail.com",
                "phone": "5550101000",
                "guest_type": "adult",
            }
        ],
        room_selections=[{"room_type": "Budget Room", "bed_options": "1 Queen Bed", "count": 1}],
        payment_status="paid",
        booking_status="confirmed",
    )
    assets = (login_user,)

    goal = (
        "Open Travel and book a hotel in Albuquerque from October 2, 2026 to October 3, 2026. "
        "Select the first result, Grand Gaming Resort, and the first room type, Budget Room with "
        "1 Queen Bed, for one adult guest. Use guest name \"Ryan Walker\", email \"bhi@gmail.com\", "
        "and US phone number \"5550101000\". Complete payment so the booking is confirmed."
    )

    def setup(self, client) -> None:
        open_travel_app(client)

    def criteria(self):
        return [AssetExists(self.expected_booking, task=self)]
