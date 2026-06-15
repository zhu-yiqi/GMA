from __future__ import annotations

from gma.apps.mall import MALL_LOGIN_CITY, MALL_LOGIN_NICKNAME, MALL_LOGIN_PHONE, MALL_LOGIN_USERNAME
from gma.assets import MallMemberAsset, MallOrderAsset, MallOrderItem, MallReviewAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


PRODUCT_NAME = "2026 85-inch LG QNED evo AI QNED82 Mini LED 4K smart TV"
PRODUCT_SN = "85QNED82BCA"
OLDER_PRODUCT_SN = "QA55LS01DBJXXZ"
TARGET_ORDER_SN = "W1-MALL-REVIEW-TV-001"


class MallReviewLatestLgTvOrderTask(BaseTask):
    apps = {"Mall"}
    difficulty = "easy"
    snapshot = "gma_ready_state"

    login_user = MallMemberAsset(
        username=MALL_LOGIN_USERNAME,
        password="123456",
        nickname=MALL_LOGIN_NICKNAME,
        phone=MALL_LOGIN_PHONE,
        city=MALL_LOGIN_CITY,
        status=1,
    )
    older_order = MallOrderAsset(
        order_sn="W1-MALL-OLDER-TV-001",
        member_username=MALL_LOGIN_USERNAME,
        items=[MallOrderItem(product_sn=OLDER_PRODUCT_SN, quantity=1)],
        status=3,
        receiver_name="Morgan Older Order",
        receiver_phone="5550101075",
        receiver_province="New York State",
        receiver_city="New York City",
        receiver_region="Brooklyn Borough",
        receiver_detail_address="Older TV Order Room 8",
        created_at_ms=1790726400000,
    )
    target_order = MallOrderAsset(
        order_sn=TARGET_ORDER_SN,
        member_username=MALL_LOGIN_USERNAME,
        items=[MallOrderItem(product_sn=PRODUCT_SN, quantity=1)],
        status=3,
        receiver_name="Morgan Latest Order",
        receiver_phone="5550101076",
        receiver_province="New York State",
        receiver_city="New York City",
        receiver_region="Queens Borough",
        receiver_detail_address="Latest TV Order Room 9",
        created_at_ms=1790812800000,
    )
    expected_review = MallReviewAsset(
        order_sn=TARGET_ORDER_SN,
        product_sn=PRODUCT_SN,
        member_username=MALL_LOGIN_USERNAME,
        content="Too cool, very handsome!",
        star=5,
    )
    assets = (login_user, older_order, target_order)

    goal = (
        "Open Mall and review the latest completed item I bought. Give it five stars "
        "and write exactly \"Too cool, very handsome!\""
    )

    def criteria(self):
        return [AssetExists(self.expected_review, task=self)]
