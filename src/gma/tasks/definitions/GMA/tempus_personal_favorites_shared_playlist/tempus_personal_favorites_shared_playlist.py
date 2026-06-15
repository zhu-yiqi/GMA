
from __future__ import annotations

from gma.assets import TempusFavoriteAsset, TempusPlaylistAsset, TempusSessionAsset
from gma.evaluation import AssetExists, AssetModified
from gma.tasks.base import BaseTask


OWNER = "testuserfjx"
PLUS = "+"
EGO = "Ego"


class TempusPersonalFavoritesSharedPlaylistTask(BaseTask):
    apps = {"Tempus"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    starter_mix_before = TempusPlaylistAsset(name="Starter Mix", owner_username=OWNER, visibility="private", track_titles=["Drunk", "Grade 8"], track_albums={"Drunk": PLUS, "Grade 8": PLUS})
    personal_after = TempusPlaylistAsset(name="Personal Favorites", owner_username=OWNER, visibility="private", track_titles=["The A Team"], track_albums={"The A Team": PLUS})
    shared_playlist_after = TempusPlaylistAsset(name="Shared Favorites", owner_username=OWNER, visibility="private", track_titles=["The A Team", "In the Dark"], track_albums={"The A Team": PLUS, "In the Dark": EGO})
    assets = (starter_mix_before, TempusSessionAsset(username=OWNER, password="testpass123"))

    goal = (
        'Open Tempus, rename playlist "Starter Mix" to "Personal Favorites" and remove its existing songs. '
        'Find "The A Team" from the album "+", star it, and add it to "Personal Favorites". '
        'Create a new playlist named "Shared Favorites" and add exactly "The A Team" from the album "+" and "In the Dark" to it. Star both songs.'
    )

    def criteria(self):
        return [
            AssetModified(self.starter_mix_before, self.personal_after, task=self),
            AssetExists(self.shared_playlist_after, task=self),
            AssetExists(TempusFavoriteAsset(item_type="song", track_title="The A Team", album_name=PLUS, owner_username=OWNER), task=self),
            AssetExists(TempusFavoriteAsset(item_type="song", track_title="In the Dark", album_name=EGO, owner_username=OWNER), task=self),
        ]
