from __future__ import annotations

from gma.apps.xiaoshiliu import XIAOSHILIU_DEFAULT_AVATAR, XIAOSHILIU_LOGIN_USER_ID
from gma.assets import (
    MattermostChannelAsset,
    MattermostChannelMembershipAsset,
    MattermostPostAsset,
    MattermostSessionAsset,
    MattermostUserAsset,
    XiaoShiLiuCommentAsset,
    XiaoShiLiuLikeAsset,
    XiaoShiLiuPostAsset,
    XiaoShiLiuUserAsset,
)
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


SENDER = 'style-coordinator'
BOB = 'bob'
COMMENT = 'I love your style! Could you please share where you bought this?'
IMAGE_FILENAME = 'outfit-style.jpeg'
IMAGE_URL = f'/assets/{IMAGE_FILENAME}'
POSTS = [
    ('w5-row242-outfit-author-1', 'Outfit Layering Idea One'),
    ('w5-row242-outfit-author-2', 'Outfit Layering Idea Two'),
    ('w5-row242-outfit-author-3', 'Outfit Layering Idea Three'),
    ('w5-row242-outfit-author-4', 'Outfit Layering Idea Four'),
    ('w5-row242-outfit-author-5', 'Outfit Layering Idea Five'),
]

class MattermostXslOutfitCommentTask(BaseTask):
    apps = {'Mattermost', 'XiaoShiLiu'}
    difficulty = 'hard'
    snapshot = 'gma_ready_state'

    sender = MattermostUserAsset(
        username=SENDER,
        email='style.coordinator@example.com',
        first_name='Style',
        last_name='Coordinator',
        team='company',
    )
    bob = MattermostUserAsset(
        username=BOB,
        email='bob.w5@example.com',
        first_name='Bob',
        team='company',
    )
    session = MattermostSessionAsset(username=SENDER)
    expected_channel = MattermostChannelAsset(
        team='company',
        name='chat',
        display_name='chat',
        channel_type='O',
        purpose='StreetStyleShare',
    )
    expected_membership = MattermostChannelMembershipAsset(team='company', channel='chat', username=BOB)
    expected_post = MattermostPostAsset(
        team='company',
        channel='chat',
        username=SENDER,
        message='What are you wearing today?',
    )
    xsl_users = tuple(
        XiaoShiLiuUserAsset(
            user_id=user_id,
            nickname=f'Outfit Creator {index}',
            email=f'{user_id}@example.com',
            avatar=XIAOSHILIU_DEFAULT_AVATAR,
            bio='Campus outfit inspiration.',
            location='Seed Campus',
        )
        for index, (user_id, _title) in enumerate(POSTS, start=1)
    )
    xsl_posts = tuple(
        XiaoShiLiuPostAsset(
            author_user_id=user_id,
            title=title,
            content='A campus outfit idea for the week.',
            category='Fashion',
            tags=['outfit', 'style'],
            image_urls=[IMAGE_URL],
            min_image_count=1,
        )
        for user_id, title in POSTS
    )
    assets = (sender, bob, session, *xsl_users, *xsl_posts)

    goal = (
        'Open Mattermost as style-coordinator, create a public channel named "chat" with purpose '
        '"StreetStyleShare", add Bob, and send exactly "What are you wearing today?". Then open '
        'XiaoShiLiu and, for each Outfit post titled "Outfit Layering Idea One", "Outfit Layering Idea Two", '
        '"Outfit Layering Idea Three", "Outfit Layering Idea Four", and "Outfit Layering Idea Five", like the post '
        f'and comment exactly "{COMMENT}".'
    )

    def criteria(self):
        checks = [
            AssetExists(self.expected_channel, task=self),
            AssetExists(self.expected_membership, task=self),
            AssetExists(self.expected_post, task=self),
        ]
        for user_id, title in POSTS:
            checks.append(AssetExists(XiaoShiLiuLikeAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=title, post_author_user_id=user_id), task=self))
            checks.append(AssetExists(XiaoShiLiuCommentAsset(post_title=title, post_author_user_id=user_id, author_user_id=XIAOSHILIU_LOGIN_USER_ID, content=COMMENT), task=self))
        return checks
