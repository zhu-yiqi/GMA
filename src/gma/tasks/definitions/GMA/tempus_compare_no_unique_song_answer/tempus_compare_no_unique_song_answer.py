from __future__ import annotations

from gma.assets import TempusFavoriteAsset, TempusPlaylistAsset, TempusSessionAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


OWNER = "testuserfjx"
ASIA = "The End of Asia"
EGO = "Ego"


class TempusCompareNoUniqueSongAnswerTask(BaseTask):
    apps = {"Tempus"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    user_interaction = (
        "If the agent reports that no song appears in My Favorite Songs but not in Evening Check and asks what to do, answer exactly: "
        "Rename My Favorite Songs to My Favorite Songs Checked. Do not answer unrelated questions."
    )

    expected_renamed_playlist = TempusPlaylistAsset(name="My Favorite Songs Checked", owner_username=OWNER, track_titles=["The End of Asia"], track_albums={"The End of Asia": ASIA})
    comparison_playlist = TempusPlaylistAsset(name="Evening Check", owner_username=OWNER, track_titles=["The End of Asia", "In the Dark"], track_albums={"The End of Asia": ASIA, "In the Dark": EGO})
    assets = (TempusSessionAsset(username=OWNER, password="testpass123"),)

    goal = (
        'Open Tempus, create a playlist named "My Favorite Songs", add "The End of Asia" to it, and star that song. '
        'Then create a playlist named "Evening Check" and add "The End of Asia" and "In the Dark" to it. '
        'Compare these two newly created playlists and tell me which song appears in "My Favorite Songs" but not in "Evening Check".'
    )

    def criteria(self):
        return [
            AssetExists(self.expected_renamed_playlist, task=self),
            AssetExists(self.comparison_playlist, task=self),
            AssetExists(TempusFavoriteAsset(item_type="song", track_title="The End of Asia", album_name=ASIA, owner_username=OWNER), task=self),
        ]
