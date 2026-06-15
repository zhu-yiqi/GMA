from __future__ import annotations

from gma.assets import TempusPlaylistAsset
from gma.evaluation import AssetModified
from gma.tasks.base import BaseTask


OWNER_USERNAME = "testuserfjx"
ALBUM_NAME = "+"


class TempusAddLegoHouseToAcousticPracticePlaylistTask(BaseTask):
    apps = {"Tempus"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    before_playlist = TempusPlaylistAsset(
        name="Acoustic Practice",
        owner_username=OWNER_USERNAME,
        comment="Seeded playlist for add-song task.",
        visibility="private",
        track_titles=["Drunk"],
        track_albums={"Drunk": ALBUM_NAME},
    )
    after_playlist = TempusPlaylistAsset(
        name="Acoustic Practice",
        owner_username=OWNER_USERNAME,
        comment="Seeded playlist for add-song task.",
        visibility="private",
        track_titles=["Drunk", "Lego House"],
        track_albums={"Drunk": ALBUM_NAME, "Lego House": ALBUM_NAME},
    )
    assets = (before_playlist,)

    goal = 'Open Tempus, find the song "Lego House", and add it to the playlist "Acoustic Practice".'

    def criteria(self):
        return [AssetModified(self.before_playlist, self.after_playlist, task=self)]
