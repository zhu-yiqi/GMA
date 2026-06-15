from __future__ import annotations

from gma.assets import DeviceFileAsset, MattermostChannelAsset, MattermostFilePostAsset, MattermostSessionAsset, MattermostUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


USER = "jamie-cole"
FIRST_CHANNEL = "w3-row24-alpha-review"
SECOND_CHANNEL = "w3-row24-beta-review"
FILE_NAME = "tasks.txt"
FILE_TEXT = "Task list for the weekly operations review.\n- Confirm vendor packet\n- Prepare launch handoff\n"
POST_MESSAGE = "Task file for review."


class MattermostUploadTasksFileToFirstChannelTask(BaseTask):
    apps = {"Mattermost", "Files"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    first_channel = MattermostChannelAsset(
        team="company",
        name=FIRST_CHANNEL,
        display_name="Alpha Review",
        channel_type="O",
    )
    second_channel = MattermostChannelAsset(
        team="company",
        name=SECOND_CHANNEL,
        display_name="Beta Review",
        channel_type="O",
    )
    user = MattermostUserAsset(
        username=USER,
        email="jamie.cole@example.com",
        first_name="Jamie",
        last_name="Cole",
        team="company",
        channel_memberships=[FIRST_CHANNEL, SECOND_CHANNEL],
    )
    source_file = DeviceFileAsset(
        app="Files",
        storage_dir="Download",
        filename=FILE_NAME,
        mime_type="text/plain",
        text_content=FILE_TEXT,
    )
    expected_post = MattermostFilePostAsset(
        team="company",
        channel=FIRST_CHANNEL,
        username=USER,
        message=POST_MESSAGE,
        filename=FILE_NAME,
        mime_type="text/plain",
        text_content=FILE_TEXT,
    )
    assets = (first_channel, second_channel, user, source_file, MattermostSessionAsset(username=USER))

    goal = (
        "Open Mattermost and go to the first review channel, Alpha Review. "
        'Upload the Downloads file tasks.txt with the message "Task file for review."'
    )

    def criteria(self):
        return [AssetExists(self.expected_post, task=self)]
