from __future__ import annotations

from gma.apps.xiaoshiliu import XIAOSHILIU_DEFAULT_AVATAR, XIAOSHILIU_LOGIN_USER_ID
from gma.assets import MailAccountAsset, MailMessageAsset, MastodonAccountAsset, MastodonFavoriteAsset, MastodonFollowAsset, MastodonStatusAsset, XiaoShiLiuFollowAsset, XiaoShiLiuLikeAsset, XiaoShiLiuPostAsset, XiaoShiLiuUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


ALEX = "alex_rivera"
ALEX_SECOND = "Alex second post about campus planning."
ALICE = "alice_morgan"
ALICE_STATUS = "Alice post about sharing campus updates."
XSL_ALICE = "w5-row254-alice"
XSL_POST = "Alice Campus Most Liked Note"

IMAGE_FILENAME = 'alice-campus-note.jpeg'
IMAGE_URL = f'/assets/{IMAGE_FILENAME}'

class MastodonMailXslAliceFollowupTask(BaseTask):
    apps = {'Mastodon', 'Mail', 'XiaoShiLiu'}
    difficulty = 'hard'
    snapshot = 'gma_ready_state'

    alex_account = MastodonAccountAsset(username=ALEX, email='alex.rivera@example.com', display_name='Alex Rivera', bio='Seeded Alex account.')
    alex_first = MastodonStatusAsset(username=ALEX, text='Alex first post about campus.', visibility='public')
    alex_second = MastodonStatusAsset(username=ALEX, text=ALEX_SECOND, visibility='public')
    alice_account = MastodonAccountAsset(username=ALICE, email='alice.morgan@example.com', display_name='Alice Morgan', bio='Seeded Alice account.')
    alice_status = MastodonStatusAsset(username=ALICE, text=ALICE_STATUS, visibility='public')
    account = MailAccountAsset(display_name='Taylor Morgan', email='taylor.morgan@example.com')
    expected_mail = MailMessageAsset(mailbox='sent', from_name=account.display_name, from_email='test@gmail.com', to=['alice@gmail.com'], subject='Posting encouragement', body='Hope you continue posting', read=True)
    xsl_user = XiaoShiLiuUserAsset(user_id=XSL_ALICE, nickname='Alice Campus', email='w5-row254-alice@example.com', avatar=XIAOSHILIU_DEFAULT_AVATAR, bio='Campus posts.', location='Seed Campus')
    xsl_post = XiaoShiLiuPostAsset(author_user_id=XSL_ALICE, title=XSL_POST, content='A campus note by Alice with the most likes on her page.', category='Campus Life', tags=['alice', 'campus'], image_urls=[IMAGE_URL], min_image_count=1)
    assets = (alex_account, alex_first, alex_second, alice_account, alice_status, account, xsl_user, xsl_post)
    goal = (
        f'Open Mastodon, follow Alex Rivera, and favorite his post "{ALEX_SECOND}". Then follow Alice Morgan and comment exactly "Support" on her post "{ALICE_STATUS}". '
        'Open Mail and send alice@gmail.com an email with subject "Posting encouragement" and body "Hope you continue posting". '
        f'Open XiaoShiLiu, follow Alice Campus, and like the post titled "{XSL_POST}".'
    )

    def criteria(self):
        return [
            AssetExists(MastodonFollowAsset(follower_username='owner', followed_username=ALEX), task=self),
            AssetExists(MastodonFavoriteAsset(actor_username='owner', target_username=ALEX, target_text=ALEX_SECOND), task=self),
            AssetExists(MastodonFollowAsset(follower_username='owner', followed_username=ALICE), task=self),
            AssetExists(MastodonStatusAsset(username='owner', text='Support', visibility='public', reply_to_username=ALICE, reply_to_text=ALICE_STATUS), task=self),
            AssetExists(self.expected_mail, task=self),
            AssetExists(XiaoShiLiuFollowAsset(follower_user_id=XIAOSHILIU_LOGIN_USER_ID, following_user_id=XSL_ALICE), task=self),
            AssetExists(XiaoShiLiuLikeAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=XSL_POST, post_author_user_id=XSL_ALICE), task=self),
        ]
