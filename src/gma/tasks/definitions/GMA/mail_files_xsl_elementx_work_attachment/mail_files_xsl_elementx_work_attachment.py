from __future__ import annotations

from gma.apps.xiaoshiliu import XIAOSHILIU_DEFAULT_AVATAR, XIAOSHILIU_LOGIN_USER_ID
from gma.assets import (
    DeviceFileAsset,
    ElementXFileAsset,
    ElementXMessageAsset,
    ElementXRoomAsset,
    ElementXUserAsset,
    MailAccountAsset,
    MailAttachment,
    MailMessageAsset,
    XiaoShiLiuLikeAsset,
    XiaoShiLiuPostAsset,
    XiaoShiLiuUserAsset,
)
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


ATTACHMENT_NAME = 'work-brief-first.txt'
ATTACHMENT_TEXT = 'Work attachment for the first inbox item.\n'
IMAGE_FILENAME = 'file-organizing.jpeg'
IMAGE_URL = f'/assets/{IMAGE_FILENAME}'
XSL_AUTHOR = 'w5-row245-file-author'
TARGET_TITLE = 'Quick File Sorting Third Tip'
ROOM_ALIAS = 'w5-row245-attachment-review'

class MailFilesXslElementXWorkAttachmentTask(BaseTask):
    apps = {'Mail', 'Files', 'XiaoShiLiu', 'ElementX'}
    difficulty = 'hard'
    category = ['Multi-Step Workflow Tasks']
    snapshot = 'gma_ready_state'

    account = MailAccountAsset(display_name='Work Attachment User', email='work.attachment.user@example.com')
    first_mail = MailMessageAsset(mailbox='inbox', from_name='Work Sender One', from_email='work.sender.one@example.com', to=[account.email], subject='Work attachment package A', body='Use the first work attachment.', attachments=[MailAttachment(filename=ATTACHMENT_NAME, mime_type='text/plain', text_content=ATTACHMENT_TEXT)], read=True)
    second_mail = MailMessageAsset(mailbox='inbox', from_name='Work Sender Two', from_email='work.sender.two@example.com', to=[account.email], subject='Work attachment package B', body='Decoy work attachment.', attachments=[MailAttachment(filename='work-brief-second.txt', mime_type='text/plain', text_content='Second attachment.\n')], read=True)
    expected_file = DeviceFileAsset(app='Files', storage_dir='Download', filename=ATTACHMENT_NAME, mime_type='text/plain', text_content=ATTACHMENT_TEXT)
    expected_mail = MailMessageAsset(mailbox='sent', from_name=account.display_name, from_email='test@gmail.com', to=['mncjd@gmail.com'], subject='Work', body='Please check', attachments=[MailAttachment(filename=ATTACHMENT_NAME, mime_type='text/plain', text_content=ATTACHMENT_TEXT)], read=True)
    xsl_author = XiaoShiLiuUserAsset(user_id=XSL_AUTHOR, nickname='File Organizer Sam', email='w5-row245-file-author@example.com', avatar=XIAOSHILIU_DEFAULT_AVATAR, bio='File organization notes.', location='Seed Campus')
    xsl_posts = tuple(XiaoShiLiuPostAsset(author_user_id=XSL_AUTHOR, title=title, content='A practical file organization tip.', category='Study', tags=['files', 'organization'], image_urls=[IMAGE_URL], min_image_count=1) for title in ['Quick File Sorting First Tip', 'Quick File Sorting Second Tip', TARGET_TITLE])
    group_member = ElementXUserAsset(username='w5-row245-group-member', password='password', display_name='Attachment Review Member')
    group_room = ElementXRoomAsset(name='Attachment Review Group', room_type='group', creator_username='testuser', creator_password='testpass123', members=['w5-row245-group-member'], alias_localpart=ROOM_ALIAS, topic='Attachment review')
    assets = (account, first_mail, second_mail, xsl_author, *xsl_posts, group_member, group_room)
    user_interaction = 'If the agent asks which work attachment email to use, respond: Use the first work attachment email.'

    goal = (
        f'Open Mail, download the attachment "{ATTACHMENT_NAME}" from the first work attachment email, then send mncjd@gmail.com an email with subject "Work", body "Please check", and attach that downloaded file. '
        f'Open XiaoShiLiu and like the post titled "{TARGET_TITLE}". Then open ElementX, go to "Attachment Review Group", send exactly "Please check", and upload "{ATTACHMENT_NAME}".'
    )

    def criteria(self):
        return [
            AssetExists(self.expected_file, task=self),
            AssetExists(self.expected_mail, task=self),
            AssetExists(XiaoShiLiuLikeAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=TARGET_TITLE, post_author_user_id=XSL_AUTHOR), task=self),
            AssetExists(ElementXMessageAsset(room=ROOM_ALIAS, sender_username='testuser', sender_password='testpass123', text='Please check'), task=self),
            AssetExists(ElementXFileAsset(room=ROOM_ALIAS, sender_username='testuser', sender_password='testpass123', filename=ATTACHMENT_NAME, mime_type='text/plain', text_content=ATTACHMENT_TEXT), task=self),
        ]
