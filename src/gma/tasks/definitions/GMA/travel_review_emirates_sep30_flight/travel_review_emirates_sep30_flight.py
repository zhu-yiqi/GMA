from __future__ import annotations

from gma.assets import TravelFlightBookingAsset, TravelReviewAsset
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

SEEDED_FLIGHT = TravelFlightBookingAsset(
    user_email=TRAVEL_USER.email,
    from_airport="DXB",
    to_airport="LHR",
    departure_date_ms=dt_ms(2026, 9, 30, 0),
    flight_code="EK2106",
    passenger_first_name="Owner",
    passenger_last_name="Traveler",
    passenger_email=TRAVEL_USER.email,
    passenger_phone="5550101121",
    passenger_phone_dial_code="+1",
    passenger_gender="other",
    passenger_country="United States",
    passenger_birth_ms=dt_ms(1995, 1, 1),
    passport_number="P48201984",
    passport_expiry_ms=dt_ms(2031, 1, 1),
    passenger_count=1,
    seat_class="economy",
    payment_status="paid",
    ticket_status="confirmed",
)
EXPECTED_REVIEW = TravelReviewAsset(user_email=TRAVEL_USER.email, target="flight", from_airport="DXB", to_airport="LHR", flight_code="EK2106", departure_date_ms=dt_ms(2026, 9, 30, 0), rating=5, comment="Very punctual.")


class TravelReviewEmiratesSep30FlightTask(BaseTask):
    apps = {"Travel"}
    difficulty = "medium"
    category = []
    snapshot = "gma_ready_state"
    assets = (TRAVEL_USER, SEEDED_FLIGHT)
    user_interaction = "If the agent asks which flight of the September 30 Emirates order to review, answer: Review the Dubai to London Emirates flight."
    goal = "Open Travel and review the flight of my Emirates order EK2106 from Dubai to London on September 30, 2026 with 5 stars and the exact review text \"Very punctual.\""

    def setup(self, client):
        open_travel(client)

    def criteria(self):
        return [AssetExists(EXPECTED_REVIEW, task=self)]
