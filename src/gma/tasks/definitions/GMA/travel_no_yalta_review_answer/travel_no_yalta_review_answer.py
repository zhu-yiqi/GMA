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


class TravelNoYaltaReviewAnswerTask(BaseTask):
    apps = {"Travel"}
    difficulty = "hard"
    snapshot = "gma_ready_state"
    category = ["Invalid-Instruction Tasks"]
    user_interaction = (
        "If the agent reports that Yalta Cliff Castle in Yalta is not available for review and asks what to do, answer exactly: "
        "Favorite Kiyomizu-dera Temple in Kyoto instead. Do not answer unrelated questions."
    )
    assets = (TRAVEL_USER,)
    goal = 'Open Travel and write a review for Yalta Cliff Castle in Yalta with 4 stars and the exact review text "The view sounds unforgettable."'
    expected_favorite = TravelFavoriteAsset(user_email=TRAVEL_USER.email, target="attraction", attraction_name="Kiyomizu-dera Temple", attraction_slug="kiyomizu-dera-temple-kyoto")

    def setup(self, client) -> None:
        login_travel_app(client, email=TRAVEL_LOGIN_EMAIL, username=TRAVEL_LOGIN_USERNAME, password=TRAVEL_LOGIN_PASSWORD, ensure_user=False)

    def criteria(self):
        return [AssetExists(self.expected_favorite, task=self)]
