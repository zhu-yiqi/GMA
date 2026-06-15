from __future__ import annotations

from gma.apps.elementx import elementx_user_id
from gma.apps.xiaoshiliu import XIAOSHILIU_DEFAULT_AVATAR, XIAOSHILIU_LOGIN_USER_ID
from gma.assets import (
    AlarmAsset,
    DeviceFileAsset,
    ElementXMessageAsset,
    ElementXRoomAsset,
    ElementXUserAsset,
    MailAccountAsset,
    MailAttachment,
    MailMessageAsset,
    MailReplyReference,
    XiaoShiLiuCollectionAsset,
    XiaoShiLiuPostAsset,
    XiaoShiLiuUserAsset,
)
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


FILE_NAME = 'resignation_letter.txt'
FILE_TEXT = 'Formal resignation letter draft.\n'
REPLY_BODY = 'Okay, I will attend on time.'
IMAGE_FILENAME = 'interview-prep.jpeg'
IMAGE_URL = f'/assets/{IMAGE_FILENAME}'
XSL_AUTHOR = 'w5-row248-interview-author'
POST_TITLE = 'Product Manager Intern Interview Experience'
ELEMENTX_USER = 'mia-foster-row248'
ELEMENTX_USER_ID = elementx_user_id(ELEMENTX_USER)

class MailXslElementXClockResignationInterviewTask(BaseTask):
    apps = {'Mail', 'Files', 'XiaoShiLiu', 'ElementX', 'Clock'}
    difficulty = 'hard'
    snapshot = 'gma_ready_state'

    source_file = DeviceFileAsset(app='Files', storage_dir='Download', filename=FILE_NAME, mime_type='text/plain', text_content=FILE_TEXT)
    account = MailAccountAsset(display_name='Nora Wilson', email='nora.wilson@example.com')
    expected_mail = MailMessageAsset(mailbox='sent', from_name=account.display_name, from_email='test@gmail.com', to=['asd@gmail.com'], subject='Resignation Letter', body='Please approve.', attachments=[MailAttachment(filename=FILE_NAME, mime_type='text/plain', text_content=FILE_TEXT)], read=True)
    interview_mail = MailMessageAsset(mailbox='inbox', from_name='Recruiting Team', from_email='recruiting@example.com', to=[account.email], subject='Interview for Product Manager Intern', body='The job position is Product Manager Intern.', read=False, timestamp_ms=202609301430)
    expected_reply = MailMessageAsset(mailbox='sent', from_name=account.display_name, from_email='test@gmail.com', to=['recruiting@example.com'], subject='RE: Interview for Product Manager Intern', body=REPLY_BODY, read=True, reply_to=MailReplyReference(from_email='recruiting@example.com', subject='Interview for Product Manager Intern'))
    xsl_author = XiaoShiLiuUserAsset(user_id=XSL_AUTHOR, nickname='Interview Coach Lee', email='w5-row248-interview-author@example.com', avatar=XIAOSHILIU_DEFAULT_AVATAR, bio='Interview preparation posts.', location='Seed Campus')
    xsl_post = XiaoShiLiuPostAsset(author_user_id=XSL_AUTHOR, title=POST_TITLE, content='A practical interview experience note for Product Manager Intern candidates.', category='Campus Life', tags=['interview', 'career'], image_urls=[IMAGE_URL], min_image_count=1)
    elementx_user = ElementXUserAsset(username=ELEMENTX_USER, password='password', display_name='Mia Foster')
    expected_alarm = AlarmAsset(
        hour=14,
        minute=0,
        enabled=True,
        scheduled_year=2026,
        scheduled_month=10,
        scheduled_day=2,
    )
    assets = (source_file, account, interview_mail, xsl_author, xsl_post, elementx_user)

    goal = (
        f'Open Mail and send asd@gmail.com an email with subject "Resignation Letter", body "Please approve.", and attach "{FILE_NAME}". Then reply to the interview email for Product Manager Intern with exactly "{REPLY_BODY}". '
        f'Open XiaoShiLiu and save the post titled "{POST_TITLE}". Open ElementX, start a direct message with Mia Foster, and send exactly "I\'ve resigned." Finally set a Clock alarm for 2:00 PM tomorrow.'
    )

    def criteria(self):
        return [
            AssetExists(self.expected_mail, task=self),
            AssetExists(self.expected_reply, task=self),
            AssetExists(XiaoShiLiuCollectionAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=POST_TITLE, post_author_user_id=XSL_AUTHOR), task=self),
            AssetExists(ElementXRoomAsset(name='Mia Foster', room_type='dm', creator_username='testuser', creator_password='testpass123', members=[ELEMENTX_USER]), task=self),
            AssetExists(ElementXMessageAsset(room=ELEMENTX_USER_ID, sender_username='testuser', sender_password='testpass123', text="I've resigned."), task=self),
            AssetExists(self.expected_alarm, task=self),
        ]
