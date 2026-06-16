from __future__ import annotations

from gma.apps.mall import MALL_LOGIN_CITY, MALL_LOGIN_NICKNAME, MALL_LOGIN_PHONE, MALL_LOGIN_USERNAME
from gma.apps.xiaoshiliu import XIAOSHILIU_DEFAULT_AVATAR, XIAOSHILIU_LOGIN_USER_ID
from gma.assets import MallAddressAsset, MallMemberAsset, MastodonAccountAsset, MastodonStatusAsset, XiaoShiLiuCollectionAsset, XiaoShiLiuPostAsset, XiaoShiLiuUserAsset
from gma.evaluation import AssetDeleted, AssetExists
from gma.tasks.base import BaseTask
from gma.evaluation.checks.mall import MallCheckoutOrderCreated


PRODUCT_SN = "HRF-A52XF1BU1"
AUTHOR_ID = "w4-row228-fridge-author"
LEO_POST = "Recommended refrigerator model: Yunxi 512 L air-cooled inverter multi-door refrigerator. It is quiet and efficient."
TARGET_POSTS = (
    XiaoShiLiuPostAsset(author_user_id=AUTHOR_ID, title="Yunxi 512 L air-cooled inverter multi-door refrigerator Review A", content="Recommended refrigerator model: Yunxi 512 L air-cooled inverter multi-door refrigerator. Many users like this fridge.", category="Technology", tags=["Yunxi 512 L", "refrigerator"], image_urls=["/assets/mastodon-refrigerator-xsl-mall-buy-fridge.png"], min_image_count=1, created_at_ms=1790845500000),
    XiaoShiLiuPostAsset(author_user_id=AUTHOR_ID, title="Yunxi 512 L air-cooled inverter multi-door refrigerator Review B", content="Yunxi 512 L air-cooled inverter multi-door refrigerator is the model recommended most often in this thread.", category="Technology", tags=["Yunxi 512 L", "refrigerator"], image_urls=["/assets/mastodon-refrigerator-xsl-mall-buy-fridge.png"], min_image_count=1, created_at_ms=1790845200000),
)
DISTRACTOR_POST = XiaoShiLiuPostAsset(author_user_id=AUTHOR_ID, title="Aurora 420 L frost-free refrigerator Review", content="Aurora 420 L frost-free refrigerator is a different model. It is mentioned here as a comparison, not Leo's recommendation.", category="Technology", tags=["Aurora 420 L", "refrigerator"], image_urls=["/assets/mastodon-refrigerator-xsl-mall-buy-fridge.png"], min_image_count=1, created_at_ms=1790844900000)
COLLECTIONS = tuple(XiaoShiLiuCollectionAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=post.title, post_author_user_id=AUTHOR_ID) for post in TARGET_POSTS)
DISTRACTOR_COLLECTION = XiaoShiLiuCollectionAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=DISTRACTOR_POST.title, post_author_user_id=AUTHOR_ID)

class MastodonRefrigeratorXslMallBuyTask(BaseTask):
    apps = {"Mastodon", "XiaoShiLiu", "Mall"}
    difficulty = "hard"
    snapshot = "gma_ready_state"
    assets = (
        MastodonAccountAsset(username="leo", email="leo.row228@example.com", display_name="Leo"),
        MastodonStatusAsset(username="leo", text=LEO_POST, visibility="public", created_at_ms=202610011100),
        XiaoShiLiuUserAsset(user_id=AUTHOR_ID, nickname="Fridge Review Desk", email="fridge-row228@example.com", avatar=XIAOSHILIU_DEFAULT_AVATAR),
        *TARGET_POSTS,
        DISTRACTOR_POST,
        MallMemberAsset(username=MALL_LOGIN_USERNAME, password="123456", nickname=MALL_LOGIN_NICKNAME, phone=MALL_LOGIN_PHONE, city=MALL_LOGIN_CITY, status=1),
        MallAddressAsset(member_username=MALL_LOGIN_USERNAME, name="Morgan Carter", phone_number="5550101078", province="New York State", city="New York City", region="Brooklyn Borough", detail_address="124 Park Slope Avenue Apt 3", default_status=True),
    )
    goal = (
        "Open Mastodon and read Leo's refrigerator recommendation. Then open XiaoShiLiu, search for the recommended refrigerator model, "
        "save only the related review notes for that recommended model, and confirm it is the most recommended model. "
        "Finally open Mall and buy one matching refrigerator using Morgan Carter's default address and pay with Alipay."
    )

    def criteria(self):
        return [
            *(AssetExists(collection, task=self) for collection in COLLECTIONS),
            AssetDeleted(DISTRACTOR_COLLECTION, task=self),
            MallCheckoutOrderCreated(member_username=MALL_LOGIN_USERNAME, product_sn=PRODUCT_SN, quantity=1, expected_status=1, receiver_name="Morgan Carter"),
        ]
