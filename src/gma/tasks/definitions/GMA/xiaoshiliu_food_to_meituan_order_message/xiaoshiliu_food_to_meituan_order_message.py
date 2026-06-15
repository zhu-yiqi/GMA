from __future__ import annotations

from gma.apps.meituan import MEITUAN_LOGIN_CITY, MEITUAN_LOGIN_USER_ID, MEITUAN_LOGIN_USERNAME
from gma.apps.xiaoshiliu import XIAOSHILIU_DEFAULT_AVATAR, XIAOSHILIU_LOGIN_USER_ID
from gma.assets import ContactAsset, MeituanAddressAsset, MeituanOrderAsset, MeituanOrderFood, MeituanUserAsset, SmsMessageAsset, XiaoShiLiuCommentAsset, XiaoShiLiuPostAsset, XiaoShiLiuUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


AUTHOR_ID = "w4-row202-food-finder"
TARGET_TITLE = "Zinger Burger Recommendation"
RECOMMENDED_FOOD = "Zinger burger"
COMMENT_TEXT = "Which one is the most delicious?"
RESTAURANT = "Jishengke"
FOODS = ("Zinger burger", "Mexican chicken rolls", "Old Beijing chicken roll")
CONTACT = ContactAsset(name="Food Friend", phone_number="5550101003")
EXPECTED_SMS = SmsMessageAsset(address=CONTACT.phone_number, body="Let me treat you to this food.", box="sent", read=True)
AUTHOR = XiaoShiLiuUserAsset(user_id=AUTHOR_ID, nickname="Food Finder", email="food-finder-row202@example.com", avatar=XIAOSHILIU_DEFAULT_AVATAR)
DISTRACTOR_POST = XiaoShiLiuPostAsset(author_user_id=AUTHOR_ID, title="Campus Sandwich Notes", content="A quick sandwich note for another lunch option.", category="Food", tags=["food"], image_urls=["/assets/xiaoshiliu-food-to-meituan-order-message-sandwich.png"], min_image_count=1, created_at_ms=1790845200000)
TARGET_POST = XiaoShiLiuPostAsset(author_user_id=AUTHOR_ID, title=TARGET_TITLE, content="Recommended food name: Zinger burger. It works well with the next two listed menu items.", category="Food", tags=["food", "curry"], image_urls=["/assets/xiaoshiliu-food-to-meituan-order-message-curry-rice.png"], min_image_count=1, created_at_ms=1790845500000)
EXPECTED_COMMENT = XiaoShiLiuCommentAsset(post_title=TARGET_TITLE, post_author_user_id=AUTHOR_ID, author_user_id=XIAOSHILIU_LOGIN_USER_ID, content=COMMENT_TEXT)
EXPECTED_ORDER = MeituanOrderAsset(
    user_id=MEITUAN_LOGIN_USER_ID,
    restaurant_name=RESTAURANT,
    foods=[MeituanOrderFood(food_name=name, quantity=1) for name in FOODS],
    status="Payment successful",
    address_name="Default Office Receiver",
    code=200,
    delivery_status=1,
)

class XiaoShiLiuFoodToMeituanOrderMessageTask(BaseTask):
    apps = {"XiaoShiLiu", "Meituan", "Messages"}
    difficulty = "hard"
    snapshot = "gma_ready_state"
    assets = (
        AUTHOR,
        DISTRACTOR_POST,
        TARGET_POST,
        MeituanUserAsset(username=MEITUAN_LOGIN_USERNAME, password="123456", user_id=MEITUAN_LOGIN_USER_ID, city=MEITUAN_LOGIN_CITY, status=1),
        MeituanAddressAsset(user_id=MEITUAN_LOGIN_USER_ID, name="Default Office Receiver", phone="5550101125", address="Office Tower", address_detail="18F", label="Office", city=MEITUAN_LOGIN_CITY),
        CONTACT,
    )
    goal = (
        'Open XiaoShiLiu, search for "food", open the first result, read the recommended food name, '
        'and comment "Which one is the most delicious?". Then open Meituan, search for that recommended food, open the matching restaurant, '
        'add the recommended food and the next two listed menu items from that restaurant to the cart, place the order using the default Office address, and pay with Alipay. '
        'Finally open Messages and send "Let me treat you to this food." to 5550101003.'
    )

    def criteria(self):
        return [AssetExists(EXPECTED_COMMENT, task=self), AssetExists(EXPECTED_ORDER, task=self), AssetExists(EXPECTED_SMS, task=self)]
