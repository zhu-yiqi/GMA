from __future__ import annotations

from gma.apps.elementx import elementx_user_id
from gma.apps.xiaoshiliu import XIAOSHILIU_DEFAULT_AVATAR, XIAOSHILIU_LOGIN_USER_ID
from gma.assets import (
    ContactAsset,
    ElementXMessageAsset,
    ElementXRoomAsset,
    ElementXUserAsset,
    SmsMessageAsset,
    XiaoShiLiuCollectionAsset,
    XiaoShiLiuFollowAsset,
    XiaoShiLiuPostAsset,
    XiaoShiLiuUserAsset,
)
from gma.evaluation import AssetDeleted, AssetExists
from gma.tasks.base import BaseTask


DELETE_BODY = "Please delete this old dinner reminder."
REPLY_BODY = "I understand."
XSL_AUTHOR_ID = "campus-foodie-logan-hill"
XSL_AUTHOR_NAME = "Campus Foodie Logan Hill"
POST_TITLE = "Best Campus Lunch Photo Guide"
POST_CONTENT = "A quick look at my favorite campus lunch plate this week."
IMAGE_FILENAME = "campus-food-lunch.jpeg"
IMAGE_URL = f"/assets/{IMAGE_FILENAME}"
ELEMENTX_USER = "alex-parker-row240"
ELEMENTX_USER_ID = elementx_user_id(ELEMENTX_USER)
ELEMENTX_MESSAGE = "I've already read it, and I think it's great. You can check it out too."

class MessagesXslElementXFoodPostShareTask(BaseTask):
    apps = {"Messages", "XiaoShiLiu", "ElementX"}
    difficulty = "hard"
    snapshot = "gma_ready_state"

    delete_contact = ContactAsset(name="Henry Hayes", phone_number="+15552012400")
    delete_message = SmsMessageAsset(
        address=delete_contact.phone_number,
        body=DELETE_BODY,
        box="inbox",
        read=True,
    )
    second_contact = ContactAsset(name="Taylor Brooks", phone_number="+15552012401")
    second_message = SmsMessageAsset(
        address=second_contact.phone_number,
        body="Please confirm that you saw the recommendation.",
        box="inbox",
        read=False,
    )
    expected_reply = SmsMessageAsset(
        address=second_contact.phone_number,
        body=REPLY_BODY,
        box="sent",
        read=True,
    )
    xsl_author = XiaoShiLiuUserAsset(
        user_id=XSL_AUTHOR_ID,
        nickname=XSL_AUTHOR_NAME,
        email="campus-foodie-logan-hill@example.com",
        avatar=XIAOSHILIU_DEFAULT_AVATAR,
        bio="Campus food snapshots and simple recommendations.",
        location="Seed Campus",
        verified=False,
        is_active=True,
    )
    xsl_post = XiaoShiLiuPostAsset(
        author_user_id=XSL_AUTHOR_ID,
        title=POST_TITLE,
        content=POST_CONTENT,
        category="Food",
        tags=["campus", "food"],
        image_urls=[IMAGE_URL],
        min_image_count=1,
    )
    elementx_user = ElementXUserAsset(
        username=ELEMENTX_USER,
        password="password",
        display_name="Alex Parker",
    )
    assets = (delete_contact, delete_message, second_contact, second_message, xsl_author, xsl_post, elementx_user)

    goal = (
        f"Open Messages and delete the conversation with Henry Hayes that contains \"{DELETE_BODY}\". "
        f"Then send Taylor Brooks exactly \"{REPLY_BODY}\". Open XiaoShiLiu, "
        f"search for \"{XSL_AUTHOR_NAME}\", follow that blogger, and save the image post titled \"{POST_TITLE}\". "
        f"Finally open ElementX, start a direct message with Alex Parker, and send exactly \"{ELEMENTX_MESSAGE}\"."
    )

    def criteria(self):
        return [
            AssetDeleted(self.delete_message, task=self),
            AssetExists(self.expected_reply, task=self),
            AssetExists(
                XiaoShiLiuFollowAsset(
                    follower_user_id=XIAOSHILIU_LOGIN_USER_ID,
                    following_user_id=XSL_AUTHOR_ID,
                ),
                task=self,
            ),
            AssetExists(
                XiaoShiLiuCollectionAsset(
                    user_id=XIAOSHILIU_LOGIN_USER_ID,
                    post_title=POST_TITLE,
                    post_author_user_id=XSL_AUTHOR_ID,
                ),
                task=self,
            ),
            AssetExists(
                ElementXRoomAsset(
                    name="Alex Parker",
                    room_type="dm",
                    creator_username="testuser",
                    creator_password="testpass123",
                    members=[ELEMENTX_USER],
                ),
                task=self,
            ),
            AssetExists(
                ElementXMessageAsset(
                    room=ELEMENTX_USER_ID,
                    sender_username="testuser",
                    sender_password="testpass123",
                    text=ELEMENTX_MESSAGE,
                ),
                task=self,
            ),
        ]
