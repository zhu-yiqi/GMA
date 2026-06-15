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
from gma.assets import TravelFavoriteAsset, TravelUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


LOGIN_EMAIL = TRAVEL_LOGIN_EMAIL
LOGIN_USERNAME = TRAVEL_LOGIN_USERNAME
LOGIN_PASSWORD = TRAVEL_LOGIN_PASSWORD


def ms(year: int, month: int, day: int, hour: int = 12) -> int:
    return int(datetime(year, month, day, hour, 0, tzinfo=UTC).timestamp() * 1000)


def open_travel_app(client) -> None:
    login_travel_app(client, email=LOGIN_EMAIL, username=LOGIN_USERNAME, password=LOGIN_PASSWORD, ensure_user=False)


class TravelFavoriteGrandPalaceBangkokTask(BaseTask):
    apps = {"Travel"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    login_user = TravelUserAsset(
        email=LOGIN_EMAIL,
        username=LOGIN_USERNAME,
        password=LOGIN_PASSWORD,
        first_name=TRAVEL_LOGIN_FIRST_NAME,
        last_name=TRAVEL_LOGIN_LAST_NAME,
        phone="5550101118",
    )
    expected_favorite = TravelFavoriteAsset(
        user_email=LOGIN_EMAIL,
        target="attraction",
        attraction_name="Grand Palace",
        attraction_slug="grand-palace-bangkok",
    )
    assets = (login_user,)

    goal = "Open Travel, find the Grand Palace attraction in Bangkok, and add it to your favorites."

    def setup(self, client) -> None:
        open_travel_app(client)

    def criteria(self):
        return [AssetExists(self.expected_favorite, task=self)]
