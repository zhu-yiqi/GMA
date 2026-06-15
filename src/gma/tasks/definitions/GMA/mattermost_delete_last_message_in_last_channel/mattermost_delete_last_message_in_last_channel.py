from __future__ import annotations

from gma.assets import MattermostChannelAsset, MattermostPostAsset, MattermostSessionAsset, MattermostUserAsset
from gma.evaluation import AssetDeleted
from gma.tasks.base import BaseTask


USER = "casey-nolan"
FIRST_CHANNEL = "w3-row25-alpha-intake"
SECOND_CHANNEL = "w3-row25-beta-review"
LAST_CHANNEL = "w3-row25-zeta-archive"
OLDER_MESSAGE = "Keep the archive notes available for audit review."
TARGET_MESSAGE = "Retire the stale checklist after the migration."


class MattermostDeleteLastMessageInLastChannelTask(BaseTask):
    apps = {"Mattermost"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    first_channel = MattermostChannelAsset(team="company", name=FIRST_CHANNEL, display_name="Alpha Intake", channel_type="O")
    second_channel = MattermostChannelAsset(team="company", name=SECOND_CHANNEL, display_name="Beta Review", channel_type="O")
    last_channel = MattermostChannelAsset(team="company", name=LAST_CHANNEL, display_name="Zeta Archive", channel_type="O")
    user = MattermostUserAsset(
        username=USER,
        email="casey.nolan@example.com",
        first_name="Casey",
        last_name="Nolan",
        team="company",
        channel_memberships=[FIRST_CHANNEL, SECOND_CHANNEL, LAST_CHANNEL],
    )
    older_post = MattermostPostAsset(
        team="company",
        channel=LAST_CHANNEL,
        username=USER,
        message=OLDER_MESSAGE,
        create_at_ms=202610011000,
    )
    target_post = MattermostPostAsset(
        team="company",
        channel=LAST_CHANNEL,
        username=USER,
        message=TARGET_MESSAGE,
        create_at_ms=202610011010,
    )
    assets = (first_channel, second_channel, last_channel, user, older_post, target_post, MattermostSessionAsset(username=USER))

    goal = (
        "Open Mattermost, go to the last channel in the Channels list, Zeta Archive, "
        'and delete its newest message: "Retire the stale checklist after the migration."'
    )

    def criteria(self):
        return [AssetDeleted(self.target_post, task=self)]
