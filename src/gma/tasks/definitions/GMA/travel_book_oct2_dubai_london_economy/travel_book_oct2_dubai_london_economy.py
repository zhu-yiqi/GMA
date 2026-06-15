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
from gma.assets import TravelFlightBookingAsset, TravelUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


LOGIN_EMAIL = TRAVEL_LOGIN_EMAIL
LOGIN_USERNAME = TRAVEL_LOGIN_USERNAME
LOGIN_PASSWORD = TRAVEL_LOGIN_PASSWORD


def ms(year: int, month: int, day: int, hour: int = 12) -> int:
    return int(datetime(year, month, day, hour, 0, tzinfo=UTC).timestamp() * 1000)


def open_travel_app(client) -> None:
    login_travel_app(client, email=LOGIN_EMAIL, username=LOGIN_USERNAME, password=LOGIN_PASSWORD, ensure_user=False)


class TravelBookOct2DubaiLondonEconomyTask(BaseTask):
    apps = {"Travel"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    login_user = TravelUserAsset(
        email=LOGIN_EMAIL,
        username=LOGIN_USERNAME,
        password=LOGIN_PASSWORD,
        first_name=TRAVEL_LOGIN_FIRST_NAME,
        last_name=TRAVEL_LOGIN_LAST_NAME,
        phone="5550101114",
    )
    expected_booking = TravelFlightBookingAsset(
        user_email=LOGIN_EMAIL,
        from_airport="DXB",
        to_airport="LHR",
        flight_code="EK2156",
        departure_date_ms=ms(2026, 10, 2, 0),
        passenger_first_name="Evan",
        passenger_last_name="Carter",
        passenger_email="fad@gmail.com",
        passenger_phone="5550101007",
        passenger_gender="female",
        passenger_country="United States",
        passenger_birth_ms=ms(2000, 1, 1, 0),
        passport_number="1236549874561",
        passport_expiry_ms=ms(2027, 12, 3, 0),
        passenger_count=1,
        seat_class="economy",
        payment_status="paid",
        ticket_status="confirmed",
    )
    assets = (login_user,)

    goal = (
        "Open Travel and book the first economy flight from Dubai (DXB) to London (LHR) "
        "departing on October 2, 2026 for one adult passenger. Use passenger name \"Evan Carter\", "
        "date of birth January 1, 2000, passport number \"1236549874561\", passport expiry date "
        "December 3, 2027, nationality United States, gender Female, email \"fad@gmail.com\", and phone "
        "number \"5550101007\". There is no seat, meal, or baggage preference. Complete payment so the booking is confirmed."
    )

    def setup(self, client) -> None:
        open_travel_app(client)

    def criteria(self):
        return [AssetExists(self.expected_booking, task=self)]
