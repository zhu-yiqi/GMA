from __future__ import annotations

from gma.assets import TravelHotelBookingAsset
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

HOTEL_SLUG = "stay-kay-city-hotel-boutique-lat40.760586-lon-73.975403"
EXPECTED_BOOKING = TravelHotelBookingAsset(
    user_email=TRAVEL_USER.email,
    hotel_slug=HOTEL_SLUG,
    hotel_name="Stay-Kay City Hotel",
    check_in_ms=dt_ms(2026, 10, 5, 15),
    check_out_ms=dt_ms(2026, 10, 7, 11),
    guest_first_name="Max",
    guest_last_name="Miller",
    guest_count=1,
    room_count=1,
    guests=[{"first_name": "Max", "last_name": "Miller", "email": "max.miller@example.com", "phone": "5550101002", "guest_type": "adult"}],
    room_selections=[{"room_type": "Deluxe Room", "bed_options": "1 King Bed", "count": 1}],
    booking_status="confirmed",
    payment_status="paid",
)


class TravelBookStayKayDeluxeRoomTask(BaseTask):
    apps = {"Travel"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (TRAVEL_USER,)
    goal = (
        "Open Travel and book one room at Stay-Kay City Hotel in New York from October 5, 2026 to October 7, 2026. "
        "Book for one adult guest, Max Miller, using email \"max.miller@example.com\" and US phone number \"5550101002\". "
        "Choose one Deluxe Room with \"1 King Bed\", then complete payment so the booking is confirmed."
    )

    def setup(self, client):
        open_travel(client)

    def criteria(self):
        return [AssetExists(EXPECTED_BOOKING, task=self)]
