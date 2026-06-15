from __future__ import annotations

from gma.assets import MattermostChannelAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


class MattermostCreateTaskChannelTask(BaseTask):
    apps = {"Mattermost"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    expected_channel = MattermostChannelAsset(
        team="company",
        name="task",
        display_name="Task",
        channel_type="O",
    )

    goal = 'Open Mattermost in the Company workspace and create a public channel named "Task".'

    def criteria(self):
        return [AssetExists(self.expected_channel, task=self)]
