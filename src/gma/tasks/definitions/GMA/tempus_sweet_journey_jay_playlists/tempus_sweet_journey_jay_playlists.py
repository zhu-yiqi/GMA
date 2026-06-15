
from __future__ import annotations

from gma.assets import TempusFavoriteAsset, TempusPlaylistAsset, TempusSessionAsset
from gma.evaluation import AssetExists, AssetMissing, AssetModified
from gma.tasks.base import BaseTask


OWNER = "testuserfjx"
PLUS = "+"


class TempusSweetJourneyJayPlaylistsTask(BaseTask):
    apps = {"Tempus"}
    difficulty = "medium"
    category = ['Invalid-Instruction Tasks']
    snapshot = "gma_ready_state"
    user_interaction = (
        "If the agent reports that \"Look in the Sky\" is not found and asks what to do, answer exactly: "
        "Use \"The A Team\" from the album \"+\" instead. Do not answer unrelated questions."
    )

    journey_before = TempusPlaylistAsset(name="Journey Memories", owner_username=OWNER, track_titles=["Small Bump"], track_albums={"Small Bump": PLUS})
    journey_after = TempusPlaylistAsset(name="Journey Memories", owner_username=OWNER, track_titles=["Drunk", "Lego House", "Grade 8"], track_albums={"Drunk": PLUS, "Lego House": PLUS, "Grade 8": PLUS})
    sweet_after = TempusPlaylistAsset(name="Sweet Songs", owner_username=OWNER, track_titles=["The A Team", "Lego House"], track_albums={"The A Team": PLUS, "Lego House": PLUS})
    jay_after = TempusPlaylistAsset(name="Jay", owner_username=OWNER, track_titles=["Small Bump", "This"], track_albums={"Small Bump": PLUS, "This": PLUS})
    seed_small_bump_favorite = TempusFavoriteAsset(item_type="song", track_title="Small Bump", album_name=PLUS, owner_username=OWNER)
    assets = (journey_before, seed_small_bump_favorite, TempusSessionAsset(username=OWNER, password="testpass123"))

    goal = (
        "Open Tempus, search for \"Look in the Sky\", and add it to a playlist named \"Sweet Songs\". "
        "Search for \"Lego House\" from the album \"+\", star the song, and add it to \"Sweet Songs\". "
        "In the existing playlist \"Journey Memories\", add \"Drunk\", \"Lego House\", and \"Grade 8\" from the album \"+\", and star these three songs. Then remove \"Small Bump\" from \"Journey Memories\" and unstar the song. "
        "Create a new playlist named \"Jay\" and add \"Small Bump\" from the album \"+\" and \"This\" from the album \"+\" to it."
    )

    def criteria(self):
        return [
            AssetExists(self.sweet_after, task=self),
            AssetModified(self.journey_before, self.journey_after, task=self),
            AssetExists(self.jay_after, task=self),
            AssetExists(TempusFavoriteAsset(item_type="song", track_title="Lego House", album_name=PLUS, owner_username=OWNER), task=self),
            AssetExists(TempusFavoriteAsset(item_type="song", track_title="Drunk", album_name=PLUS, owner_username=OWNER), task=self),
            AssetExists(TempusFavoriteAsset(item_type="song", track_title="Grade 8", album_name=PLUS, owner_username=OWNER), task=self),
            AssetMissing(self.seed_small_bump_favorite, task=self),
        ]
