from __future__ import annotations

from gma.apps.meituan import MEITUAN_LOGIN_CITY, MEITUAN_LOGIN_USER_ID, MEITUAN_LOGIN_USERNAME
from gma.assets import (
    AlarmAsset,
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
)
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


ROOM_ALIAS = 'w5-row247-family-day-group'
FIRST_MESSAGE = "I'll bring fried chicken tomorrow."
SECOND_MESSAGE = '@room Order details: 3 Zinger burger and 5 Mexican chicken rolls. What about you?'
REPLY_BODY = 'OK, I will attend on time.'


class MailMeituanElementXClockFamilyDayTask(BaseTask):
    apps = {'Mail', 'Meituan', 'ElementX', 'Clock'}
    difficulty = 'hard'
    snapshot = 'gma_ready_state'

    account = MailAccountAsset(display_name='Riley Cooper', email='riley.cooper@example.com')
    old_mail = MailMessageAsset(mailbox='inbox', from_name='School Office', from_email='school.office@example.com', to=[account.email], subject='School Family Day Details', body='Earlier family day details.', read=True, timestamp_ms=202609300900)
    latest_mail = MailMessageAsset(mailbox='inbox', from_name='School Office', from_email='school.office@example.com', to=[account.email], subject='School Family Day Final Notice', body='Please confirm attendance for school family day.', read=False, timestamp_ms=202609301000)
    expected_reply = MailMessageAsset(mailbox='sent', from_name=account.display_name, from_email='test@gmail.com', to=['school.office@example.com'], subject='RE: School Family Day Final Notice', body=REPLY_BODY, read=True, reply_to=MailReplyReference(from_email='school.office@example.com', subject='School Family Day Final Notice'))
    meituan_user = MeituanUserAsset(username=MEITUAN_LOGIN_USERNAME, password='123456', user_id=MEITUAN_LOGIN_USER_ID, city=MEITUAN_LOGIN_CITY, status=1)
    default_address = MeituanAddressAsset(user_id=MEITUAN_LOGIN_USER_ID, name='Default Office Receiver', phone='5550101059', address='Default Office', address_detail='Room 701', label='Office', gender='male', city=MEITUAN_LOGIN_CITY)
    expected_order = MeituanOrderAsset(user_id=MEITUAN_LOGIN_USER_ID, restaurant_name='Jishengke', foods=[MeituanOrderFood(food_name='Zinger burger', quantity=3), MeituanOrderFood(food_name='Mexican chicken rolls', quantity=5)], status='Payment successful', address_name='Default Office Receiver', code=200, delivery_status=1)
    group_member = ElementXUserAsset(username='w5-row247-group-member', password='password', display_name='Family Day Group Member')
    group_room = ElementXRoomAsset(name='Family Day Group', room_type='group', creator_username='testuser', creator_password='testpass123', members=['w5-row247-group-member'], alias_localpart=ROOM_ALIAS, topic='Family day food coordination')
    expected_alarm = AlarmAsset(hour=9, minute=0, enabled=True, vibrate=False)
    assets = (account, old_mail, latest_mail, meituan_user, default_address, group_member, group_room)

    goal = (
        f'Open Mail and reply to the newest school family day email with exactly "{REPLY_BODY}". Then open Meituan and order 3 "Zinger burger" and 5 "Mexican chicken rolls" from Jishengke using the default Office address, and pay with Alipay. '
        f'Open ElementX, go to "Family Day Group", send exactly "{FIRST_MESSAGE}", then send exactly "{SECOND_MESSAGE}". Finally open Clock and set a 9:00 AM alarm with vibration off.'
    )

    def criteria(self):
        return [
            AssetExists(self.expected_reply, task=self),
            AssetExists(self.expected_order, task=self),
            AssetExists(ElementXMessageAsset(room=ROOM_ALIAS, sender_username='testuser', sender_password='testpass123', text=FIRST_MESSAGE), task=self),
            AssetExists(ElementXMessageAsset(room=ROOM_ALIAS, sender_username='testuser', sender_password='testpass123', text=SECOND_MESSAGE, mentions_room=True), task=self),
            AssetExists(self.expected_alarm, task=self),
        ]
