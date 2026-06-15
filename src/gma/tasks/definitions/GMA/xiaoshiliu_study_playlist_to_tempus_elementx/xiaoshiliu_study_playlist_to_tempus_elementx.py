from __future__ import annotations

from gma.apps.xiaoshiliu import XIAOSHILIU_DEFAULT_AVATAR, XIAOSHILIU_LOGIN_USER_ID
from gma.assets import ElementXMessageAsset, ElementXRoomAsset, ElementXUserAsset, TempusPlaylistAsset, XiaoShiLiuCollectionAsset, XiaoShiLiuPostAsset, XiaoShiLiuUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


AUTHOR_ID = "w4-row203-playlist-curator"
ROOM_ALIAS = "w4-row203-study-group"
ROOM_NAME = "Study Group"
SONGS = ["The A Team", "Lego House", "Grade 8"]
SEARCH_PHRASE = "Cedar Library Study Playlist"
PRIMARY_TITLE = f"{SEARCH_PHRASE}: Main Track List"
IMAGE_FILENAME = "xiaoshiliu-study-playlist-to-tempus-elementx-library-playlist.png"
IMAGE_URL = f"/assets/{IMAGE_FILENAME}"
POST_TITLES = (
    PRIMARY_TITLE,
    f"{SEARCH_PHRASE}: Quiet Homework Songs",
    f"{SEARCH_PHRASE}: Evening Reading Mix",
    f"{SEARCH_PHRASE}: Focus Desk Playlist",
    f"{SEARCH_PHRASE}: Exam Review Tracks",
    f"{SEARCH_PHRASE}: Lo-Fi Walk to Class",
    f"{SEARCH_PHRASE}: Paper Draft Soundtrack",
    f"{SEARCH_PHRASE}: Late Night Notes Mix",
    f"{SEARCH_PHRASE}: Morning Problem Set Songs",
    f"{SEARCH_PHRASE}: Weekend Study Rotation",
)
AUTHOR = XiaoShiLiuUserAsset(user_id=AUTHOR_ID, nickname="Playlist Curator", email="playlist.curator@example.com", avatar=XIAOSHILIU_DEFAULT_AVATAR)
POSTS = tuple(
    XiaoShiLiuPostAsset(
        author_user_id=AUTHOR_ID,
        title=title,
        content=("Songs: The A Team; Lego House; Grade 8." if index == 0 else f"A Cedar Library study playlist note number {index + 1} for quiet homework sessions."),
        category="Music",
        tags=["study playlist", "music"],
        image_urls=[IMAGE_URL],
        min_image_count=1,
        created_at_ms=1790845200000 - index * 60000,
    )
    for index, title in enumerate(POST_TITLES)
)
EXPECTED_COLLECTIONS = tuple(XiaoShiLiuCollectionAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=title, post_author_user_id=AUTHOR_ID) for title in POST_TITLES)
EXPECTED_PLAYLIST = TempusPlaylistAsset(name="Study Playlist", owner_username="testuserfjx", track_titles=SONGS, track_albums={"The A Team": "+", "Lego House": "+", "Grade 8": "+"})
EXPECTED_MESSAGE = ElementXMessageAsset(room=ROOM_ALIAS, sender_username="testuser", sender_password="testpass123", text="I found a playlist suitable for studying.")

class XiaoShiLiuStudyPlaylistToTempusElementXTask(BaseTask):
    apps = {"XiaoShiLiu", "Tempus", "ElementX"}
    difficulty = "hard"
    snapshot = "gma_ready_state"
    assets = (AUTHOR, *POSTS, ElementXUserAsset(username="w4-row203-study-partner", display_name="Study Partner"), ElementXRoomAsset(name=ROOM_NAME, room_type="group", creator_username="testuser", creator_password="testpass123", members=["w4-row203-study-partner"], alias_localpart=ROOM_ALIAS))
    goal = (
        f"Open XiaoShiLiu, search for \"{SEARCH_PHRASE}\", and save every note shown in the search results. "
        f"Read all song titles from \"{PRIMARY_TITLE}\". "
        "Then open Tempus, create a playlist named \"Study Playlist\", add those songs from Ed Sheeran's + album, "
        "and open ElementX to send \"I found a playlist suitable for studying.\" in Study Group."
    )

    def criteria(self):
        return [*(AssetExists(asset, task=self) for asset in EXPECTED_COLLECTIONS), AssetExists(EXPECTED_PLAYLIST, task=self), AssetExists(EXPECTED_MESSAGE, task=self)]
