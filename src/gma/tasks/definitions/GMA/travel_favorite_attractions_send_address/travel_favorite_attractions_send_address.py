from __future__ import annotations

from gma.assets import ElementXMessageAsset, ElementXRoomAsset, ElementXUserAsset, TravelFavoriteAsset
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

DM_USER = "w4-row193-travel-morgan"
ROOM_ALIAS = "w4-row193-travel-address"
ROOM_NAME = "Travel Address Chat"
START_TIME_MESSAGE = "St Stephen's Cathedral opening time: 08:00"
RIJKSMUSEUM_FAVORITE = TravelFavoriteAsset(user_email=TRAVEL_USER.email, target="attraction", attraction_name="Rijksmuseum", attraction_slug="rijksmuseum-amsterdam")
STEPHEN_FAVORITE = TravelFavoriteAsset(user_email=TRAVEL_USER.email, target="attraction", attraction_name="St Stephen's Cathedral", attraction_slug="st-stephen-s-cathedral-vienna")
EXPECTED_MESSAGE = ElementXMessageAsset(room=ROOM_ALIAS, sender_username="testuser", sender_password="testpass123", text=START_TIME_MESSAGE)


class TravelFavoriteAttractionsSendAddressTask(BaseTask):
    apps = {"Travel", "ElementX"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (
        TRAVEL_USER,
        ElementXUserAsset(username=DM_USER, password="password", display_name="Morgan Travel"),
        ElementXRoomAsset(name=ROOM_NAME, room_type="dm", creator_username="testuser", creator_password="testpass123", members=[DM_USER], alias_localpart=ROOM_ALIAS, topic="Travel address relay"),
    )
    goal = (
        "Open Travel, save Rijksmuseum in Amsterdam and save St Stephen's Cathedral in Vienna. "
        "Check St Stephen's Cathedral's opening time, then open ElementX and send Travel Address Chat a message in exactly this format: "
        '"St Stephen\'s Cathedral opening time: <time>".'
    )

    def setup(self, client):
        open_travel(client)

    def criteria(self):
        return [
            AssetExists(RIJKSMUSEUM_FAVORITE, task=self),
            AssetExists(STEPHEN_FAVORITE, task=self),
            AssetExists(EXPECTED_MESSAGE, task=self),
        ]
