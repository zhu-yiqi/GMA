from __future__ import annotations

from gma.assets import TempusPlaylistAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


OWNER_USERNAME = "testuserfjx"
ALBUM_NAME = "+"


class TempusCreateMyFavoritePlaylistTask(BaseTask):
    apps = {"Tempus"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    expected_playlist = TempusPlaylistAsset(
        name="My Favorite Playlist",
        owner_username=OWNER_USERNAME,
        comment=None,
        track_titles=["Lego House"],
        track_albums={"Lego House": ALBUM_NAME},
        track_match="contains",
    )

    goal = (
        'Open Tempus and create a playlist named "My Favorite Playlist". '
        'Add the song "Lego House" from the album "+" to make the new playlist saveable.'
    )

    def criteria(self):
        return [AssetExists(self.expected_playlist, task=self)]
