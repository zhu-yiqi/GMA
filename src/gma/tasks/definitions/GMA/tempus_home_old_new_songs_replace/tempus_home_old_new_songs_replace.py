
from __future__ import annotations

from gma.assets import TempusFavoriteAsset, TempusPlaylistAsset, TempusSessionAsset
from gma.evaluation import AssetExists, AssetModified
from gma.tasks.base import BaseTask


OWNER = "testuserfjx"
PLUS = "+"
EGO = "Ego"
BEST = "Best Day Ever"
FULL_OF_IT_ALBUM = "Ego"


class TempusHomeOldNewSongsReplaceTask(BaseTask):
    apps = {"Tempus"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    new_before = TempusPlaylistAsset(name="New Songs", owner_username=OWNER, track_titles=["Drunk", "This"], track_albums={"Drunk": PLUS, "This": PLUS})
    new_after = TempusPlaylistAsset(name="New Songs", owner_username=OWNER, track_titles=["This", "In the Dark", "She Said"], track_albums={"This": PLUS, "In the Dark": EGO, "She Said": BEST})
    old_after = TempusPlaylistAsset(name="Old Songs", owner_username=OWNER, track_titles=["Lights Go Out", "In the Dark", "She Said"], track_albums={"Lights Go Out": EGO, "In the Dark": EGO, "She Said": BEST})
    assets = (new_before, TempusSessionAsset(username=OWNER, password="testpass123"))

    goal = (
        "Open Tempus, search for \"Full of It\" and star it. Then search for \"In the Dark\" and add it to the existing playlist \"New Songs\". "
        "Create a new playlist named \"Old Songs\" and add \"Lights Go Out\", \"In the Dark\", and \"She Said\" to it. "
        "In \"New Songs\", replace \"Drunk\" with \"She Said\"."
    )

    def criteria(self):
        return [
            AssetExists(TempusFavoriteAsset(item_type="song", track_title="Full of It", album_name=FULL_OF_IT_ALBUM, owner_username=OWNER), task=self),
            AssetModified(self.new_before, self.new_after, task=self),
            AssetExists(self.old_after, task=self),
        ]
