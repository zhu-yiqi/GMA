from __future__ import annotations

from gma.assets import ContactAsset, SmsMessageAsset, TempusFavoriteAsset, TempusPlaylistAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask

CASEY_MIX = TempusPlaylistAsset(name="Casey Mix", owner_username="testuserfjx", visibility="private", track_titles=["The A Team", "Lego House"], track_albums={"The A Team": "+", "Lego House": "+"})
MORGAN_MIX = TempusPlaylistAsset(name="Morgan Mix", owner_username="testuserfjx", visibility="private", track_titles=["Lego House", "Grade 8"], track_albums={"Lego House": "+", "Grade 8": "+"})
FAVORITE = TempusFavoriteAsset(item_type="song", track_title="Lego House", owner_username="testuserfjx")
CONTACT = ContactAsset(name="Casey Morgan", phone_number="+15550100860")
EXPECTED_SMS = SmsMessageAsset(address="+15550100860", body="I have found the song. Song name: Lego House; Liked: yes.", box="sent", read=True)


class TempusCommonSongMessageCaseyMorganTask(BaseTask):
    apps = {"Tempus", "Messages"}
    difficulty = "hard"
    snapshot = "gma_ready_state"
    assets = (CASEY_MIX, MORGAN_MIX, FAVORITE, CONTACT)
    goal = (
        'Open Tempus, compare playlists Casey Mix and Morgan Mix, find a song that appears in both, and check whether it is liked. '
        'Then open Messages and send Casey Morgan a message in exactly this format: "I have found the song. Song name: <song name>; Liked: <yes/no>."'
    )

    def criteria(self):
        return [AssetExists(EXPECTED_SMS, task=self)]
