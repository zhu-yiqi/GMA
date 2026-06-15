from __future__ import annotations

from pathlib import Path
from gma.apps.xiaoshiliu import XIAOSHILIU_LOGIN_USER_ID
from gma.assets import DeviceFileAsset, ElementXMessageAsset, ElementXRoomAsset, ElementXUserAsset, ImageContentExpectation, MastodonBookmarkAsset, MastodonStatusAsset, XiaoShiLiuPostAsset
from gma.evaluation import AssetExists, AssetModified
from gma.tasks.base import BaseTask

BEFORE_TEXT = "Yesterday's question draft."
POST_TEXT = 'What would you do if the world ended tomorrow?'
IMAGE_FILENAME = 'learning-question.jpeg'
ROOM_ALIAS = 'w5-row253-posting-review'
GROUP_MESSAGE = 'Quickly go comment on the posts I just posted on Mastodon and XiaoShiLiu!'

class MastodonXslElementXEndWorldPostTask(BaseTask):
    apps = {'Mastodon', 'XiaoShiLiu', 'Gallery', 'ElementX'}
    difficulty = 'hard'
    category = []
    snapshot = 'gma_ready_state'

    before_status = MastodonStatusAsset(username='owner', text=BEFORE_TEXT, visibility='public')
    after_status = MastodonStatusAsset(username='owner', text=POST_TEXT, visibility='public')
    upload_image = DeviceFileAsset(app='Gallery', storage_dir='Pictures', filename=IMAGE_FILENAME, mime_type='image/jpeg', source_path=str(Path(__file__).with_name('assets') / IMAGE_FILENAME))
    expected_post = XiaoShiLiuPostAsset(author_user_id=XIAOSHILIU_LOGIN_USER_ID, title='Learning Check-in Question', content=POST_TEXT, category='Study', tags=['Learning Check-in'], min_image_count=1, expected_images=(ImageContentExpectation(source_path=str(Path(__file__).with_name('assets') / IMAGE_FILENAME)),))
    member = ElementXUserAsset(username='jordan-lee', password='password', display_name='Jordan Lee')
    room = ElementXRoomAsset(name='Posting Review Group', room_type='group', creator_username='testuser', creator_password='testpass123', members=['jordan-lee'], alias_localpart=ROOM_ALIAS, topic='Post review')
    assets = (before_status, upload_image, member, room)
    user_interaction = 'If ElementX has no existing group chat, create Posting Review Group with Jordan Lee and send the message there.'

    goal = (
        f'Open Mastodon and edit your post "{BEFORE_TEXT}" so its content is exactly "{POST_TEXT}", then bookmark that edited post. '
        f'Open XiaoShiLiu and create a post titled "Learning Check-in Question" with content "{POST_TEXT}", upload the latest image from Gallery, set category Study, and add the tag Learning Check-in. '
        f'Open ElementX, go to Posting Review Group, and send exactly "{GROUP_MESSAGE}".'
    )

    def criteria(self):
        return [
            AssetModified(self.before_status, self.after_status, task=self),
            AssetExists(MastodonBookmarkAsset(actor_username='owner', target_username='owner', target_text=POST_TEXT), task=self),
            AssetExists(self.expected_post, task=self),
            AssetExists(ElementXMessageAsset(room=ROOM_ALIAS, sender_username='testuser', sender_password='testpass123', text=GROUP_MESSAGE), task=self),
        ]
