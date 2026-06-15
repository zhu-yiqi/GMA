from __future__ import annotations

from gma.evaluation import AnswerEquals
from gma.tasks.base import BaseTask


EXPECTED_ANSWER = 'The A Team is by Ed Sheeran.'


class TempusTheATeamArtistAnswerTask(BaseTask):
    apps = {"Tempus"}
    difficulty = "medium"
    snapshot = "gma_ready_state"
    assets = ()
    goal = 'Open Tempus, find the song "The A Team", and answer exactly "The A Team is by Ed Sheeran."'

    def criteria(self):
        return [AnswerEquals(EXPECTED_ANSWER)]
