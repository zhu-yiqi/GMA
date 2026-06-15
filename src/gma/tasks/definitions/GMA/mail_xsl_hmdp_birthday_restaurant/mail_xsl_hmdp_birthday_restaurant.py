from __future__ import annotations

from gma.apps.hmdp import HMDP_LOGIN_NICKNAME, HMDP_LOGIN_PASSWORD, HMDP_LOGIN_PHONE
from gma.apps.xiaoshiliu import XIAOSHILIU_DEFAULT_AVATAR, XIAOSHILIU_LOGIN_USER_ID
from gma.assets import (
    DeviceFileAsset,
    HmdpShopFavoriteAsset,
    HmdpUserAsset,
    MailAccountAsset,
    MailAttachment,
    MailMessageAsset,
    XiaoShiLiuCollectionAsset,
    XiaoShiLiuPostAsset,
    XiaoShiLiuUserAsset,
)
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


INVITE_NAME = 'invitation.txt'
INVITE_TEXT = 'You are invited to the birthday party.\n'
IMAGE_FILENAME = 'birthday-restaurant.jpeg'
IMAGE_URL = f'/assets/{IMAGE_FILENAME}'
XSL_AUTHOR = 'w5-row246-birthday-author'
POST_TITLE = 'Birthday Dinner Restaurant Shortlist'
SHOP_NAME = 'Maple Leaf Bar'

class MailXslHmdpBirthdayRestaurantTask(BaseTask):
    apps = {'Mail', 'Files', 'XiaoShiLiu', 'HMDP'}
    difficulty = 'hard'
    snapshot = 'gma_ready_state'

    invitation_file = DeviceFileAsset(app='Files', storage_dir='Download', filename=INVITE_NAME, mime_type='text/plain', text_content=INVITE_TEXT)
    account = MailAccountAsset(display_name='Riley Carter', email='riley.carter@example.com')
    expected_mail = MailMessageAsset(mailbox='sent', from_name=account.display_name, from_email='test@gmail.com', to=['mncjd@gmail.com'], subject='Birthday Party', body='Welcome everyone to my party!', attachments=[MailAttachment(filename=INVITE_NAME, mime_type='text/plain', text_content=INVITE_TEXT)], read=True)
    xsl_author = XiaoShiLiuUserAsset(user_id=XSL_AUTHOR, nickname='Birthday Planner Riley', email='w5-row246-birthday-author@example.com', avatar=XIAOSHILIU_DEFAULT_AVATAR, bio='Birthday dinner planning notes.', location='Seed Campus')
    xsl_post = XiaoShiLiuPostAsset(author_user_id=XSL_AUTHOR, title=POST_TITLE, content='A concise shortlist of cozy restaurants for a small birthday dinner.', category='Food', tags=['birthday', 'restaurant'], image_urls=[IMAGE_URL], min_image_count=1)
    hmdp_user = HmdpUserAsset(phone=HMDP_LOGIN_PHONE, password=HMDP_LOGIN_PASSWORD, nick_name=HMDP_LOGIN_NICKNAME, city='Austin', level=1)
    expected_favorite = HmdpShopFavoriteAsset(user_phone=HMDP_LOGIN_PHONE, shop_name=SHOP_NAME)
    assets = (invitation_file, account, xsl_author, xsl_post, hmdp_user)

    goal = (
        f'Open Mail and send mncjd@gmail.com an email with subject "Birthday Party", body "Welcome everyone to my party!", and attach "{INVITE_NAME}" from Downloads. '
        f'Then open XiaoShiLiu and save the post titled "{POST_TITLE}". Finally open HMDP, find "{SHOP_NAME}", and favorite it.'
    )

    def criteria(self):
        return [
            AssetExists(self.expected_mail, task=self),
            AssetExists(XiaoShiLiuCollectionAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=POST_TITLE, post_author_user_id=XSL_AUTHOR), task=self),
            AssetExists(self.expected_favorite, task=self),
        ]
