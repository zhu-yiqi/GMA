from __future__ import annotations

from gma.apps.travel import TRAVEL_LOGIN_EMAIL, TRAVEL_LOGIN_FIRST_NAME, TRAVEL_LOGIN_LAST_NAME, TRAVEL_LOGIN_PASSWORD, TRAVEL_LOGIN_USERNAME, login_travel_app
from gma.assets import TravelFavoriteAsset, TravelUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


TRAVEL_USER = TravelUserAsset(
    email=TRAVEL_LOGIN_EMAIL,
    username=TRAVEL_LOGIN_USERNAME,
    password=TRAVEL_LOGIN_PASSWORD,
    first_name=TRAVEL_LOGIN_FIRST_NAME,
    last_name=TRAVEL_LOGIN_LAST_NAME,
)


class TravelMessagesBarcelonaFreeAttractionsInvalidTask(BaseTask):
    apps = {"Travel"}
    difficulty = "hard"
    snapshot = "gma_ready_state"
    free_attractions = (
        TravelFavoriteAsset(user_email=TRAVEL_USER.email, target="attraction", attraction_name="Barceloneta Beach", attraction_slug="barceloneta-beach-barcelona"),
        TravelFavoriteAsset(user_email=TRAVEL_USER.email, target="attraction", attraction_name="Gothic Quarter", attraction_slug="gothic-quarter-barcelona"),
        TravelFavoriteAsset(user_email=TRAVEL_USER.email, target="attraction", attraction_name="La Boqueria Market", attraction_slug="la-boqueria-market-barcelona"),
        TravelFavoriteAsset(user_email=TRAVEL_USER.email, target="attraction", attraction_name="La Rambla Walking Tour", attraction_slug="la-rambla-walking-tour-barcelona"),
    )
    user_interaction = (
        "If the agent reports that ten free Barcelona attractions are not available and asks what to do, answer exactly: "
        "Bookmark all available free Barcelona attractions instead. "
        "Do not answer unrelated questions."
    )
    assets = (TRAVEL_USER,)
    goal = "Open Travel and bookmark ten free attractions in Barcelona."

    def setup(self, client) -> None:
        login_travel_app(client, email=TRAVEL_LOGIN_EMAIL, username=TRAVEL_LOGIN_USERNAME, password=TRAVEL_LOGIN_PASSWORD, ensure_user=False)

    def criteria(self):
        return [
            *(AssetExists(favorite, task=self) for favorite in self.free_attractions),
        ]
