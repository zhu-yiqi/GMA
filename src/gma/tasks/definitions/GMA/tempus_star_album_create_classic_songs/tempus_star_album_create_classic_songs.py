from __future__ import annotations

from gma.assets import TempusFavoriteAsset, TempusPlaylistAsset, TempusSessionAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


OWNER = "testuserfjx"
ALBUM = "Stoney"
SONGS = ["Congratulations", "White Iverson", "I Fall Apart", "Go Flex", "Feeling Whitney"]


class TempusStarAlbumCreateClassicSongsTask(BaseTask):
    apps = {"Tempus"}
    difficulty = "medium"
    category = []
    snapshot = "gma_ready_state"

    expected_album = TempusFavoriteAsset(item_type="album", album_name=ALBUM, owner_username=OWNER)
    expected_playlist = TempusPlaylistAsset(name="Classic Songs", owner_username=OWNER, track_titles=SONGS, track_albums={title: ALBUM for title in SONGS})
    assets = (TempusSessionAsset(username=OWNER, password="testpass123"),)

    goal = (
        'Open Tempus, star the album "Stoney", create a playlist named "Classic Songs", '
        'and add these five songs from that album: "Congratulations", "White Iverson", "I Fall Apart", "Go Flex", and "Feeling Whitney". '
        'Star those five songs too.'
    )

    def criteria(self):
        return [
            AssetExists(self.expected_album, task=self),
            AssetExists(self.expected_playlist, task=self),
            *[AssetExists(TempusFavoriteAsset(item_type="song", track_title=title, album_name=ALBUM, owner_username=OWNER), task=self) for title in SONGS],
        ]
