from __future__ import annotations

import re
from typing import Literal

from gma.evaluation.criteria import Criterion


class AnswerCriterion(Criterion):
    """Evaluate the terminal answer text reported by the agent or manual runner."""

    def __init__(
        self,
        expected: str,
        *,
        mode: Literal["equals", "contains", "regex"] = "equals",
        case_sensitive: bool = True,
        strip: bool = True,
        weight: float = 1.0,
    ):
        super().__init__(weight=weight)
        if mode not in {"equals", "contains", "regex"}:
            raise ValueError(f"Unsupported answer match mode: {mode}")
        self.expected = expected
        self.mode = mode
        self.case_sensitive = case_sensitive
        self.strip = strip

    @property
    def name(self) -> str:
        return f"{self.__class__.__name__}({self.expected})"

    def _normalize(self, value: object) -> str:
        text = "" if value is None else str(value)
        if self.strip:
            text = text.strip()
        if not self.case_sensitive:
            text = text.casefold()
        return text

    def evaluate(self, controller):
        try:
            terminal = controller.get_terminal_state()
        except AttributeError:
            return self._fail("controller does not expose terminal answer state")
        except Exception as exc:
            return self._fail(f"failed to read terminal answer state: {exc}")

        raw_answer = terminal.get("answer_text")
        if raw_answer is None:
            return self._fail("no answer submitted")

        actual = self._normalize(raw_answer)
        expected = self._normalize(self.expected)

        if self.mode == "equals":
            matched = actual == expected
        elif self.mode == "contains":
            matched = expected in actual
        else:
            flags = 0 if self.case_sensitive else re.IGNORECASE
            pattern = self.expected.strip() if self.strip else self.expected
            matched = re.search(pattern, actual, flags=flags) is not None

        if matched:
            return self._pass(f"answer matched: {raw_answer!r}")
        return self._fail(f"answer {raw_answer!r} did not {self.mode} {self.expected!r}")


class AnswerEquals(AnswerCriterion):
    """Pass when the submitted terminal answer exactly equals the expected text."""

    def __init__(
        self,
        expected: str,
        *,
        case_sensitive: bool = True,
        strip: bool = True,
        weight: float = 1.0,
    ):
        super().__init__(
            expected,
            mode="equals",
            case_sensitive=case_sensitive,
            strip=strip,
            weight=weight,
        )


class AnswerContains(AnswerCriterion):
    """Pass when the submitted terminal answer contains the expected text."""

    def __init__(
        self,
        expected: str,
        *,
        case_sensitive: bool = True,
        strip: bool = True,
        weight: float = 1.0,
    ):
        super().__init__(
            expected,
            mode="contains",
            case_sensitive=case_sensitive,
            strip=strip,
            weight=weight,
        )


class AnswerMatches(AnswerCriterion):
    """Pass when the submitted terminal answer matches a regular expression."""

    def __init__(
        self,
        pattern: str,
        *,
        case_sensitive: bool = True,
        strip: bool = True,
        weight: float = 1.0,
    ):
        super().__init__(
            pattern,
            mode="regex",
            case_sensitive=case_sensitive,
            strip=strip,
            weight=weight,
        )
