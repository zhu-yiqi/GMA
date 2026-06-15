from __future__ import annotations

from gma.assets import MattermostChannelAsset, MattermostPostAsset
from gma.evaluation import AssetDeleted
from gma.tasks.base import BaseTask


CHANNEL_NAME = "sprint-cleanup-archive"
CHANNEL_DISPLAY_NAME = "Sprint Cleanup Archive"
POST_MESSAGE = "This cleanup channel should be archived."


class MattermostDeleteSeededCleanupChannelTask(BaseTask):
    apps = {"Mattermost"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    cleanup_channel = MattermostChannelAsset(
        team="company",
        name=CHANNEL_NAME,
        display_name=CHANNEL_DISPLAY_NAME,
        channel_type="O",
        purpose="Temporary cleanup channel",
        header="Archive this channel",
    )
    cleanup_post = MattermostPostAsset(
        team="company",
        channel=CHANNEL_NAME,
        username="admin",
        message=POST_MESSAGE,
    )
    assets = (cleanup_channel, cleanup_post)

    goal = 'Open Mattermost, find the channel "Sprint Cleanup Archive", and archive or delete that channel.'

    def criteria(self):
        return [AssetDeleted(self.cleanup_channel, task=self)]
