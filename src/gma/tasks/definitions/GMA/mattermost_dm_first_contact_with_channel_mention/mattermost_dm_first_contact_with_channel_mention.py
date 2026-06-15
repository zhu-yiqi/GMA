from __future__ import annotations

from gma.assets import (
    MattermostDirectChannelAsset,
    MattermostDirectPostAsset,
    MattermostSessionAsset,
    MattermostUserAsset,
)
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


SENDER_USER = "taylor-brooks"
FIRST_CONTACT = "ava-morgan"
SECOND_CONTACT = "ben-parker"
MESSAGE = "@channel Please review the handoff checklist before noon."


class MattermostDmFirstContactWithChannelMentionTask(BaseTask):
    apps = {"Mattermost"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    sender = MattermostUserAsset(
        username=SENDER_USER,
        email="taylor.brooks@example.com",
        first_name="Taylor",
        last_name="Brooks",
        team="company",
    )
    ava = MattermostUserAsset(
        username=FIRST_CONTACT,
        email="ava.morgan@example.com",
        first_name="Ava",
        last_name="Morgan",
        team="company",
    )
    ben = MattermostUserAsset(
        username=SECOND_CONTACT,
        email="ben.parker@example.com",
        first_name="Ben",
        last_name="Parker",
        team="company",
    )
    seeded_first_dm = MattermostDirectChannelAsset(usernames=(SENDER_USER, FIRST_CONTACT))
    seeded_second_dm = MattermostDirectChannelAsset(usernames=(SENDER_USER, SECOND_CONTACT))
    expected_post = MattermostDirectPostAsset(
        username=SENDER_USER,
        other_username=FIRST_CONTACT,
        message=MESSAGE,
    )
    assets = (
        sender,
        ava,
        ben,
        seeded_first_dm,
        seeded_second_dm,
        MattermostSessionAsset(username=SENDER_USER),
    )

    goal = (
        'Open Mattermost and use the direct-message contact Ava Morgan. '
        'Send exactly "@channel Please review the handoff checklist before noon."'
    )

    def criteria(self):
        return [AssetExists(self.expected_post, task=self)]
