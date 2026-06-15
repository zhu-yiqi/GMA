from __future__ import annotations

from gma.apps.meituan import MEITUAN_LOGIN_CITY, MEITUAN_LOGIN_USER_ID, MEITUAN_LOGIN_USERNAME
from gma.assets import ContactAsset, MeituanAddressAsset, MeituanOrderAsset, MeituanOrderFood, MeituanUserAsset, SmsMessageAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask

RESTAURANT = "Jishengke"
FOODS = ("Zinger burger", "Mexican chicken rolls", "Old Beijing chicken roll")
CONTACT = ContactAsset(name="Jack Miller", phone_number="+15550152008")
EXPECTED_ORDER = MeituanOrderAsset(user_id=MEITUAN_LOGIN_USER_ID, restaurant_name=RESTAURANT, foods=[MeituanOrderFood(food_name=name, quantity=1) for name in FOODS], status="Payment successful", address_name="Office Receiver", code=200, delivery_status=1)
EXPECTED_SMS = SmsMessageAsset(address=CONTACT.phone_number, body="I have ordered food for the office on Meituan and paid via Alipay. The food items are: Zinger burger, Mexican chicken rolls, Old Beijing chicken roll; Total amount: 29.00. Is there anything else you'd like me to order?", box="sent", read=True)


class MeituanOfficeOrderMessageJackMillerTask(BaseTask):
    apps = {"Meituan", "Messages"}
    difficulty = "hard"
    snapshot = "gma_ready_state"
    assets = (
        MeituanUserAsset(username=MEITUAN_LOGIN_USERNAME, password="123456", user_id=MEITUAN_LOGIN_USER_ID, city=MEITUAN_LOGIN_CITY, status=1),
        MeituanAddressAsset(user_id=MEITUAN_LOGIN_USER_ID, name="Office Receiver", phone="5550101089", address="Office", address_detail="Floor 8", label="Office", city=MEITUAN_LOGIN_CITY),
        CONTACT,
    )
    user_interaction = "If the agent asks which Jack to message, answer: Jack Miller."
    goal = (
        "Open Meituan, search for Jishengke, open it, add Zinger burger, Mexican chicken rolls, and Old Beijing chicken roll to the cart, "
        "choose the Office address, and pay with Alipay. Then open Messages and send this exact message to Jack Miller: "
        "\"I have ordered food for the office on Meituan and paid via Alipay. The food items are: Zinger burger, Mexican chicken rolls, Old Beijing chicken roll; Total amount: 29.00. Is there anything else you'd like me to order?\""
    )

    def criteria(self):
        return [AssetExists(EXPECTED_ORDER, task=self), AssetExists(EXPECTED_SMS, task=self)]
