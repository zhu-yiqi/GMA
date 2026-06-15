
from __future__ import annotations

from gma.apps.meituan import MEITUAN_LOGIN_CITY, MEITUAN_LOGIN_USER_ID, MEITUAN_LOGIN_USERNAME
from gma.assets import (
    MastodonPollSpec,
    MastodonPollStatusAsset,
    MastodonSessionAsset,
    MeituanAddressAsset,
    MeituanOrderAsset,
    MeituanOrderFood,
    MeituanSessionAsset,
    MeituanUserAsset,
)
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


MAIN_USER = "owner"
POLL_TEXT = "Which do you prefer, Mexican chicken wrap or Korean-style chicken wrap?"
OPTION_ONE = "French fries trio"
OPTION_TWO = "Mai la Ji tui Bao single meal"


class MastodonMeituanWrapPollOrderTask(BaseTask):
    apps = {"Mastodon", "Meituan"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    meituan_user = MeituanUserAsset(username=MEITUAN_LOGIN_USERNAME, password="123456", user_id=MEITUAN_LOGIN_USER_ID, city=MEITUAN_LOGIN_CITY, status=1)
    meituan_session = MeituanSessionAsset(username=MEITUAN_LOGIN_USERNAME, password="123456")
    company_address = MeituanAddressAsset(
        user_id=MEITUAN_LOGIN_USER_ID,
        name="Company",
        phone="5550101061",
        address="Company Campus",
        address_detail="Building A Front Desk",
        label="Office",
        gender="male",
        province="New York State",
        city=MEITUAN_LOGIN_CITY,
    )
    expected_poll = MastodonPollStatusAsset(
        username=MAIN_USER,
        text=POLL_TEXT,
        visibility="public",
        poll=MastodonPollSpec(options=(OPTION_ONE, OPTION_TWO), multiple=False),
    )
    expected_order = MeituanOrderAsset(
        user_id=MEITUAN_LOGIN_USER_ID,
        restaurant_name="McDonald's",
        foods=[MeituanOrderFood(food_name=OPTION_ONE, quantity=1), MeituanOrderFood(food_name=OPTION_TWO, quantity=1)],
        status="Payment successful",
        address_name="Company",
        code=200,
        delivery_status=1,
    )
    assets = (MastodonSessionAsset(username=MAIN_USER), meituan_user, meituan_session, company_address)

    goal = (
        "Open Mastodon and publish a public single-choice poll with exactly "
        "\"Which do you prefer, Mexican chicken wrap or Korean-style chicken wrap?\" as the question, "
        "and exactly these options: \"French fries trio\" and \"Mai la Ji tui Bao single meal\". "
        "Then open Meituan, search for \"French fries trio\" and \"Mai la Ji tui Bao single meal\", "
        "order one of each from McDonald's using the saved Company address, and pay with Alipay."
    )

    def criteria(self):
        return [AssetExists(self.expected_poll, task=self), AssetExists(self.expected_order, task=self)]
