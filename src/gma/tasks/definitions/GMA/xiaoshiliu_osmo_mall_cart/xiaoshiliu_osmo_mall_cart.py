from __future__ import annotations

from gma.apps.mall import MALL_LOGIN_CITY, MALL_LOGIN_NICKNAME, MALL_LOGIN_PHONE, MALL_LOGIN_USERNAME
from gma.apps.xiaoshiliu import XIAOSHILIU_DEFAULT_AVATAR, XIAOSHILIU_LOGIN_USER_ID
from gma.assets import MallCartItemAsset, MallMemberAsset, XiaoShiLiuCollectionAsset, XiaoShiLiuLikeAsset, XiaoShiLiuPostAsset, XiaoShiLiuUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


AUTHOR_ID = "w4-row226-osmo-author"
PRODUCT_SN = "2358964"
POSTS = (
    XiaoShiLiuPostAsset(author_user_id=AUTHOR_ID, title="Osmo Handheld Setup", content="Osmo handheld stabilizer setup for street video.", category="Technology", tags=["Osmo"], image_urls=["/assets/xiaoshiliu-osmo-mall-cart-osmo-handheld.png"], min_image_count=1, created_at_ms=1790845800000),
    XiaoShiLiuPostAsset(author_user_id=AUTHOR_ID, title="Osmo Walking Shot", content="Osmo handheld notes for smooth walking shots.", category="Technology", tags=["Osmo"], image_urls=["/assets/xiaoshiliu-osmo-mall-cart-osmo-handheld.png"], min_image_count=1, created_at_ms=1790845500000),
    XiaoShiLiuPostAsset(author_user_id=AUTHOR_ID, title="Osmo Wearable Reminder", content="A wearable Osmo accessory that should not be selected for Mall.", category="Technology", tags=["Osmo"], image_urls=["/assets/xiaoshiliu-osmo-mall-cart-osmo-handheld.png"], min_image_count=1, created_at_ms=1790845200000),
)
LIKED_POSTS = POSTS[:2]
SEEDED_LIKES = tuple(XiaoShiLiuLikeAsset(user_id=f"w4-row226-like-{i}", post_title=post.title, post_author_user_id=AUTHOR_ID) for i, post in enumerate(LIKED_POSTS, start=1))
COLLECTIONS = tuple(XiaoShiLiuCollectionAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=post.title, post_author_user_id=AUTHOR_ID) for post in LIKED_POSTS)

class XiaoShiLiuOsmoMallCartTask(BaseTask):
    apps = {"XiaoShiLiu", "Mall"}
    difficulty = "hard"
    snapshot = "gma_ready_state"
    assets = (
        XiaoShiLiuUserAsset(user_id=AUTHOR_ID, nickname="Osmo Gear Desk", email="osmo-row226@example.com", avatar=XIAOSHILIU_DEFAULT_AVATAR),
        *POSTS,
        *SEEDED_LIKES,
        MallMemberAsset(username=MALL_LOGIN_USERNAME, password="123456", nickname=MALL_LOGIN_NICKNAME, phone=MALL_LOGIN_PHONE, city=MALL_LOGIN_CITY, status=1),
    )
    goal = (
        "Open XiaoShiLiu, search for Osmo, and save every Osmo note whose like count is not zero. "
        "Then open Mall and add one matching Osmo product to the cart. It must be handheld, non-wearable, and priced no more than 2300."
    )

    def criteria(self):
        return [
            *(AssetExists(collection, task=self) for collection in COLLECTIONS),
            AssetExists(MallCartItemAsset(member_username=MALL_LOGIN_USERNAME, product_sn=PRODUCT_SN, quantity=1, delete_status=False), task=self),
        ]
