from __future__ import annotations

from gma.assets import ContactAsset, MastodonAccountAsset, MastodonFavoriteAsset, MastodonPollSpec, MastodonPollStatusAsset, MastodonStatusAsset, SmsMessageAsset
from gma.evaluation import AssetExists, AssetModified
from gma.tasks.base import BaseTask

MAIN_USER = 'owner'
TARGET = 'w5_masto_row251'
BEFORE_TEXT = 'Team lunch poll draft.'
AFTER_TEXT = 'Team lunch poll draft. In summary, all options are good'
THIRD_POST = 'Third update for review.'
MESSAGE = "Hello, I've updated the poll post on Mastodon. Please review it. If there are any issues, feel free to contact me."

class MastodonMessagesPollUpdateVoterTask(BaseTask):
    apps = {'Mastodon', 'Messages'}
    difficulty = 'hard'
    category = ['Conditional Tasks']
    snapshot = 'gma_ready_state'

    before_poll = MastodonPollStatusAsset(username=MAIN_USER, text=BEFORE_TEXT, visibility='public', poll=MastodonPollSpec(options=('Option A', 'Option B'), multiple=False))
    after_poll = MastodonPollStatusAsset(username=MAIN_USER, text=AFTER_TEXT, visibility='public', poll=MastodonPollSpec(options=('Option A', 'Option B', '1', '2'), multiple=False))
    target_account = MastodonAccountAsset(username=TARGET, email='w5-masto-row251@example.com', display_name='Poll Review Target', bio='Poll review account for lunch updates.')
    target_status = MastodonStatusAsset(username=TARGET, text=THIRD_POST, visibility='public')
    contact = ContactAsset(name='Jordan Miller', phone_number='+15552012510')
    expected_sms = SmsMessageAsset(address=contact.phone_number, body=MESSAGE, box='sent', read=True)
    assets = (before_poll, target_account, target_status, contact)
    user_interaction = 'If the agent cannot find a Messages contact named Voter, use Jordan Miller instead.'

    goal = (
        f'Open Mastodon and edit your poll post "{BEFORE_TEXT}" so the text becomes exactly "{AFTER_TEXT}" and the poll options are Option A, Option B, 1, and 2. '
        f'Then favorite the post "{THIRD_POST}" by Poll Review Target if it is not already favorited. Open Messages and send Jordan Miller exactly "{MESSAGE}".'
    )

    def criteria(self):
        return [
            AssetModified(self.before_poll, self.after_poll, task=self),
            AssetExists(MastodonFavoriteAsset(actor_username=MAIN_USER, target_username=TARGET, target_text=THIRD_POST), task=self),
            AssetExists(self.expected_sms, task=self),
        ]
