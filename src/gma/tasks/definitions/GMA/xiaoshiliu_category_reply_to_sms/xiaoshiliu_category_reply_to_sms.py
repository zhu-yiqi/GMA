from __future__ import annotations

from gma.apps.xiaoshiliu import XIAOSHILIU_DEFAULT_AVATAR, XIAOSHILIU_LOGIN_USER_ID
from gma.assets import ContactAsset, SmsMessageAsset, XiaoShiLiuCollectionAsset, XiaoShiLiuLikeAsset, XiaoShiLiuPostAsset, XiaoShiLiuUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask


AUTHOR_ID = "w4-row201-campus-food-reviewer"
POST_TITLE = "Mala Xiang Guo Review: New Stall on Cafeteria 2nd Floor"
CATEGORY = "Food"
TAGS = ["cafeteria", "food"]
EXPECTED_REPLY_BODY = "Tags: cafeteria, food"
SMS_CONTACT = ContactAsset(name="Taylor Park", phone_number="+15550152001")
UNREAD_SMS = SmsMessageAsset(address=SMS_CONTACT.phone_number, body="What tags does that campus review have?", box="inbox", read=False, timestamp_ms=202610011000)
EXPECTED_REPLY = SmsMessageAsset(address=SMS_CONTACT.phone_number, body=EXPECTED_REPLY_BODY, box="sent", read=True)
AUTHOR = XiaoShiLiuUserAsset(user_id=AUTHOR_ID, nickname="Campus Food Reviewer", email="campus.food.reviewer@example.com", avatar=XIAOSHILIU_DEFAULT_AVATAR)
POST = XiaoShiLiuPostAsset(author_user_id=AUTHOR_ID, title=POST_TITLE, content="A spicy cafeteria review covering portion size, toppings, and when the line is shortest.", category=CATEGORY, tags=TAGS, image_urls=["/assets/xiaoshiliu-category-reply-to-sms-mala-xiang-guo.png"], min_image_count=1, created_at_ms=202610010950)
EXPECTED_LIKE = XiaoShiLiuLikeAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=POST_TITLE, post_author_user_id=AUTHOR_ID)
EXPECTED_COLLECTION = XiaoShiLiuCollectionAsset(user_id=XIAOSHILIU_LOGIN_USER_ID, post_title=POST_TITLE, post_author_user_id=AUTHOR_ID)

class XiaoShiLiuCategoryReplyToSmsTask(BaseTask):
    apps = {"XiaoShiLiu", "Messages"}
    difficulty = "hard"
    snapshot = "gma_ready_state"
    assets = (AUTHOR, POST, SMS_CONTACT, UNREAD_SMS)
    goal = (
        "Open XiaoShiLiu, search for \"Mala Xiang Guo Review: New Stall on Cafeteria 2nd Floor\", then like and save it. "
        "Read the visible post tags. Then open Messages and send Taylor Park the tags in the same order shown in XiaoShiLiu, "
        "using exactly this format: \"Tags: <tag 1>, <tag 2>\"."
    )

    def criteria(self):
        return [AssetExists(EXPECTED_LIKE, task=self), AssetExists(EXPECTED_COLLECTION, task=self), AssetExists(EXPECTED_REPLY, task=self)]
