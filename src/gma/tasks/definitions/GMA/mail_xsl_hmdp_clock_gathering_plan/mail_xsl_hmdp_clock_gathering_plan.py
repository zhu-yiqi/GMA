from __future__ import annotations

from gma.apps.hmdp import HMDP_LOGIN_NICKNAME, HMDP_LOGIN_PASSWORD, HMDP_LOGIN_PHONE
from gma.apps.xiaoshiliu import XIAOSHILIU_DEFAULT_AVATAR, XIAOSHILIU_LOGIN_USER_ID
from gma.assets import AlarmAsset, HmdpShopFavoriteAsset, HmdpUserAsset, MailAccountAsset, MailMessageAsset, XiaoShiLiuCollectionAsset, XiaoShiLiuPostAsset, XiaoShiLiuUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


IMAGE_FILENAME = 'gathering-games.jpeg'
IMAGE_URL = f'/assets/{IMAGE_FILENAME}'
XSL_AUTHOR = 'w5-row250-gathering-author'
POST_TITLE = 'Gathering Games First Pick'
SHOP_NAME = 'Maple Leaf Bar'
MAIL_BODY = 'Start at 11 a.m. tomorrow.'

class MailXslHmdpClockGatheringPlanTask(BaseTask):
    apps = {'Mail', 'XiaoShiLiu', 'HMDP', 'Clock'}
    difficulty = 'hard'
    snapshot = 'gma_ready_state'

    account = MailAccountAsset(display_name='Nora Brooks', email='nora.brooks@example.com')
    expected_mail = MailMessageAsset(mailbox='sent', from_name=account.display_name, from_email='test@gmail.com', to=['xsw@gmail.com'], subject='Gathering', body=MAIL_BODY, read=True)
    xsl_author = XiaoShiLiuUserAsset(user_id=XSL_AUTHOR, nickname='Gathering Games Nora', email='nora.gathering@example.com', avatar=XIAOSHILIU_DEFAULT_AVATAR, bio='Party game notes.', location='Seed Campus')
    xsl_post = XiaoShiLiuPostAsset(author_user_id=XSL_AUTHOR, title=POST_TITLE, content=f'A gathering games shortlist that recommends {SHOP_NAME} as the first karaoke lounge to check.', category='Campus Life', tags=['gathering', 'games'], image_urls=[IMAGE_URL], min_image_count=1)
    hmdp_user = HmdpUserAsset(phone=HMDP_LOGIN_PHONE, password=HMDP_LOGIN_PASSWORD, nick_name=HMDP_LOGIN_NICKNAME, city='Austin', level=1)
    expected_alarm = AlarmAsset(
        hour=9,
        minute=0,
        enabled=True,
        scheduled_year=2026,
        scheduled_month=10,
        scheduled_day=2,
    )
    assets = (account, xsl_author, xsl_post, hmdp_user)

    goal = (
        f'Open Mail and send xsw@gmail.com an email with subject "Gathering" and body "{MAIL_BODY}". '
        f'Then open XiaoShiLiu, find and save the post titled "{POST_TITLE}". Read which shop the post recommends, then open HMDP and favorite that shop. '
        'Finally open Clock and set an enabled alarm for 9:00 AM tomorrow.'
    )

    def criteria(self):
        return [
            AssetExists(self.expected_mail, task=self),
            AssetExists(XiaoShiLiuCollectionAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=POST_TITLE, post_author_user_id=XSL_AUTHOR), task=self),
            AssetExists(HmdpShopFavoriteAsset(user_phone=HMDP_LOGIN_PHONE, shop_name=SHOP_NAME), task=self),
            AssetExists(self.expected_alarm, task=self),
        ]
