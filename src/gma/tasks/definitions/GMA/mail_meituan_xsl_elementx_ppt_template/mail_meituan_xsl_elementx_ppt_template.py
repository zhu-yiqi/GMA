from __future__ import annotations

from gma.apps.elementx import elementx_user_id
from gma.apps.meituan import MEITUAN_LOGIN_CITY, MEITUAN_LOGIN_USER_ID, MEITUAN_LOGIN_USERNAME
from gma.apps.xiaoshiliu import XIAOSHILIU_DEFAULT_AVATAR, XIAOSHILIU_LOGIN_USER_ID
from gma.assets import (
    ElementXMessageAsset,
    ElementXRoomAsset,
    ElementXUserAsset,
    MailAccountAsset,
    MailMessageAsset,
    MailReplyReference,
    MeituanAddressAsset,
    MeituanOrderAsset,
    MeituanOrderFood,
    MeituanUserAsset,
    XiaoShiLiuCollectionAsset,
    XiaoShiLiuLikeAsset,
    XiaoShiLiuPostAsset,
    XiaoShiLiuUserAsset,
)
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


REPLY_BODY = 'Received, thanks.'
XSL_AUTHOR = 'w5-row249-ppt-author'
XSL_AUTHOR_NAME = 'Template Maker Nora'
POST_TITLE = 'Universal PPT Template Clean Layout'
IMAGE_FILENAME = 'ppt-template.jpeg'
IMAGE_URL = f'/assets/{IMAGE_FILENAME}'
ELEMENTX_USER = 'riley-park-ppt'
ELEMENTX_USER_ID = elementx_user_id(ELEMENTX_USER)
SECOND_MESSAGE = "I think this author's PPT templates are quite good. You should check them out."

class MailMeituanXslElementXPptTemplateTask(BaseTask):
    apps = {'Mail', 'Meituan', 'XiaoShiLiu', 'ElementX'}
    difficulty = 'hard'
    category = ['Multi-Step Workflow Tasks']
    snapshot = 'gma_ready_state'

    account = MailAccountAsset(display_name='Avery Morgan', email='avery.morgan@example.com')
    event_mail = MailMessageAsset(mailbox='inbox', from_name='Event Planner', from_email='event.planner@example.com', to=[account.email], subject='Event plan final draft', body='Please confirm the final event plan.', read=False, timestamp_ms=202609301200)
    expected_reply = MailMessageAsset(mailbox='sent', from_name=account.display_name, from_email='test@gmail.com', to=['event.planner@example.com'], subject='RE: Event plan final draft', body=REPLY_BODY, read=True, reply_to=MailReplyReference(from_email='event.planner@example.com', subject='Event plan final draft'))
    expected_mail = MailMessageAsset(mailbox='sent', from_name=account.display_name, from_email='test@gmail.com', to=['xcv@gmail.com'], subject='Meeting Arrangement', body='Please attend on time.', read=True)
    meituan_user = MeituanUserAsset(username=MEITUAN_LOGIN_USERNAME, password='123456', user_id=MEITUAN_LOGIN_USER_ID, city=MEITUAN_LOGIN_CITY, status=1)
    default_address = MeituanAddressAsset(user_id=MEITUAN_LOGIN_USER_ID, name='Company Office Receiver', phone='5550101060', address='Company Office', address_detail='Room 901', label='Office', gender='male', city=MEITUAN_LOGIN_CITY)
    expected_order = MeituanOrderAsset(user_id=MEITUAN_LOGIN_USER_ID, restaurant_name='CHAGEE', foods=[MeituanOrderFood(food_name='boya vast string', quantity=10), MeituanOrderFood(food_name='Qingqing Nuoshan', quantity=10)], status='Payment successful', address_name='Company Office Receiver', code=200, delivery_status=1)
    xsl_author = XiaoShiLiuUserAsset(user_id=XSL_AUTHOR, nickname=XSL_AUTHOR_NAME, email='nora.templates@example.com', avatar=XIAOSHILIU_DEFAULT_AVATAR, bio='Presentation template notes.', location='Seed Campus')
    xsl_post = XiaoShiLiuPostAsset(author_user_id=XSL_AUTHOR, title=POST_TITLE, content='A clean universal PPT template planning note.', category='Study', tags=['ppt', 'template'], image_urls=[IMAGE_URL], min_image_count=1)
    elementx_user = ElementXUserAsset(username=ELEMENTX_USER, password='password', display_name='Riley Park')
    assets = (account, event_mail, meituan_user, default_address, xsl_author, xsl_post, elementx_user)

    goal = (
        f'Open Mail and reply to the event plan email with exactly "{REPLY_BODY}". Then send xcv@gmail.com an email with subject "Meeting Arrangement" and body "Please attend on time." '
        'Open Meituan and order 10 "boya vast string" and 10 "Qingqing Nuoshan" from CHAGEE using the default Office address, and pay with Alipay. '
        f'Open XiaoShiLiu, like and save the post titled "{POST_TITLE}", and note the post author. Open ElementX, start a direct message with Riley Park, send exactly the author name you found, then send exactly "{SECOND_MESSAGE}".'
    )

    def criteria(self):
        return [
            AssetExists(self.expected_reply, task=self),
            AssetExists(self.expected_mail, task=self),
            AssetExists(self.expected_order, task=self),
            AssetExists(XiaoShiLiuLikeAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=POST_TITLE, post_author_user_id=XSL_AUTHOR), task=self),
            AssetExists(XiaoShiLiuCollectionAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=POST_TITLE, post_author_user_id=XSL_AUTHOR), task=self),
            AssetExists(ElementXRoomAsset(name='Riley Park', room_type='dm', creator_username='testuser', creator_password='testpass123', members=[ELEMENTX_USER]), task=self),
            AssetExists(ElementXMessageAsset(room=ELEMENTX_USER_ID, sender_username='testuser', sender_password='testpass123', text=XSL_AUTHOR_NAME), task=self),
            AssetExists(ElementXMessageAsset(room=ELEMENTX_USER_ID, sender_username='testuser', sender_password='testpass123', text=SECOND_MESSAGE), task=self),
        ]
