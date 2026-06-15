from __future__ import annotations

from gma.assets import MattermostDirectChannelAsset, MattermostDirectPostAsset, MattermostUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


PLAYBOOKS = "playbooks"
MESSAGE = "Are you available tomorrow?"


class MattermostDmPlaybooksAvailabilityTask(BaseTask):
    apps = {"Mattermost"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (
        MattermostUserAsset(
            username=PLAYBOOKS,
            email="playbooks@example.com",
            first_name="Playbooks",
            last_name="Member",
            team="company",
        ),
        MattermostDirectChannelAsset(usernames=("admin", PLAYBOOKS)),
    )
    goal = (
        "Open Mattermost, open the direct message with playbooks, and send exactly this message: "
        "\"Are you available tomorrow?\" Then return to the most recent group channel and open its latest message."
    )

    def criteria(self):
        return [
            AssetExists(
                MattermostDirectPostAsset(
                    username="admin",
                    other_username=PLAYBOOKS,
                    message=MESSAGE,
                ),
                task=self,
            )
        ]
