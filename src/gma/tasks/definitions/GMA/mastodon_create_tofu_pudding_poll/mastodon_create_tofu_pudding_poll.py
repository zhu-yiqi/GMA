from __future__ import annotations

from gma.assets import MastodonAccountAsset, MastodonPollSpec, MastodonPollStatusAsset, MastodonSessionAsset, MastodonStatusAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


MAIN_USER = "owner"
POLL_TEXT = "Which tofu pudding do you like better?"
OPTION_ONE = "Sweet tofu pudding"
OPTION_TWO = "Savory tofu pudding"


class MastodonCreateTofuPuddingPollTask(BaseTask):
    apps = {"Mastodon"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    neighbor = MastodonAccountAsset(
        username="w3_masto_row29_neighbor",
        email="w3.masto.row29.neighbor@example.com",
        display_name="Neighborhood Notes",
        bio="Seeded account for food-poll timeline context.",
    )
    context_status = MastodonStatusAsset(
        username="w3_masto_row29_neighbor",
        text="I am comparing breakfast ideas for the weekend market.",
        visibility="public",
        created_at_ms=1790845200000,
    )
    context_poll = MastodonPollStatusAsset(
        username="w3_masto_row29_neighbor",
        text="Which morning drink should the market sample first?",
        visibility="public",
        poll=MastodonPollSpec(options=("Hot soy milk", "Iced tea"), multiple=False),
        created_at_ms=1790845500000,
    )
    expected_poll = MastodonPollStatusAsset(
        username=MAIN_USER,
        text=POLL_TEXT,
        visibility="public",
        poll=MastodonPollSpec(options=(OPTION_ONE, OPTION_TWO), multiple=False),
    )
    assets = (neighbor, context_status, context_poll, MastodonSessionAsset(username=MAIN_USER))

    goal = (
        "Open Mastodon and publish a public single-choice poll. Use exactly "
        '"Which tofu pudding do you like better?" as the post text, with exactly these options: '
        '"Sweet tofu pudding" and "Savory tofu pudding".'
    )

    def criteria(self):
        return [AssetExists(self.expected_poll, task=self)]
