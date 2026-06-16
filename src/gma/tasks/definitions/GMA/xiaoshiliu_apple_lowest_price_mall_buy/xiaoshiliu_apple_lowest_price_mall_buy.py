from __future__ import annotations

from gma.apps.mall import MALL_LOGIN_CITY, MALL_LOGIN_NICKNAME, MALL_LOGIN_PHONE, MALL_LOGIN_USERNAME
from gma.apps.xiaoshiliu import XIAOSHILIU_DEFAULT_AVATAR
from gma.assets import MallAddressAsset, MallMemberAsset, XiaoShiLiuPostAsset, XiaoShiLiuUserAsset
from gma.evaluation.checks.mall import MallCheckoutOrderCreated
from gma.tasks.base import BaseTask


AUTHOR_ID = "w4-row231-apple-author"
LOW_SN = "MPXR3CH/A"
POSTS = (
    XiaoShiLiuPostAsset(author_user_id=AUTHOR_ID, title="iPhone 14 Pro Recommendation", content="Recommended Apple product: iPhone 14 Pro.", category="Technology", tags=["Apple"], image_urls=["/assets/xiaoshiliu-apple-lowest-price-mall-buy-airpods.png"], min_image_count=1, created_at_ms=1790845800000),
    XiaoShiLiuPostAsset(author_user_id=AUTHOR_ID, title="iPhone 16 Pro Recommendation", content="Recommended Apple product: iPhone 16 Pro.", category="Technology", tags=["Apple"], image_urls=["/assets/xiaoshiliu-apple-lowest-price-mall-buy-ipad.png"], min_image_count=1, created_at_ms=1790845500000),
    XiaoShiLiuPostAsset(author_user_id=AUTHOR_ID, title="iPhone 17 Pro Recommendation", content="Recommended Apple product: iPhone 17 Pro.", category="Technology", tags=["Apple"], image_urls=["/assets/xiaoshiliu-apple-lowest-price-mall-buy-watch.png"], min_image_count=1, created_at_ms=1790845200000),
)

class XiaoShiLiuAppleLowestPriceMallBuyTask(BaseTask):
    apps = {"XiaoShiLiu", "Mall"}
    difficulty = "hard"
    snapshot = "gma_ready_state"
    assets = (
        XiaoShiLiuUserAsset(user_id=AUTHOR_ID, nickname="Apple Picks", email="apple.picks@example.com", avatar=XIAOSHILIU_DEFAULT_AVATAR),
        *POSTS,
        MallMemberAsset(username=MALL_LOGIN_USERNAME, password="123456", nickname=MALL_LOGIN_NICKNAME, phone=MALL_LOGIN_PHONE, city=MALL_LOGIN_CITY, status=1),
        MallAddressAsset(member_username=MALL_LOGIN_USERNAME, name="Morgan Carter", phone_number="5550101124", province="New York State", city="New York City", region="Queens Borough", detail_address="Apartment 4B", default_status=True),
    )
    goal = (
        "Open XiaoShiLiu and search for Apple. Note the recommended Apple products from the search results, "
        "then open Mall, compare their prices, and buy the lowest-priced recommended product and pay with Alipay."
    )

    def criteria(self):
        return [MallCheckoutOrderCreated(member_username=MALL_LOGIN_USERNAME, product_sn=LOW_SN, quantity=1, expected_status=1, receiver_name="Morgan Carter")]
