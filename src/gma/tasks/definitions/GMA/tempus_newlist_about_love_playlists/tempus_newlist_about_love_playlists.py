
from __future__ import annotations

from gma.assets import TempusFavoriteAsset, TempusPlaylistAsset, TempusSessionAsset
from gma.evaluation import AssetExists, AssetModified
from gma.tasks.base import BaseTask


OWNER = "testuserfjx"
EGO = "Ego"
ASIA = "The End of Asia"
LIGHTS_ALBUM = "Ego"
TANGERINE_ALBUM = "Ego"


class TempusNewlistAboutLovePlaylistsTask(BaseTask):
    apps = {"Tempus"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    pm_before = TempusPlaylistAsset(name="PM", owner_username=OWNER, track_titles=["Lights Go Out"], track_albums={"Lights Go Out": LIGHTS_ALBUM})
    newlist_after = TempusPlaylistAsset(name="NewList", owner_username=OWNER, track_titles=["Lights Go Out", "The End of Asia"], track_albums={"Lights Go Out": LIGHTS_ALBUM, "The End of Asia": ASIA})
    new_songs_after = TempusPlaylistAsset(name="New Songs", owner_username=OWNER, track_titles=["In the Dark", "The End of Asia", "Lights Go Out"], track_albums={"In the Dark": EGO, "The End of Asia": ASIA, "Lights Go Out": LIGHTS_ALBUM})
    about_love_after = TempusPlaylistAsset(name="About Love", owner_username=OWNER, track_titles=["Tangerine Dreams"], track_albums={"Tangerine Dreams": TANGERINE_ALBUM})
    assets = (pm_before, TempusSessionAsset(username=OWNER, password="testpass123"))

    goal = (
        "Open Tempus, star \"In the Dark\", then create a playlist named \"New Songs\" and add \"In the Dark\" and \"The End of Asia\". "
        "Add \"Lights Go Out\" to \"New Songs\" and star the song. Add \"The End of Asia\" to playlist \"PM\", then rename \"PM\" exactly to \"NewList\". "
        "Finally create a playlist named \"About Love\", add \"Tangerine Dreams\" to it, and star \"Tangerine Dreams\"."
    )

    def criteria(self):
        return [
            AssetExists(self.new_songs_after, task=self),
            AssetModified(self.pm_before, self.newlist_after, task=self),
            AssetExists(self.about_love_after, task=self),
            AssetExists(TempusFavoriteAsset(item_type="song", track_title="In the Dark", album_name=EGO, owner_username=OWNER), task=self),
            AssetExists(TempusFavoriteAsset(item_type="song", track_title="Lights Go Out", album_name=LIGHTS_ALBUM, owner_username=OWNER), task=self),
            AssetExists(TempusFavoriteAsset(item_type="song", track_title="Tangerine Dreams", album_name=TANGERINE_ALBUM, owner_username=OWNER), task=self),
        ]
