
from __future__ import annotations

from gma.assets import TempusFavoriteAsset, TempusPlaylistAsset, TempusSessionAsset
from gma.evaluation import AssetExists, AssetModified
from gma.tasks.base import BaseTask


OWNER = "testuserfjx"
ALBUMS = ["Ego", "Best Day Ever", "The End of Asia"]
BEST_DAY_EVER_SONGS = ["All Around the World", "BDE Bonus", "Best Day Ever"]


class TempusFavoriteAlbumsRenameMyFavoritesTask(BaseTask):
    apps = {"Tempus"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    before_playlist = TempusPlaylistAsset(name="My Favorites", owner_username=OWNER, track_titles=["In the Dark"], track_albums={"In the Dark": "Ego"})
    after_playlist = TempusPlaylistAsset(name="My Favorites V1", owner_username=OWNER, track_titles=["In the Dark", *BEST_DAY_EVER_SONGS], track_albums={"In the Dark": "Ego", **{title: "Best Day Ever" for title in BEST_DAY_EVER_SONGS}})
    assets = (before_playlist, TempusSessionAsset(username=OWNER, password="testpass123"))

    goal = (
        "Open Tempus and star these albums: \"Ego\", \"Best Day Ever\", and \"The End of Asia\". "
        "Then add these songs from the album \"Best Day Ever\" to playlist \"My Favorites\": "
        "\"All Around the World\", \"BDE Bonus\", and \"Best Day Ever\". Finally rename \"My Favorites\" exactly to \"My Favorites V1\"."
    )

    def criteria(self):
        return [
            *[AssetExists(TempusFavoriteAsset(item_type="album", album_name=album, owner_username=OWNER), task=self) for album in ALBUMS],
            AssetModified(self.before_playlist, self.after_playlist, task=self),
        ]
