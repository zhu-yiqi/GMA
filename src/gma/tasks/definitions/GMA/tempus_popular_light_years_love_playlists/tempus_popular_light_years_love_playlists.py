
from __future__ import annotations

from gma.assets import TempusFavoriteAsset, TempusPlaylistAsset, TempusSessionAsset
from gma.evaluation import AssetExists, AssetModified
from gma.tasks.base import BaseTask


OWNER = "testuserfjx"
PLUS = "+"
EGO = "Ego"
FULL_OF_IT_ALBUM = "Ego"


class TempusPopularLightYearsLovePlaylistsTask(BaseTask):
    apps = {"Tempus"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    pop_before = TempusPlaylistAsset(name="Pop Music", owner_username=OWNER, track_titles=["Drunk"], track_albums={"Drunk": PLUS})
    light_after = TempusPlaylistAsset(name="Light Years Playlist", owner_username=OWNER, track_titles=["Drunk", "In the Dark"], track_albums={"Drunk": PLUS, "In the Dark": EGO})
    popular_after = TempusPlaylistAsset(name="Popular Songs", owner_username=OWNER, track_titles=["The A Team", "Drunk", "Lego House"], track_albums={"The A Team": PLUS, "Drunk": PLUS, "Lego House": PLUS})
    love_after = TempusPlaylistAsset(name="Love Songs Playlist", owner_username=OWNER, track_titles=["Full of It"], track_albums={"Full of It": FULL_OF_IT_ALBUM})
    assets = (pop_before, TempusSessionAsset(username=OWNER, password="testpass123"))

    goal = (
        "Open Tempus, star \"The A Team\" from the album \"+\", then create a playlist named \"Popular Songs\" and add \"The A Team\" from the album \"+\" and \"Drunk\". "
        "Star \"Drunk\", then add \"Lego House\" and star the song. Add \"In the Dark\" to the playlist \"Pop Music\", then rename \"Pop Music\" exactly to \"Light Years Playlist\". "
        "Finally create \"Love Songs Playlist\", add \"Full of It\" to it, and star \"Full of It\"."
    )

    def criteria(self):
        return [
            AssetExists(self.popular_after, task=self),
            AssetModified(self.pop_before, self.light_after, task=self),
            AssetExists(self.love_after, task=self),
            *[AssetExists(TempusFavoriteAsset(item_type="song", track_title=title, album_name=album, owner_username=OWNER), task=self) for title, album in [("The A Team", PLUS), ("Drunk", PLUS), ("Lego House", PLUS), ("Full of It", FULL_OF_IT_ALBUM)]],
        ]
