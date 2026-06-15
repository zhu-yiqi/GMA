from __future__ import annotations

from gma.apps.meituan import MEITUAN_LOGIN_CITY, MEITUAN_LOGIN_USER_ID, MEITUAN_LOGIN_USERNAME
from gma.assets import MailAccountAsset, MailMessageAsset, MeituanAddressAsset, MeituanCollectionAsset, MeituanOrderAsset, MeituanOrderFood, MeituanUserAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask

RESTAURANT = "CHAGEE"
FOOD = "boya vast string"
ACCOUNT = MailAccountAsset(display_name="Avery Cole", email="avery.cole@example.com")
EXPECTED_MAIL = MailMessageAsset(mailbox="sent", from_name=ACCOUNT.display_name, from_email="test@gmail.com", to=["dfg@gmail.com"], subject="Price", body="17.00", read=True)
EXPECTED_ORDER = MeituanOrderAsset(user_id=MEITUAN_LOGIN_USER_ID, restaurant_name=RESTAURANT, foods=[MeituanOrderFood(food_name=FOOD, quantity=1)], status="Payment successful", address_name="Default Delivery Receiver", code=200, delivery_status=1)


class MeituanBoyaVastStringMailPriceTask(BaseTask):
    apps = {"Meituan", "Mail"}
    difficulty = "hard"
    snapshot = "gma_ready_state"
    assets = (
        MeituanUserAsset(username=MEITUAN_LOGIN_USERNAME, password="123456", user_id=MEITUAN_LOGIN_USER_ID, city=MEITUAN_LOGIN_CITY, status=1),
        MeituanAddressAsset(user_id=MEITUAN_LOGIN_USER_ID, name="Default Delivery Receiver", phone="5550101082", address="Default Delivery", address_detail="Room 230", label="Home", city=MEITUAN_LOGIN_CITY),
        ACCOUNT,
    )
    goal = (
        'Open Meituan, search for "boya vast string", favorite CHAGEE if it is not already favorited, and order one boya vast string using the default address and default delivery time, and pay with Alipay. '
        'Read the item price. Then open Mail and send an email to dfg@gmail.com with subject "Price" and a body containing only the price in exactly this format: "<price>".'
    )

    def criteria(self):
        return [
            AssetExists(MeituanCollectionAsset(user_id=MEITUAN_LOGIN_USER_ID, restaurant_name=RESTAURANT), task=self),
            AssetExists(EXPECTED_ORDER, task=self),
            AssetExists(EXPECTED_MAIL, task=self),
        ]
