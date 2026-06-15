from __future__ import annotations

from gma.apps.elementx import elementx_user_id
from gma.apps.meituan import MEITUAN_LOGIN_CITY, MEITUAN_LOGIN_USER_ID, MEITUAN_LOGIN_USERNAME
from gma.assets import (
    ElementXMessageAsset,
    ElementXRoomAsset,
    ElementXUserAsset,
    MattermostChannelAsset,
    MattermostPostAsset,
    MattermostSessionAsset,
    MattermostUserAsset,
    MeituanAddressAsset,
    MeituanOrderAsset,
    MeituanOrderFood,
    MeituanUserAsset,
)
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


SENDER = 'dinner-planner'
SECOND_CHANNEL = 'fried-chicken-plan'
ELEMENTX_USER = 'jordan-lee-dinner'
ELEMENTX_USER_ID = elementx_user_id(ELEMENTX_USER)
ELEMENTX_MESSAGE = 'Do you want to eat fried chicken? Ordered items: Air-fried rice cake; Four-in-one Chicken Strips, French Fries, Rice Cakes, and Yam Slices.'


class MattermostMeituanElementXFriedChickenOrderTask(BaseTask):
    apps = {'Mattermost', 'Meituan', 'ElementX'}
    difficulty = 'hard'
    snapshot = 'gma_ready_state'

    mattermost_user = MattermostUserAsset(username=SENDER, email='dinner.planner@example.com', first_name='Dinner', team='company', channel_memberships=['dinner-ideas', SECOND_CHANNEL])
    channels = (
        MattermostChannelAsset(team='company', name='dinner-ideas', display_name='Dinner Ideas', channel_type='O'),
        MattermostChannelAsset(team='company', name=SECOND_CHANNEL, display_name='Fried Chicken Plan', channel_type='O'),
    )
    session = MattermostSessionAsset(username=SENDER)
    meituan_user = MeituanUserAsset(username=MEITUAN_LOGIN_USERNAME, password='123456', user_id=MEITUAN_LOGIN_USER_ID, city=MEITUAN_LOGIN_CITY, status=1)
    expected_address = MeituanAddressAsset(user_id=MEITUAN_LOGIN_USER_ID, name='Carter', phone='5550101079', address='North Street', address_detail='Office', label='Office', gender='male', city=MEITUAN_LOGIN_CITY)
    expected_order = MeituanOrderAsset(
        user_id=MEITUAN_LOGIN_USER_ID,
        restaurant_name='Chicken Strips Lord',
        foods=[
            MeituanOrderFood(food_name='Air-fried rice cake', quantity=1),
            MeituanOrderFood(food_name='Four-in-one Chicken Strips, French Fries, Rice Cakes, and Yam Slices', quantity=1),
        ],
        status='Payment successful',
        address_name='Mr. Carter',
        code=200,
        delivery_status=1,
    )
    elementx_user = ElementXUserAsset(username=ELEMENTX_USER, password='password', display_name='Jordan Lee')
    assets = (*channels, mattermost_user, session, meituan_user, elementx_user)

    goal = (
        'Open Mattermost as dinner-planner and send exactly "What to eat for dinner?" in "Fried Chicken Plan". '
        'Then open Meituan, order one "Air-fried rice cake" and one "Four-in-one Chicken Strips, French Fries, Rice Cakes, and Yam Slices" from "Chicken Strips Lord", add a new Office-labeled delivery address for Mr. Carter, phone 5550101079, with Street set to North Street and Apt set to Office, and pay with Alipay. '
        f'Finally open ElementX, start a direct message with Jordan Lee, and send exactly "{ELEMENTX_MESSAGE}".'
    )

    def criteria(self):
        return [
            AssetExists(MattermostPostAsset(team='company', channel=SECOND_CHANNEL, username=SENDER, message='What to eat for dinner?'), task=self),
            AssetExists(self.expected_address, task=self),
            AssetExists(self.expected_order, task=self),
            AssetExists(ElementXRoomAsset(name='Jordan Lee', room_type='dm', creator_username='testuser', creator_password='testpass123', members=[ELEMENTX_USER]), task=self),
            AssetExists(ElementXMessageAsset(room=ELEMENTX_USER_ID, sender_username='testuser', sender_password='testpass123', text=ELEMENTX_MESSAGE), task=self),
        ]
