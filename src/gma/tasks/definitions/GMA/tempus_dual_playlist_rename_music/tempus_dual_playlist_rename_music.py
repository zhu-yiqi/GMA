
from __future__ import annotations

from gma.assets import TempusPlaylistAsset, TempusSessionAsset
from gma.evaluation import AssetExists, AssetModified
from gma.tasks.base import BaseTask


OWNER = "testuserfjx"
PLUS_ALBUM = "+"
EGO_ALBUM = "Ego"


class TempusDualPlaylistRenameMusicTask(BaseTask):
    apps = {"Tempus"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    favorites_before = TempusPlaylistAsset(name="Favorites", owner_username=OWNER, track_titles=["Drunk"], track_albums={"Drunk": PLUS_ALBUM})
    favorites_after = TempusPlaylistAsset(name="Favorite Pop Music", owner_username=OWNER, track_titles=["Drunk", "In the Dark"], track_albums={"Drunk": PLUS_ALBUM, "In the Dark": EGO_ALBUM})
    expected_english = TempusPlaylistAsset(name="English Music", owner_username=OWNER, track_titles=["The A Team"], track_albums={"The A Team": PLUS_ALBUM})
    assets = (favorites_before, TempusSessionAsset(username=OWNER, password="testpass123"))

    goal = (
        "Open Tempus, search for the song \"The A Team\" from the album \"+\", add it to a newly created playlist named \"Playlist 01\", "
        "then search for \"In the Dark\" and add it to the existing playlist named \"Favorites\". "
        "Rename \"Playlist 01\" to \"English Music\" and rename \"Favorites\" to \"Favorite Pop Music\"."
    )

    def criteria(self):
        return [AssetExists(self.expected_english, task=self), AssetModified(self.favorites_before, self.favorites_after, task=self)]
