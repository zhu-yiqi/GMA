from __future__ import annotations

from datetime import UTC, datetime

from gma.apps.travel import TRAVEL_LOGIN_EMAIL, TRAVEL_LOGIN_FIRST_NAME, TRAVEL_LOGIN_LAST_NAME, TRAVEL_LOGIN_PASSWORD, TRAVEL_LOGIN_USERNAME, login_travel_app
from gma.assets import TravelAttractionBookingAsset, TravelUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


TRAVEL_USER = TravelUserAsset(
    email=TRAVEL_LOGIN_EMAIL,
    username=TRAVEL_LOGIN_USERNAME,
    password=TRAVEL_LOGIN_PASSWORD,
    first_name=TRAVEL_LOGIN_FIRST_NAME,
    last_name=TRAVEL_LOGIN_LAST_NAME,
    phone="5550101114",
)


def dt_ms(year: int, month: int, day: int, hour: int = 12) -> int:
    return int(datetime(year, month, day, hour, 0, tzinfo=UTC).timestamp() * 1000)


class TravelNoYaltaFlightAnswerTask(BaseTask):
    apps = {"Travel"}
    difficulty = "hard"
    snapshot = "gma_ready_state"
    category = ["Invalid-Instruction Tasks"]
    user_interaction = (
        "If the agent reports that Yalta Cliff Castle in Yalta is not available and asks what to do, answer exactly: "
        "Book Borghese Gallery in Rome instead, keeping the same visit date, ticket counts, visitor names, and visitor types, and complete payment so the attraction booking is confirmed. Do not answer unrelated questions."
    )
    assets = (TRAVEL_USER,)
    goal = (
        "Open Travel and book tickets for Yalta Cliff Castle in Yalta on October 6, 2026. "
        "Buy two adult tickets and one child ticket. Use visitor 1 Evan Carter as an adult, "
        "visitor 2 Maya Carter as an adult, and visitor 3 Lily Carter as a child. "
        "Complete payment so the attraction booking is confirmed."
    )
    expected_booking = TravelAttractionBookingAsset(
        user_email=TRAVEL_USER.email,
        attraction_name="Borghese Gallery",
        attraction_slug="borghese-gallery-rome",
        visit_date_ms=dt_ms(2026, 10, 6, 9),
        adult_tickets=2,
        child_tickets=1,
        visitors=[
            {"firstName": "Evan", "lastName": "Carter", "type": "adult"},
            {"firstName": "Maya", "lastName": "Carter", "type": "adult"},
            {"firstName": "Lily", "lastName": "Carter", "type": "child"},
        ],
        booking_status="confirmed",
        payment_status="paid",
    )

    def setup(self, client) -> None:
        login_travel_app(client, email=TRAVEL_LOGIN_EMAIL, username=TRAVEL_LOGIN_USERNAME, password=TRAVEL_LOGIN_PASSWORD, ensure_user=False)

    def criteria(self):
        return [AssetExists(self.expected_booking, task=self)]
