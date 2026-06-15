from __future__ import annotations

from gma.assets import MastodonStatusAsset
from gma.evaluation import AssetModified
from gma.tasks.base import BaseTask


MAIN_USER = "owner"


class MastodonEditLatestChoosePostTask(BaseTask):
    apps = {"Mastodon"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    older_status = MastodonStatusAsset(
        username=MAIN_USER,
        text="Keeping a short reading list for tonight.",
        visibility="public",
        created_at_ms=1790802000000,
    )
    before_status = MastodonStatusAsset(
        username=MAIN_USER,
        text="Which notebook color should I use for the project?",
        visibility="public",
        created_at_ms=1790805600000,
    )
    after_status = MastodonStatusAsset(
        username=MAIN_USER,
        text="Please help me choose, thank you.",
        visibility="public",
    )
    assets = (older_status, before_status)

    goal = (
        "Open Mastodon and edit my most recent post. Change its text exactly to "
        '"Please help me choose, thank you."'
    )

    def criteria(self):
        return [AssetModified(self.before_status, self.after_status, task=self)]
