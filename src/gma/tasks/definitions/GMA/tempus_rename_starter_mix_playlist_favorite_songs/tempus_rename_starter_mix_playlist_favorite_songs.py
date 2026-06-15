from __future__ import annotations

from gma.assets import TempusPlaylistAsset
from gma.evaluation import AssetModified
from gma.tasks.base import BaseTask


OWNER_USERNAME = "testuserfjx"
ALBUM_NAME = "+"
TRACKS = ["Drunk", "Grade 8"]


class TempusRenameStarterMixPlaylistFavoriteSongsTask(BaseTask):
    apps = {"Tempus"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    before_playlist = TempusPlaylistAsset(
        name="Starter Mix",
        owner_username=OWNER_USERNAME,
        comment="Seeded playlist for rename task.",
        track_titles=TRACKS,
        track_albums={title: ALBUM_NAME for title in TRACKS},
    )
    after_playlist = TempusPlaylistAsset(
        name="My favorite songs",
        owner_username=OWNER_USERNAME,
        comment="Seeded playlist for rename task.",
        track_titles=TRACKS,
        track_albums={title: ALBUM_NAME for title in TRACKS},
    )
    assets = (before_playlist,)

    goal = 'Open Tempus, find the playlist "Starter Mix", and rename it exactly to "My favorite songs".'

    def criteria(self):
        return [AssetModified(self.before_playlist, self.after_playlist, task=self)]
