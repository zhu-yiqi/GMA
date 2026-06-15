from __future__ import annotations

from gma.assets import TravelAttractionBookingAsset
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

EXPECTED_BOOKING = TravelAttractionBookingAsset(
    user_email=TRAVEL_USER.email,
    attraction_name="Borghese Gallery",
    attraction_slug="borghese-gallery-rome",
    visit_date_ms=dt_ms(2026, 10, 2, 9),
    adult_tickets=2,
    child_tickets=1,
    visitors=[
        {"firstName": "Jack", "lastName": "Young", "type": "adult"},
        {"firstName": "Lucas", "lastName": "Smith", "type": "adult"},
        {"firstName": "Nora", "lastName": "Lewis", "type": "child"},
    ],
    booking_status="confirmed",
    payment_status="paid",
)


class TravelBookBorgheseTicketsTask(BaseTask):
    apps = {"Travel"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (TRAVEL_USER,)
    goal = (
        "Open Travel and book three tickets for Borghese Gallery on October 2, 2026: "
        "two adult tickets for Jack Young and Lucas Smith, and one child ticket for Nora Lewis. "
        "Complete payment so the attraction booking is confirmed."
    )

    def setup(self, client):
        open_travel(client)

    def criteria(self):
        return [AssetExists(EXPECTED_BOOKING, task=self)]
