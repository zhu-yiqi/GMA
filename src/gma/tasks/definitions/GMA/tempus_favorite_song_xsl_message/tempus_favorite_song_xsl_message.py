from __future__ import annotations

from gma.apps.xiaoshiliu import XIAOSHILIU_DEFAULT_AVATAR, XIAOSHILIU_LOGIN_USER_ID
from gma.assets import ContactAsset, SmsMessageAsset, TempusPlaylistAsset, XiaoShiLiuCollectionAsset, XiaoShiLiuLikeAsset, XiaoShiLiuPostAsset, XiaoShiLiuUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


AUTHOR_ID = "w4-row216-review-author"
POSTS = (
    XiaoShiLiuPostAsset(author_user_id=AUTHOR_ID, title="The A Team Review One", content="The A Team by Ed Sheeran feels intimate and acoustic.", category="Music", tags=["The A Team", "review"], image_urls=["/assets/tempus-favorite-song-xsl-message-review-1.png"], min_image_count=1, created_at_ms=1790845800000),
    XiaoShiLiuPostAsset(author_user_id=AUTHOR_ID, title="The A Team Review Two", content="The A Team by Ed Sheeran works well for quiet study time.", category="Music", tags=["The A Team", "review"], image_urls=["/assets/tempus-favorite-song-xsl-message-review-2.png"], min_image_count=1, created_at_ms=1790845500000),
    XiaoShiLiuPostAsset(author_user_id=AUTHOR_ID, title="The A Team Review Three", content="The A Team by Ed Sheeran is the review I would save for later.", category="Music", tags=["The A Team", "review"], image_urls=["/assets/tempus-favorite-song-xsl-message-review-3.png"], min_image_count=1, created_at_ms=1790845200000),
)
DISTRACTOR_POSTS = (
    XiaoShiLiuPostAsset(author_user_id=AUTHOR_ID, title="Lego House Listening Notes", content="Lego House by Ed Sheeran has a warm chorus and a direct pop shape.", category="Music", tags=["Lego House", "review"], image_urls=["/assets/tempus-favorite-song-xsl-message-review-1.png"], min_image_count=1, created_at_ms=1790844900000),
    XiaoShiLiuPostAsset(author_user_id=AUTHOR_ID, title="Grade 8 Quick Review", content="Grade 8 by Ed Sheeran feels playful and bright in a short playlist.", category="Music", tags=["Grade 8", "review"], image_urls=["/assets/tempus-favorite-song-xsl-message-review-2.png"], min_image_count=1, created_at_ms=1790844600000),
    XiaoShiLiuPostAsset(author_user_id=AUTHOR_ID, title="In the Dark Listening Notes", content="In the Dark has a different mood from the acoustic Ed Sheeran tracks.", category="Music", tags=["In the Dark", "review"], image_urls=["/assets/tempus-favorite-song-xsl-message-review-3.png"], min_image_count=1, created_at_ms=1790844300000),
)
CONTACT = ContactAsset(name="Carter", phone_number="+15552160216")
SEED_SMS = SmsMessageAsset(address=CONTACT.phone_number, body="Please text me the song details when you finish.", box="inbox", read=True, timestamp_ms=202610010900)
EXPECTED_SMS = SmsMessageAsset(address=CONTACT.phone_number, body="I searched online for the song you mentioned: Song title: The A Team; Artist: Ed Sheeran.", box="sent", read=True)
EXPECTED_COLLECTIONS = tuple(XiaoShiLiuCollectionAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=post.title, post_author_user_id=AUTHOR_ID) for post in POSTS)
EXPECTED_LIKE = XiaoShiLiuLikeAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=POSTS[2].title, post_author_user_id=AUTHOR_ID)
SEEDED_COLLECTIONS = (
    XiaoShiLiuCollectionAsset(user_id="w4-row216-other-1", post_title=POSTS[0].title, post_author_user_id=AUTHOR_ID),
    XiaoShiLiuCollectionAsset(user_id="w4-row216-other-2", post_title=POSTS[1].title, post_author_user_id=AUTHOR_ID),
    XiaoShiLiuCollectionAsset(user_id="w4-row216-other-3", post_title=POSTS[1].title, post_author_user_id=AUTHOR_ID),
    XiaoShiLiuCollectionAsset(user_id="w4-row216-other-4", post_title=POSTS[2].title, post_author_user_id=AUTHOR_ID),
    XiaoShiLiuCollectionAsset(user_id="w4-row216-other-5", post_title=POSTS[2].title, post_author_user_id=AUTHOR_ID),
    XiaoShiLiuCollectionAsset(user_id="w4-row216-other-6", post_title=POSTS[2].title, post_author_user_id=AUTHOR_ID),
    XiaoShiLiuCollectionAsset(user_id="w4-row216-other-7", post_title=POSTS[2].title, post_author_user_id=AUTHOR_ID),
)

class TempusFavoriteSongXslMessageTask(BaseTask):
    apps = {"Tempus", "XiaoShiLiu", "Messages"}
    difficulty = "hard"
    snapshot = "gma_ready_state"
    assets = (
        TempusPlaylistAsset(name="My Favorites", owner_username="testuserfjx", visibility="private", track_titles=["The A Team", "Lego House"], track_albums={"The A Team": "+", "Lego House": "+"}),
        XiaoShiLiuUserAsset(user_id=AUTHOR_ID, nickname="Song Review Desk", email="song-review-row216@example.com", avatar=XIAOSHILIU_DEFAULT_AVATAR),
        *POSTS,
        *DISTRACTOR_POSTS,
        *SEEDED_COLLECTIONS,
        CONTACT,
        SEED_SMS,
    )
    goal = (
        'Open Tempus, view the playlist My Favorites, and read its first song title and artist. '
        'Then open XiaoShiLiu, search for that song title, save the first three matching review posts, and like the saved post with the most saves. '
        'Finally open Messages and send Carter a message in exactly this format: '
        '"I searched online for the song you mentioned: Song title: <song title>; Artist: <artist>."'
    )

    def criteria(self):
        return [
            *(AssetExists(collection, task=self) for collection in EXPECTED_COLLECTIONS),
            AssetExists(EXPECTED_LIKE, task=self),
            AssetExists(EXPECTED_SMS, task=self),
        ]
