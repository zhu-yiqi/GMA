from __future__ import annotations

from gma.evaluation import AnswerEquals
from gma.tasks.base import BaseTask


EXPECTED_ANSWER = 'Lego House is in the album +.'


class TempusLegoHouseAlbumAnswerTask(BaseTask):
    apps = {"Tempus"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = ()
    goal = 'Open Tempus, find the song "Lego House", and answer exactly "Lego House is in the album +."'

    def criteria(self):
        return [AnswerEquals(EXPECTED_ANSWER)]
