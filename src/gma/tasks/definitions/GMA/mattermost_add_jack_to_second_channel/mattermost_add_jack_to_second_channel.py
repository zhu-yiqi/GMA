from __future__ import annotations

from gma.assets import (
    MattermostChannelAsset,
    MattermostChannelMembershipAsset,
    MattermostSessionAsset,
    MattermostUserAsset,
)
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


OWNER_USER = "morgan-lane"
JACK_USER = "jack-reed"
FIRST_CHANNEL = "w3-row21-atlas-briefing"
SECOND_CHANNEL = "w3-row21-field-notes"


class MattermostAddJackToSecondChannelTask(BaseTask):
    apps = {"Mattermost"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    owner = MattermostUserAsset(
        username=OWNER_USER,
        email="morgan.lane@example.com",
        first_name="Morgan",
        last_name="Lane",
        team="company",
        channel_memberships=[FIRST_CHANNEL, SECOND_CHANNEL],
    )
    jack = MattermostUserAsset(
        username=JACK_USER,
        email="jack.reed@example.com",
        first_name="Jack",
        last_name="Reed",
        team="company",
    )
    first_channel = MattermostChannelAsset(
        team="company",
        name=FIRST_CHANNEL,
        display_name="Atlas Briefing",
        channel_type="P",
        purpose="Planning notes for the Atlas launch.",
    )
    second_channel = MattermostChannelAsset(
        team="company",
        name=SECOND_CHANNEL,
        display_name="Field Notes",
        channel_type="P",
        purpose="Daily field updates that need Jack's input.",
    )
    expected_membership = MattermostChannelMembershipAsset(
        team="company",
        channel=SECOND_CHANNEL,
        username=JACK_USER,
    )
    assets = (first_channel, second_channel, owner, jack, MattermostSessionAsset(username=OWNER_USER))

    goal = (
        "Open Mattermost. In the Channels list, use the second planning channel, "
        "Field Notes, and add Jack Reed to that channel."
    )

    def criteria(self):
        return [AssetExists(self.expected_membership, task=self)]
