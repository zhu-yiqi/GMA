
from __future__ import annotations

from gma.assets import TempusFavoriteAsset, TempusPlaylistAsset, TempusSessionAsset
from gma.evaluation import AnswerEquals, AssetExists
from gma.tasks.base import BaseTask


OWNER = "testuserfjx"
PLUS = "+"
EXPECTED_ANSWER = "Lego House"


class TempusCompareSecondPlaylistUniqueSongTask(BaseTask):
    apps = {"Tempus"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    second_playlist = TempusPlaylistAsset(name="Second Playlist", owner_username=OWNER, track_titles=["The A Team", "Lego House"], track_albums={"The A Team": PLUS, "Lego House": PLUS})
    playlist_three = TempusPlaylistAsset(name="Playlist 3", owner_username=OWNER, track_titles=["The A Team", "Grade 8"], track_albums={"The A Team": PLUS, "Grade 8": PLUS})
    assets = (TempusSessionAsset(username=OWNER, password="testpass123"),)

    goal = (
        "Open Tempus, star \"The A Team\" from the album \"+\" and add it to a newly created playlist named \"Second Playlist\", then add \"Lego House\" to that playlist. "
        "Create a playlist named \"Playlist 3\" and add \"The A Team\" from the album \"+\" and \"Grade 8\" to it. "
        "Compare the two playlists and answer only with the exact song name that is in \"Second Playlist\" but not in \"Playlist 3\"."
    )

    def criteria(self):
        return [
            AssetExists(self.second_playlist, task=self),
            AssetExists(self.playlist_three, task=self),
            AssetExists(TempusFavoriteAsset(item_type="song", track_title="The A Team", album_name=PLUS, owner_username=OWNER), task=self),
            AnswerEquals(EXPECTED_ANSWER),
        ]
