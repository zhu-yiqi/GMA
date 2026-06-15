from __future__ import annotations

from gma.assets import MattermostChannelAsset, MattermostPostAsset
from gma.evaluation import AssetDeleted
from gma.tasks.base import BaseTask


FIRST_CHANNEL = "w3-row27-alpha-notes"
SECOND_CHANNEL = "w3-row27-delta-planning"
THIRD_CHANNEL = "w3-row27-zeta-handoff"


class MattermostArchiveSecondChannelTask(BaseTask):
    apps = {"Mattermost"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    first_channel = MattermostChannelAsset(team="company", name=FIRST_CHANNEL, display_name="Alpha Notes", channel_type="O")
    second_channel = MattermostChannelAsset(team="company", name=SECOND_CHANNEL, display_name="Delta Planning", channel_type="O")
    third_channel = MattermostChannelAsset(team="company", name=THIRD_CHANNEL, display_name="Zeta Handoff", channel_type="O")
    context_post = MattermostPostAsset(
        team="company",
        channel=SECOND_CHANNEL,
        username="admin",
        message="Delta Planning is ready to close after the review window.",
    )
    assets = (first_channel, second_channel, third_channel, context_post)

    goal = (
        "Open Mattermost and archive the second seeded channel in the Channels list, "
        "Delta Planning."
    )

    def criteria(self):
        return [AssetDeleted(self.second_channel, task=self)]
