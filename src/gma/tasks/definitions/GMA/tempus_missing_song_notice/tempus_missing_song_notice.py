from __future__ import annotations

from gma.assets import TempusFavoriteAsset, TempusSessionAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


OWNER = "testuserfjx"


class TempusMissingSongNoticeTask(BaseTask):
    apps = {"Tempus"}
    difficulty = "hard"
    snapshot = "gma_ready_state"
    user_interaction = (
        "If the agent reports that Moonlit Fax Machine Waltz is not found and asks what to do, answer exactly: "
        "Favorite Lego House from the album + instead. Do not answer unrelated questions."
    )
    assets = (TempusSessionAsset(username=OWNER, password="testpass123"),)
    goal = "Open Tempus, search for \"Moonlit Fax Machine Waltz\", and add that song to my favorites."

    def criteria(self):
        return [AssetExists(TempusFavoriteAsset(item_type="song", track_title="Lego House", album_name="+", owner_username=OWNER), task=self)]
