from __future__ import annotations

from gma.apps.meituan import MEITUAN_LOGIN_CITY, MEITUAN_LOGIN_USER_ID, MEITUAN_LOGIN_USERNAME
from gma.assets import CalendarEventAsset, ContactAsset, MeituanCollectionAsset, MeituanUserAsset, SmsMessageAsset
from gma.evaluation import AssetExists
from gma.tasks.base import BaseTask
from datetime import UTC, datetime

from gma.apps.travel import (
    TRAVEL_LOGIN_EMAIL,
    TRAVEL_LOGIN_FIRST_NAME,
    TRAVEL_LOGIN_LAST_NAME,
    TRAVEL_LOGIN_PASSWORD,
    TRAVEL_LOGIN_USERNAME,
    login_travel_app,
)
from gma.assets import TravelUserAsset

TRAVEL_USER = TravelUserAsset(
    email=TRAVEL_LOGIN_EMAIL,
    username=TRAVEL_LOGIN_USERNAME,
    password=TRAVEL_LOGIN_PASSWORD,
    first_name=TRAVEL_LOGIN_FIRST_NAME,
    last_name=TRAVEL_LOGIN_LAST_NAME,
)


def dt_ms(year: int, month: int, day: int, hour: int = 0, minute: int = 0) -> int:
    return int(datetime(year, month, day, hour, minute, tzinfo=UTC).timestamp() * 1000)


def open_travel(client) -> None:
    login_travel_app(
        client,
        email=TRAVEL_LOGIN_EMAIL,
        username=TRAVEL_LOGIN_USERNAME,
        password=TRAVEL_LOGIN_PASSWORD,
        ensure_user=False,
    )

EVENT = CalendarEventAsset(title="Small Gathering on May 16", start_ms=dt_ms(2027, 5, 16, 8, 30), end_ms=dt_ms(2027, 5, 16, 9), description="Remember to select the relevant package in advance and remind Bob of the exact location.", reminder_minutes=(0,), timezone="UTC")
BOB = ContactAsset(name="Bob", phone_number="+15552330233")
MESSAGE = "I found a great restaurant on Meituan: Mixue Ice Cream & Tea. I'd like to invite you to join me for tasting at 9:00 AM on May 16."
EXPECTED_SMS = SmsMessageAsset(address=BOB.phone_number, body=MESSAGE, box="sent", read=True)


class CalendarMeituanBobRestaurantInviteTask(BaseTask):
    apps = {"Calendar", "Meituan", "Messages"}
    difficulty = "hard"
    snapshot = "gma_ready_state"
    assets = (
        BOB,
        MeituanUserAsset(username=MEITUAN_LOGIN_USERNAME, password="123456", user_id=MEITUAN_LOGIN_USER_ID, city=MEITUAN_LOGIN_CITY, status=1),
    )
    goal = (
        'Open Calendar and create an event on May 16, 2027 titled "Small Gathering on May 16" with description "Remember to select the relevant package in advance and remind Bob of the exact location." Set it from 8:30 AM to 9:00 AM with an At start reminder. Then open Meituan, go to Fast Food, open the second Top Sales store, and bookmark it. Finally open Messages and send Bob a message in exactly this format: "I found a great restaurant on Meituan: <restaurant name>. I\'d like to invite you to join me for tasting at 9:00 AM on May 16." Use the name of that second Top Sales store for <restaurant name>.'
    )

    def criteria(self):
        return [
            AssetExists(EVENT, task=self),
            AssetExists(MeituanCollectionAsset(user_id=MEITUAN_LOGIN_USER_ID, restaurant_name="Mixue Ice Cream & Tea"), task=self),
            AssetExists(EXPECTED_SMS, task=self),
        ]
