from __future__ import annotations

from gma.apps.mall import MALL_LOGIN_CITY, MALL_LOGIN_NICKNAME, MALL_LOGIN_PHONE, MALL_LOGIN_USERNAME
from gma.apps.xiaoshiliu import XIAOSHILIU_DEFAULT_AVATAR, XIAOSHILIU_LOGIN_USER_ID
from gma.assets import ContactAsset, MallAddressAsset, MallMemberAsset, SmsMessageAsset, XiaoShiLiuLikeAsset, XiaoShiLiuPostAsset, XiaoShiLiuUserAsset, XiaoShiLiuFollowAsset
from gma.evaluation import AssetExists, AssetMissing
from gma.tasks.base import BaseTask
from gma.tasks.definitions.tests.mall._criteria import MallCheckoutOrderCreated


SCHOLAR_ID = "w4-row204-scholar-notes"
OWN_LATEST = XiaoShiLiuPostAsset(author_user_id=XIAOSHILIU_LOGIN_USER_ID, title="Outdated Study Checklist", content="These study checkpoints are outdated after the new schedule.", category="Study", image_urls=["/assets/xiaoshiliu-scholar-notes-mall-message-own-latest.png"], min_image_count=1, created_at_ms=202610012230)
SCHOLAR = XiaoShiLiuUserAsset(user_id=SCHOLAR_ID, nickname="Scholar Notes", email="scholar-notes-row204@example.com", avatar=XIAOSHILIU_DEFAULT_AVATAR)
SCHOLAR_POSTS = (
    XiaoShiLiuPostAsset(author_user_id=SCHOLAR_ID, title="Scholar Notes: Math Review", content="Concise formulas and review checkpoints.", category="Study", tags=["study"], image_urls=["/assets/xiaoshiliu-scholar-notes-mall-message-scholar-math.png"], min_image_count=1, created_at_ms=1790845500000),
    XiaoShiLiuPostAsset(author_user_id=SCHOLAR_ID, title="Scholar Notes: Reading Plan", content="A weekly reading plan for exam preparation.", category="Study", tags=["study"], image_urls=["/assets/xiaoshiliu-scholar-notes-mall-message-scholar-reading.png"], min_image_count=1, created_at_ms=1790845200000),
)
CONTACT = ContactAsset(name="Younger Sister", phone_number="+15550152004")
EXPECTED_SMS = SmsMessageAsset(address=CONTACT.phone_number, body="I already bought the Lenovo Y700 tablet for paperless studying.", box="sent", read=True)
EXPECTED_FOLLOW = XiaoShiLiuFollowAsset(follower_user_id=XIAOSHILIU_LOGIN_USER_ID, following_user_id=SCHOLAR_ID)
EXPECTED_LIKES = tuple(XiaoShiLiuLikeAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=post.title, post_author_user_id=SCHOLAR_ID) for post in SCHOLAR_POSTS)
PRODUCT_SN = "ZAH20041CN"

class XiaoShiLiuScholarNotesMallMessageTask(BaseTask):
    apps = {"XiaoShiLiu", "Mall", "Messages"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = (
        OWN_LATEST,
        SCHOLAR,
        *SCHOLAR_POSTS,
        MallMemberAsset(username=MALL_LOGIN_USERNAME, password="123456", nickname=MALL_LOGIN_NICKNAME, phone=MALL_LOGIN_PHONE, city=MALL_LOGIN_CITY, status=1),
        MallAddressAsset(member_username=MALL_LOGIN_USERNAME, name="Taylor Nguyen", phone_number="5550101126", province="New York State", city="New York City", region="Queens Borough", detail_address="18 Queens Plaza Apt 7", default_status=True),
        CONTACT,
    )
    goal = (
        'Open XiaoShiLiu, delete your newest outdated study checklist post, search for "Scholar Notes", follow Scholar Notes, open that profile, and like all two posts by Scholar Notes. '
        "Then open Mall and buy one Lenovo Legion Y700 tablet 5th generation using Taylor Nguyen's default address and pay with Alipay. "
        'Finally open Messages and send "I already bought the Lenovo Y700 tablet for paperless studying." to Younger Sister.'
    )

    def criteria(self):
        return [
            AssetMissing(OWN_LATEST, task=self),
            AssetExists(EXPECTED_FOLLOW, task=self),
            *(AssetExists(asset, task=self) for asset in EXPECTED_LIKES),
            MallCheckoutOrderCreated(member_username=MALL_LOGIN_USERNAME, product_sn=PRODUCT_SN, quantity=1, expected_status=1, receiver_name="Taylor Nguyen"),
            AssetExists(EXPECTED_SMS, task=self),
        ]
