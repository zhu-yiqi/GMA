from __future__ import annotations

from gma.assets import MattermostDirectChannelAsset, MattermostDirectPostAsset, MattermostSessionAsset, MattermostUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


OWNER_USER = "riley-chen"
SENDER_USER = "priya-shah"
ROOT_MESSAGE = "Could you confirm that the vendor packet arrived?"
REPLY_MESSAGE = "Okay, received."


class MattermostReplyToUnreadDirectMessageTask(BaseTask):
    apps = {"Mattermost"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    owner = MattermostUserAsset(
        username=OWNER_USER,
        email="riley.chen@example.com",
        first_name="Riley",
        last_name="Chen",
        team="company",
    )
    sender = MattermostUserAsset(
        username=SENDER_USER,
        email="priya.shah@example.com",
        first_name="Priya",
        last_name="Shah",
        team="company",
    )
    direct_channel = MattermostDirectChannelAsset(usernames=(OWNER_USER, SENDER_USER))
    unread_post = MattermostDirectPostAsset(
        username=SENDER_USER,
        other_username=OWNER_USER,
        message=ROOT_MESSAGE,
        create_at_ms=202610011000,
    )
    expected_reply = MattermostDirectPostAsset(
        username=OWNER_USER,
        other_username=SENDER_USER,
        message=REPLY_MESSAGE,
        root_message=ROOT_MESSAGE,
        root_username=SENDER_USER,
    )
    assets = (
        owner,
        sender,
        direct_channel,
        MattermostSessionAsset(username=OWNER_USER),
        unread_post,
    )

    goal = (
        "Open Mattermost and reply in the thread for Priya Shah's unread direct message "
        'about the vendor packet. Send exactly "Okay, received."'
    )

    def criteria(self):
        return [AssetExists(self.expected_reply, task=self)]
