
from __future__ import annotations

from gma.apps.mall import MALL_LOGIN_CITY, MALL_LOGIN_NICKNAME, MALL_LOGIN_PHONE, MALL_LOGIN_USERNAME
from gma.assets import MallMemberAsset, MastodonAccountAsset, MastodonFollowAsset, MastodonSessionAsset, MastodonStatusAsset
from gma.evaluation.checks.mall import MallProductFavorited
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


MAIN_USER = "owner"
DEMO_POST = "Sharing a short note about domestic products today."
IPHONE_17_PRO_NAME = "iPhone 17 Pro"
IPHONE_17_PRO_SN = "JNW6WYGVKF"


class MastodonDemoFollowCommentMallCartTask(BaseTask):
    apps = {"Mastodon", "Mall"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    demo = MastodonAccountAsset(username="demo", email="demo@example.com", display_name="demo", bio="Seeded Mall cross-app account.")
    demo_post = MastodonStatusAsset(username="demo", text=DEMO_POST, visibility="public", created_at_ms=202610011000)
    mall_user = MallMemberAsset(username=MALL_LOGIN_USERNAME, password="123456", nickname=MALL_LOGIN_NICKNAME, phone=MALL_LOGIN_PHONE, city=MALL_LOGIN_CITY, status=1)
    expected_follow = MastodonFollowAsset(follower_username=MAIN_USER, followed_username="demo")
    expected_comment = MastodonStatusAsset(username=MAIN_USER, text="Support domestic products", visibility="public", reply_to_username="demo", reply_to_text=DEMO_POST)
    expected_favorite = MallProductFavorited(member_username=MALL_LOGIN_USERNAME, product_sn=IPHONE_17_PRO_SN, product_name=IPHONE_17_PRO_NAME)
    assets = (demo, demo_post, mall_user, MastodonSessionAsset(username=MAIN_USER))

    goal = (
        "Open Mastodon and search for user \"demo\". If you are not already following demo, follow them, "
        "then comment exactly \"Support domestic products\" on demo's first post. Open Mall "
        "and favorite the iPhone 17 Pro product."
    )

    def criteria(self):
        return [AssetExists(self.expected_follow, task=self), AssetExists(self.expected_comment, task=self), self.expected_favorite]
