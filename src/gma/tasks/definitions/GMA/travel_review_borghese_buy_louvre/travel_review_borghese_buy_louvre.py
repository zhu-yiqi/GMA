from __future__ import annotations

from gma.assets import TravelAttractionBookingAsset, TravelFavoriteAsset, TravelReviewAsset
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

BORGHese_BOOKING = TravelAttractionBookingAsset(
    user_email=TRAVEL_USER.email,
    attraction_name="Borghese Gallery",
    attraction_slug="borghese-gallery-rome",
    visit_date_ms=dt_ms(2026, 9, 30, 9),
    adult_tickets=1,
    visitors=[{"firstName": "Owner", "lastName": "Traveler", "type": "adult"}],
    booking_status="completed",
    payment_status="paid",
)
EXPECTED_REVIEW = TravelReviewAsset(user_email=TRAVEL_USER.email, target="attraction", attraction_name="Borghese Gallery", attraction_slug="borghese-gallery-rome", rating=4, comment="It offers rich art-related information.", visit_date_ms=dt_ms(2026, 9, 30, 9), is_verified=False)
LOUVRE_FAVORITE = TravelFavoriteAsset(user_email=TRAVEL_USER.email, target="attraction", attraction_name="Louvre Museum", attraction_slug="louvre-museum-paris")
EXPECTED_LOUVRE_BOOKING = TravelAttractionBookingAsset(
    user_email=TRAVEL_USER.email,
    attraction_name="Louvre Museum",
    attraction_slug="louvre-museum-paris",
    visit_date_ms=dt_ms(2026, 10, 3, 9),
    adult_tickets=2,
    child_tickets=0,
    visitors=[{"firstName": "Emily", "lastName": "Parker", "type": "adult"}, {"firstName": "Tyler", "lastName": "Morgan", "type": "adult"}],
    booking_status="confirmed",
    payment_status="paid",
)


class TravelReviewBorgheseBuyLouvreTask(BaseTask):
    apps = {"Travel"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (TRAVEL_USER, BORGHese_BOOKING)
    user_interaction = "If the agent asks which Borghese Gallery order to use, answer: Use the most recent one."
    goal = (
        "Open Travel and review the attraction from my most recent Borghese Gallery order with a 4-star rating and the exact comment "
        "\"It offers rich art-related information.\" Then search for Louvre Museum, save it if it is not already saved, "
        "and buy two adult tickets for October 3, 2026 for Emily Parker and Tyler Morgan. Complete payment."
    )

    def setup(self, client):
        open_travel(client)

    def criteria(self):
        return [AssetExists(EXPECTED_REVIEW, task=self), AssetExists(LOUVRE_FAVORITE, task=self), AssetExists(EXPECTED_LOUVRE_BOOKING, task=self)]
