from __future__ import annotations

from gma.apps.elementx import elementx_user_id
from gma.assets import DeviceFileAsset, ElementXFileAsset, ElementXMessageAsset, ElementXRoomAsset, ElementXUserAsset, TravelAttractionBookingAsset, TravelFavoriteAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask
from datetime import UTC, datetime

from gma.apps.travel import (
    TRAVEL_LOGIN_EMAIL,
    TRAVEL_LOGIN_FIRST_NAME,
    TRAVEL_LOGIN_LAST_NAME,
    TRAVEL_LOGIN_PASSWORD,
    TRAVEL_LOGIN_USERNAME,
    login_travel_app,
)
from gma.assets import TravelUserAsset

TRAVEL_USER = TravelUserAsset(
    email=TRAVEL_LOGIN_EMAIL,
    username=TRAVEL_LOGIN_USERNAME,
    password=TRAVEL_LOGIN_PASSWORD,
    first_name=TRAVEL_LOGIN_FIRST_NAME,
    last_name=TRAVEL_LOGIN_LAST_NAME,
)


def dt_ms(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> int:
    return int(datetime(year, month, day, hour, minute, tzinfo=UTC).timestamp() * 1000)


def open_travel(client) -> None:
    login_travel_app(
        client,
        email=TRAVEL_LOGIN_EMAIL,
        username=TRAVEL_LOGIN_USERNAME,
        password=TRAVEL_LOGIN_PASSWORD,
        ensure_user=False,
    )

INVITE = 'invitation.txt'
INVITE_TEXT = 'Kiyomizu-dera Temple invitation for October 12.\n'
DM_USER = 'w5-row273-dm-friend'
DM_ROOM = elementx_user_id(DM_USER)
GROUP_ALIAS = 'w5-row273-weekend-group'
DM_MESSAGE = "I've bought two Kiyomizu-dera Temple tickets for October 12-let's go together!"
GROUP_MESSAGE = 'What gift should I bring for the October 12 visit?'

class TravelElementXKiyomizuInvitationTask(BaseTask):
    apps = {'Travel', 'ElementX', 'Files'}
    difficulty = 'hard'
    snapshot = 'gma_ready_state'

    booking = TravelAttractionBookingAsset(user_email=TRAVEL_USER.email, attraction_name='Kiyomizu-dera Temple', attraction_slug='kiyomizu-dera-temple-kyoto', visit_date_ms=dt_ms(2026,10,12,9), adult_tickets=2, child_tickets=0, visitors=[{'firstName':'Jordan','lastName':'Miller','type':'adult'}, {'firstName':'Ryan','lastName':'Walker','type':'adult'}], booking_status='confirmed', payment_status='paid')
    favorite = TravelFavoriteAsset(user_email=TRAVEL_USER.email, target='attraction', attraction_name='Kiyomizu-dera Temple', attraction_slug='kiyomizu-dera-temple-kyoto')
    invite_file = DeviceFileAsset(app='Files', storage_dir='Download', filename=INVITE, mime_type='text/plain', text_content=INVITE_TEXT)
    dm_user = ElementXUserAsset(username=DM_USER, password='password', display_name='Weekend Friend')
    group_member = ElementXUserAsset(username='w5-row273-group-member', password='password', display_name='Weekend Group Member')
    group = ElementXRoomAsset(name='Weekend Planning Group', room_type='group', creator_username='testuser', creator_password='testpass123', members=['w5-row273-group-member'], alias_localpart=GROUP_ALIAS, topic='Weekend gifts')
    assets = (TRAVEL_USER, invite_file, dm_user, group_member, group)
    user_interaction = 'If the agent asks for visitor names, use Jordan Miller and Ryan Walker.'

    goal = f'Open Travel and buy two adult tickets for Kiyomizu-dera Temple on October 12, 2026 for Jordan Miller and Ryan Walker, complete payment so the attraction booking is confirmed, then favorite the attraction. Open ElementX, send Weekend Friend exactly "{DM_MESSAGE}" and attach "{INVITE}". Then send Weekend Planning Group exactly "{GROUP_MESSAGE}".'

    def setup(self, client) -> None:
        open_travel(client)

    def criteria(self):
        return [
            AssetExists(self.booking, task=self),
            AssetExists(self.favorite, task=self),
            AssetExists(ElementXRoomAsset(name='Weekend Friend', room_type='dm', creator_username='testuser', creator_password='testpass123', members=[DM_USER]), task=self),
            AssetExists(ElementXMessageAsset(room=DM_ROOM, sender_username='testuser', sender_password='testpass123', text=DM_MESSAGE), task=self),
            AssetExists(ElementXFileAsset(room=DM_ROOM, sender_username='testuser', sender_password='testpass123', filename=INVITE, mime_type='text/plain', text_content=INVITE_TEXT), task=self),
            AssetExists(ElementXMessageAsset(room=GROUP_ALIAS, sender_username='testuser', sender_password='testpass123', text=GROUP_MESSAGE), task=self),
        ]
