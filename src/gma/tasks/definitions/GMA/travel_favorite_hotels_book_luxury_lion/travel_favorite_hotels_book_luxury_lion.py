from __future__ import annotations

from gma.assets import TravelFavoriteAsset, TravelHotelBookingAsset
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

LAKEFRONT_SLUG = "lakefront-captain-inn-budget-lat41.725285-lon-72.761261"
LUXURY_LION_SLUG = "luxury-lion-resort-luxury-lat38.67219-lon-90.44081"
LAKEFRONT_FAVORITE = TravelFavoriteAsset(user_email=TRAVEL_USER.email, target="hotel", hotel_name="Lakefront Captain Inn", hotel_slug=LAKEFRONT_SLUG)
LUXURY_LION_FAVORITE = TravelFavoriteAsset(user_email=TRAVEL_USER.email, target="hotel", hotel_name="Luxury Lion Resort", hotel_slug=LUXURY_LION_SLUG)
EXPECTED_BOOKING = TravelHotelBookingAsset(
    user_email=TRAVEL_USER.email,
    hotel_name="Luxury Lion Resort",
    hotel_slug=LUXURY_LION_SLUG,
    check_in_ms=dt_ms(2026, 10, 5, 15),
    check_out_ms=dt_ms(2026, 10, 6, 11),
    guest_first_name="Evan",
    guest_last_name="Foster",
    guest_count=1,
    room_count=1,
    guests=[{"first_name": "Evan", "last_name": "Foster", "email": "234@gmail.com", "phone": "5550101002", "guest_type": "adult"}],
    room_selections=[{"room_number": "1", "room_type": "Standard Room", "bed_options": "1 King Bed", "count": 1}],
    booking_status="confirmed",
    payment_status="paid",
)


class TravelFavoriteHotelsBookLuxuryLionTask(BaseTask):
    apps = {"Travel"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (TRAVEL_USER,)
    goal = (
        "Open Travel and save Lakefront Captain Inn in West Hartford on New Britain Avenue. Then open Luxury Lion Resort in St. Louis; "
        "if it is not already saved, save it. Book one room at Luxury Lion Resort from October 5, 2026 to October 6, 2026 for one adult guest, Evan Foster, "
        "using email \"234@gmail.com\" and phone \"+1 5550101002\". Choose one Standard Room with \"1 King Bed\", and complete payment."
    )

    def setup(self, client):
        open_travel(client)

    def criteria(self):
        return [AssetExists(LAKEFRONT_FAVORITE, task=self), AssetExists(LUXURY_LION_FAVORITE, task=self), AssetExists(EXPECTED_BOOKING, task=self)]
