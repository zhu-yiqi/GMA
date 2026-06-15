
from __future__ import annotations

from gma.assets import TempusFavoriteAsset, TempusPlaylistAsset, TempusSessionAsset
from gma.evaluation import AssetModified, AssetExists
from gma.tasks.base import BaseTask


OWNER = "testuserfjx"
ALBUM = "+"
ROAD_TRIP_BEFORE_TRACKS = ["Autumn Leaves", "Drunk", "Give Me Love _ The Parting Glass", "Gold Rush", "Grade 8", "U.N.I."]
YEARS_TRACKS = ["The A Team", "Lego House", "Small Bump"]
FINAL_TRACKS = ["This", "The A Team", "Lego House", "Small Bump"]


class TempusRebuildRoadTripRecommendedPlaylistTask(BaseTask):
    apps = {"Tempus"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    road_trip_before = TempusPlaylistAsset(name="Road Trip Mix", owner_username=OWNER, track_titles=ROAD_TRIP_BEFORE_TRACKS, track_albums={title: ALBUM for title in ROAD_TRIP_BEFORE_TRACKS})
    road_trip_after = TempusPlaylistAsset(name="Road Trip Mix", owner_username=OWNER, track_titles=["U.N.I."], track_albums={"U.N.I.": ALBUM})
    years_playlist = TempusPlaylistAsset(name="Years", owner_username=OWNER, track_titles=YEARS_TRACKS, track_albums={title: ALBUM for title in YEARS_TRACKS})
    discovery_before = TempusPlaylistAsset(name="Discovery Playlist", owner_username=OWNER, track_titles=["This"], track_albums={"This": ALBUM})
    recommended_after = TempusPlaylistAsset(name="Recommended Playlist", owner_username=OWNER, track_titles=FINAL_TRACKS, track_albums={title: ALBUM for title in FINAL_TRACKS})
    assets = (road_trip_before, years_playlist, discovery_before, TempusSessionAsset(username=OWNER, password="testpass123"))

    goal = (
        'Open Tempus, go to the music library, locate playlist "Road Trip Mix", and remove its first five songs. '
        'Add the first three songs from playlist "Years" to playlist "Discovery Playlist", then rename "Discovery Playlist" exactly to "Recommended Playlist". '
        'Star every song in "Recommended Playlist".'
    )

    def criteria(self):
        return [
            AssetModified(self.road_trip_before, self.road_trip_after, task=self),
            AssetModified(self.discovery_before, self.recommended_after, task=self),
            *[AssetExists(TempusFavoriteAsset(item_type="song", track_title=title, album_name=ALBUM, owner_username=OWNER), task=self) for title in FINAL_TRACKS],
        ]
