from __future__ import annotations

from gma.assets import TravelAttractionBookingAsset, TravelHotelBookingAsset, TravelReviewAsset
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
SEEDED_BOOKING = TravelHotelBookingAsset(
    user_email=TRAVEL_USER.email,
    hotel_name="Stay-Kay City Hotel",
    hotel_slug=HOTEL_SLUG,
    check_in_ms=dt_ms(2026, 9, 28, 15),
    check_out_ms=dt_ms(2026, 9, 30, 11),
    guest_first_name="Owner",
    guest_last_name="Traveler",
    guest_count=1,
    room_count=1,
    guests=[{"first_name": "Owner", "last_name": "Traveler", "guest_type": "adult"}],
    room_selections=[{"room_number": "11", "room_type": "Deluxe Room", "bed_options": "1 King Bed", "count": 1}],
    booking_status="completed",
    payment_status="paid",
)
EXPECTED_REVIEW = TravelReviewAsset(user_email=TRAVEL_USER.email, target="hotel", hotel_name="Stay-Kay City Hotel", hotel_slug=HOTEL_SLUG, rating=5, comment="The room was very spacious and bright.")
EXPECTED_TICKET = TravelAttractionBookingAsset(user_email=TRAVEL_USER.email, attraction_name="Ueno Zoo", attraction_slug="ueno-zoo-tokyo", visit_date_ms=dt_ms(2026, 10, 8, 9), adult_tickets=1, child_tickets=0, visitors=[{"firstName": "Jordan", "lastName": "Miller", "type": "adult"}], booking_status="confirmed", payment_status="paid")


class TravelReviewStayKayBookUenoZooTask(BaseTask):
    apps = {"Travel"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (TRAVEL_USER, SEEDED_BOOKING)
    goal = (
        "Open Travel and check the hotel from my last completed Stay-Kay City Hotel booking. If the hotel has not been reviewed, leave a 5-star review with the exact comment "
        "\"The room was very spacious and bright.\" Then book one adult ticket for Ueno Zoo on October 8, 2026 for Jordan Miller and complete payment."
    )

    def setup(self, client):
        open_travel(client)

    def criteria(self):
        return [AssetExists(EXPECTED_REVIEW, task=self), AssetExists(EXPECTED_TICKET, task=self)]
