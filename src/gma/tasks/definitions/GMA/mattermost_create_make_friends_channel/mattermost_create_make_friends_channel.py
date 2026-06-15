from __future__ import annotations

from gma.assets import (
    MattermostChannelAsset,
    MattermostChannelMembershipAsset,
    MattermostPostAsset,
    MattermostUserAsset,
)
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


CHANNEL_NAME = "make-friends"
MEMBER_USERNAME = "topplayers"


class MattermostCreateMakeFriendsChannelTask(BaseTask):
    apps = {"Mattermost"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (
        MattermostUserAsset(
            username=MEMBER_USERNAME,
            email="topplayers@example.com",
            first_name="Top",
            last_name="Players",
            team="company",
        ),
    )
    goal = (
        "Open Mattermost in the Company workspace. Create a public channel named "
        "\"make friends\" with purpose \"change our life\" and header \"Welcome\". "
        "Then open that channel, add Top Players as a member, and send exactly this message: \"1\"."
    )

    def criteria(self):
        return [
            AssetExists(
                MattermostChannelAsset(
                    team="company",
                    name=CHANNEL_NAME,
                    display_name="make friends",
                    channel_type="O",
                    purpose="change our life",
                    header="Welcome",
                ),
                task=self,
            ),
            AssetExists(
                MattermostChannelMembershipAsset(
                    team="company",
                    channel=CHANNEL_NAME,
                    username=MEMBER_USERNAME,
                ),
                task=self,
            ),
            AssetExists(
                MattermostPostAsset(
                    team="company",
                    channel=CHANNEL_NAME,
                    username="admin",
                    message="1",
                ),
                task=self,
            ),
        ]
