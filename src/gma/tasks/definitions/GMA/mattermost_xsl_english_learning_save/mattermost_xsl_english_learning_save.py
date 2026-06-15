from __future__ import annotations

from gma.apps.xiaoshiliu import XIAOSHILIU_DEFAULT_AVATAR, XIAOSHILIU_LOGIN_USER_ID
from gma.assets import (
    MattermostChannelAsset,
    MattermostPostAsset,
    MattermostSessionAsset,
    MattermostUserAsset,
    XiaoShiLiuCollectionAsset,
    XiaoShiLiuPostAsset,
    XiaoShiLiuUserAsset,
)
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


SENDER = 'english-learner'
THIRD_CHANNEL = 'english-practice-room'
MESSAGE = 'I will use my spare time to learn English; before that I will bookmark several English learning posts. @jack'
IMAGE_FILENAME = 'english-study.jpeg'
IMAGE_URL = f'/assets/{IMAGE_FILENAME}'
POSTS = [
    ('w5-row243-english-author-1', 'English Learning Speaking Routine'),
    ('w5-row243-english-author-2', 'English Learning Vocabulary Plan'),
    ('w5-row243-english-author-3', 'English Learning Listening Notes'),
]

class MattermostXslEnglishLearningSaveTask(BaseTask):
    apps = {'Mattermost', 'XiaoShiLiu'}
    difficulty = 'hard'
    snapshot = 'gma_ready_state'

    sender = MattermostUserAsset(username=SENDER, email='english.learner@example.com', first_name='English', team='company', channel_memberships=['speaking-routine', 'vocabulary-plans', THIRD_CHANNEL])
    jack = MattermostUserAsset(username='jack', email='jack.w5@example.com', first_name='Jack', team='company', channel_memberships=[THIRD_CHANNEL])
    channels = (
        MattermostChannelAsset(team='company', name='speaking-routine', display_name='Speaking Routine', channel_type='O'),
        MattermostChannelAsset(team='company', name='vocabulary-plans', display_name='Vocabulary Plans', channel_type='O'),
        MattermostChannelAsset(team='company', name=THIRD_CHANNEL, display_name='English Practice Room', channel_type='O'),
    )
    session = MattermostSessionAsset(username=SENDER)
    xsl_users = tuple(XiaoShiLiuUserAsset(user_id=user_id, nickname=f'English Mentor {i}', email=f'{user_id}@example.com', avatar=XIAOSHILIU_DEFAULT_AVATAR, bio='English learning notes.', location='Seed Campus') for i, (user_id, _title) in enumerate(POSTS, start=1))
    xsl_posts = tuple(XiaoShiLiuPostAsset(author_user_id=user_id, title=title, content='A practical English learning note for daily practice.', category='Study', tags=['english', 'learning'], image_urls=[IMAGE_URL], min_image_count=1) for user_id, title in POSTS)
    assets = (*channels, sender, jack, session, *xsl_users, *xsl_posts)

    goal = (
        'Open Mattermost as english-learner, go to "English Practice Room", and send exactly '
        f'"{MESSAGE}". Then open XiaoShiLiu and save the three English learning posts titled '
        '"English Learning Speaking Routine", "English Learning Vocabulary Plan", and "English Learning Listening Notes".'
    )

    def criteria(self):
        return [
            AssetExists(MattermostPostAsset(team='company', channel=THIRD_CHANNEL, username=SENDER, message=MESSAGE), task=self),
            *[AssetExists(XiaoShiLiuCollectionAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=title, post_author_user_id=user_id), task=self) for user_id, title in POSTS],
        ]
