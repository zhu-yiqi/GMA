from __future__ import annotations

from gma.apps.mall import MALL_LOGIN_CITY, MALL_LOGIN_NICKNAME, MALL_LOGIN_PHONE, MALL_LOGIN_USERNAME
from gma.apps.xiaoshiliu import XIAOSHILIU_DEFAULT_AVATAR, XIAOSHILIU_LOGIN_USER_ID
from gma.assets import ElementXMessageAsset, ElementXRoomAsset, ElementXUserAsset, MallAddressAsset, MallMemberAsset, XiaoShiLiuCollectionAsset, XiaoShiLiuPostAsset, XiaoShiLiuUserAsset
from gma.evaluation.checks.mall import MallCheckoutOrderCreated
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


ROOM = "w4-row227-product-friend"
PRODUCT_SN = "fr0041TU"
AUTHOR_ID = "w4-row227-product-author"
RECOMMENDATION = "I recommend the HP StarBook Pro 14-inch AI laptop for your next purchase."
POSTS = tuple(
    XiaoShiLiuPostAsset(author_user_id=AUTHOR_ID, title=f"HP StarBook Pro User Note {i}", content="Related notes about HP StarBook Pro 14-inch AI laptop for school and office work.", category="Technology", tags=["HP StarBook Pro 14-inch AI laptop"], image_urls=["/assets/elementx-recommended-product-xsl-mall-buy-hp-probook.png"], min_image_count=1, created_at_ms=1790845200000 - i * 60000)
    for i in range(1, 4)
)
COLLECTIONS = tuple(XiaoShiLiuCollectionAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=post.title, post_author_user_id=AUTHOR_ID) for post in POSTS)

class ElementXRecommendedProductXslMallBuyTask(BaseTask):
    apps = {"ElementX", "XiaoShiLiu", "Mall"}
    difficulty = "hard"
    snapshot = "gma_ready_state"
    assets = (
        ElementXUserAsset(username="w4-row227-friend", password="password", display_name="Product Friend"),
        ElementXRoomAsset(name="Product Friend", room_type="dm", creator_username="w4-row227-friend", creator_password="password", members=["testuser"], alias_localpart=ROOM),
        ElementXMessageAsset(room=ROOM, sender_username="w4-row227-friend", sender_password="password", text=RECOMMENDATION),
        XiaoShiLiuUserAsset(user_id=AUTHOR_ID, nickname="ProBook Notes", email="probook.notes@example.com", avatar=XIAOSHILIU_DEFAULT_AVATAR),
        *POSTS,
        MallMemberAsset(username=MALL_LOGIN_USERNAME, password="123456", nickname=MALL_LOGIN_NICKNAME, phone=MALL_LOGIN_PHONE, city=MALL_LOGIN_CITY, status=1),
        MallAddressAsset(member_username=MALL_LOGIN_USERNAME, name="Morgan Carter", phone_number="5550101039", province="New York State", city="New York City", region="Queens Borough", detail_address="Apartment 5C", default_status=True),
    )
    goal = (
        "Open ElementX and read the product recommended by Product Friend. Then open XiaoShiLiu, search for that product, "
        "and save all related notes. Finally open Mall and buy one unit of that product using the first saved address and pay with Alipay."
    )

    def criteria(self):
        return [
            *(AssetExists(collection, task=self) for collection in COLLECTIONS),
            MallCheckoutOrderCreated(member_username=MALL_LOGIN_USERNAME, product_sn=PRODUCT_SN, quantity=1, expected_status=1, receiver_name="Morgan Carter"),
        ]
