from __future__ import annotations

from gma.assets import TempusPlaylistAsset
from gma.evaluation import AssetModified
from gma.tasks.base import BaseTask


OWNER_USERNAME = "testuserfjx"
ALBUM_NAME = "+"


class TempusRemoveDrunkFromEveningQueuePlaylistTask(BaseTask):
    apps = {"Tempus"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    before_playlist = TempusPlaylistAsset(
        name="Evening Queue",
        owner_username=OWNER_USERNAME,
        comment="Seeded playlist for remove-song task.",
        track_titles=["Drunk", "Grade 8"],
        track_albums={"Drunk": ALBUM_NAME, "Grade 8": ALBUM_NAME},
    )
    after_playlist = TempusPlaylistAsset(
        name="Evening Queue",
        owner_username=OWNER_USERNAME,
        comment="Seeded playlist for remove-song task.",
        track_titles=["Grade 8"],
        track_albums={"Grade 8": ALBUM_NAME},
    )
    assets = (before_playlist,)

    goal = 'Open Tempus, find the playlist "Evening Queue", and remove the song "Drunk" from that playlist.'

    def criteria(self):
        return [AssetModified(self.before_playlist, self.after_playlist, task=self)]
