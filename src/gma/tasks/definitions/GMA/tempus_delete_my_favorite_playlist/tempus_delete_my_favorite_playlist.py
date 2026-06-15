from __future__ import annotations

from gma.assets import TempusPlaylistAsset
from gma.evaluation import AssetDeleted
from gma.tasks.base import BaseTask


OWNER_USERNAME = "testuserfjx"
ALBUM_NAME = "+"


class TempusDeleteMyFavoritePlaylistTask(BaseTask):
    apps = {"Tempus"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    playlist = TempusPlaylistAsset(
        name="My Favorite Playlist",
        owner_username=OWNER_USERNAME,
        comment="Seeded playlist for delete task.",
        visibility="private",
        track_titles=["Small Bump", "This"],
        track_albums={"Small Bump": ALBUM_NAME, "This": ALBUM_NAME},
    )
    assets = (playlist,)

    goal = 'Open Tempus and delete the playlist named "My Favorite Playlist".'

    def criteria(self):
        return [AssetDeleted(self.playlist, task=self)]
