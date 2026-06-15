
from __future__ import annotations

from gma.assets import ElementXPollAsset, ElementXPollResponse, ElementXRoomAsset, ElementXSessionAsset, ElementXUserAsset
from gma.evaluation import AnswerEquals, AssetExists
from gma.tasks.base import BaseTask


ANSWER = "First Group: Pizza 2, Salad 1; Second Group: Tea 1, Coffee 2; Third Group: Library 3, Cafe 0"
FIRST_ALIAS = "w2-row129-first-group"


class ElementXFirstThreePollResultsCreateDuckPollTask(BaseTask):
    apps = {"ElementX"}
    difficulty = "medium"
    snapshot = "gma_ready_state"

    users = (
        ElementXUserAsset(username="w2-row129-alex", password="password", display_name="Alex"),
        ElementXUserAsset(username="w2-row129-blair", password="password", display_name="Blair"),
        ElementXUserAsset(username="w2-row129-casey", password="password", display_name="Casey"),
    )
    first_room = ElementXRoomAsset(name="First Group", room_type="group", creator_username="testuser", creator_password="testpass123", members=["w2-row129-alex", "w2-row129-blair", "w2-row129-casey"], alias_localpart=FIRST_ALIAS)
    second_room = ElementXRoomAsset(name="Second Group", room_type="group", creator_username="testuser", creator_password="testpass123", members=["w2-row129-alex", "w2-row129-blair", "w2-row129-casey"], alias_localpart="w2-row129-second-group")
    third_room = ElementXRoomAsset(name="Third Group", room_type="group", creator_username="testuser", creator_password="testpass123", members=["w2-row129-alex", "w2-row129-blair", "w2-row129-casey"], alias_localpart="w2-row129-third-group")
    poll_one = ElementXPollAsset(room=FIRST_ALIAS, sender_username="w2-row129-alex", sender_password="password", question="Dinner preference", options=["Pizza", "Salad"], responses=[ElementXPollResponse(username="w2-row129-alex", option="Pizza"), ElementXPollResponse(username="w2-row129-blair", option="Pizza"), ElementXPollResponse(username="w2-row129-casey", option="Salad")])
    poll_two = ElementXPollAsset(room="w2-row129-second-group", sender_username="w2-row129-blair", sender_password="password", question="Drink preference", options=["Tea", "Coffee"], responses=[ElementXPollResponse(username="w2-row129-alex", option="Tea"), ElementXPollResponse(username="w2-row129-blair", option="Coffee"), ElementXPollResponse(username="w2-row129-casey", option="Coffee")])
    poll_three = ElementXPollAsset(room="w2-row129-third-group", sender_username="w2-row129-casey", sender_password="password", question="Study place", options=["Library", "Cafe"], responses=[ElementXPollResponse(username="w2-row129-alex", option="Library"), ElementXPollResponse(username="w2-row129-blair", option="Library"), ElementXPollResponse(username="w2-row129-casey", option="Library")])
    expected_poll = ElementXPollAsset(room=FIRST_ALIAS, sender_username="testuser", sender_password="testpass123", question="What to eat tonight", options=["half a roast duck", "the other half"])
    assets = (*users, first_room, second_room, third_room, poll_one, poll_two, poll_three, ElementXSessionAsset(username="testuser", password="testpass123"))

    goal = (
        "Open ElementX and enter the first three group chats respectively. View their previous poll results and keep the results for your final response. "
        "Then select the first group chat and create a new poll titled exactly \"What to eat tonight\" with option 1 exactly \"half a roast duck\" and option 2 exactly \"the other half\". "
        "After creating the poll, answer with the vote counts from the previous polls in the first group chat first, then the second group chat, and finally the third group chat, using the format \"<group name>: <option> <count>, <option> <count>; ...\"."
    )

    def criteria(self):
        return [AnswerEquals(ANSWER), AssetExists(self.expected_poll, task=self)]
