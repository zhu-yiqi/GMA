"""Task-scoped LLM user simulator for controlled clarification tasks."""

from __future__ import annotations

import re
import time
import json
from dataclasses import dataclass, field
from typing import Any

from loguru import logger
from openai import OpenAI


@dataclass
class UserSimulationRule:
    """One response hint/rule for a simulated user."""

    response: str
    when: str | list[str] | None = None
    match: str = "contains"
    max_uses: int | None = None
    uses: int = 0

    @classmethod
    def from_payload(cls, payload: Any) -> "UserSimulationRule":
        if isinstance(payload, str):
            return cls(response=payload, when=None, match="always")
        if not isinstance(payload, dict):
            raise TypeError(f"Invalid user simulation rule: {payload!r}")
        response = payload.get("response", payload.get("reply", payload.get("answer")))
        if response is None:
            raise ValueError(f"User simulation rule missing response/reply/answer: {payload!r}")
        when = payload.get(
            "when",
            payload.get("question_contains", payload.get("question_regex")),
        )
        match = payload.get("match", "contains")
        if payload.get("question_regex") is not None:
            match = "regex"
        return cls(
            response=str(response),
            when=when,
            match=str(match).lower(),
            max_uses=payload.get("max_uses"),
        )

    def matches(self, question: str) -> bool:
        if self.max_uses is not None and self.uses >= self.max_uses:
            return False
        if self.match == "always" or self.when in (None, "", []):
            return True
        values = self.when if isinstance(self.when, list) else [self.when]
        if self.match == "exact":
            return any(question.strip().lower() == str(value).strip().lower() for value in values)
        if self.match == "regex":
            return any(re.search(str(value), question, flags=re.IGNORECASE) for value in values)
        return any(str(value).lower() in question.lower() for value in values)

    def consume(self) -> str:
        self.uses += 1
        return self.response

    def to_prompt_dict(self) -> dict[str, Any]:
        return {
            "when": self.when,
            "match": self.match,
            "response": self.response,
            "max_uses": self.max_uses,
            "uses": self.uses,
        }


@dataclass
class UserSimulator:
    """LLM-backed user simulator driven by task.user_interaction metadata.

    The task metadata is a compact natural-language contract. The model decides
    whether the simulated user should respond and what to say. Legacy
    user_simulation dict support is kept only for existing hand-written tasks.
    """

    instructions: str = ""
    private_facts: dict[str, Any] = field(default_factory=dict)
    response_policy: str = ""
    default_response: str = ""
    max_turns: int = 5
    rules: list[UserSimulationRule] = field(default_factory=list)
    history: list[dict[str, str]] = field(default_factory=list)
    last_response_info: dict[str, Any] = field(default_factory=dict)
    model_name: str = ""
    llm_base_url: str = ""
    api_key: str = ""
    temperature: float = 0.2
    max_tokens: int = 256
    timeout: float = 60.0
    retries: int = 2
    _client: OpenAI | None = field(default=None, init=False, repr=False)

    @classmethod
    def from_task(cls, task: Any, **kwargs: Any) -> "UserSimulator":
        payload = getattr(task, "user_interaction", None)
        if payload is None:
            payload = getattr(task, "user_simulation", None)
        return cls.from_payload(payload, **kwargs)

    @classmethod
    def from_payload(cls, payload: Any, **kwargs: Any) -> "UserSimulator":
        if payload is None:
            return cls(**_filter_init_kwargs(kwargs))
        if isinstance(payload, str):
            return cls(instructions=payload, **_filter_init_kwargs(kwargs))
        if not isinstance(payload, dict):
            raise TypeError(f"user_interaction/user_simulation must be a dict, string, or None, got {type(payload)!r}")

        raw_rules = (
            payload.get("responses")
            or payload.get("rules")
            or payload.get("answers")
            or []
        )
        if isinstance(raw_rules, dict):
            raw_rules = [
                {"when": key, "response": value}
                for key, value in raw_rules.items()
            ]
        elif isinstance(raw_rules, (str, bytes)):
            raw_rules = [str(raw_rules)]

        private_facts = dict(payload.get("private_facts", payload.get("facts", {})) or {})
        response_policy = str(payload.get("response_policy", payload.get("policy", "")))
        instructions = str(payload.get("user_interaction", payload.get("instructions", "")))
        if private_facts:
            instructions += "\nPrivate facts the simulated user may reveal if appropriate: "
            instructions += json.dumps(private_facts, ensure_ascii=False)
        if response_policy:
            instructions += "\nResponse policy: " + response_policy

        return cls(
            instructions=instructions.strip(),
            private_facts=private_facts,
            response_policy=response_policy,
            default_response=str(payload.get("default_response", payload.get("fallback_response", ""))),
            max_turns=int(payload.get("max_turns", 5)),
            rules=[UserSimulationRule.from_payload(item) for item in raw_rules],
            **_filter_init_kwargs(kwargs),
        )

    def respond(self, question: str) -> str:
        fallback_response = self._fallback_response(question)
        if len(self.history) >= self.max_turns:
            response = ""
            info = {
                "source": "max_turns",
                "should_respond": False,
                "reason": "maximum simulated-user turns reached",
            }
        else:
            decision = self._llm_decision(question, fallback_response)
            if decision is None:
                response = fallback_response
                info = {
                    "source": "fallback",
                    "should_respond": bool(response),
                    "reason": "LLM unavailable or returned an invalid decision",
                }
            else:
                response = decision["response"] if decision["should_respond"] else ""
                info = decision
        self.history.append(
            {
                "question": question,
                "response": response,
                "fallback_response": fallback_response,
                "source": str(info.get("source", "")),
                "should_respond": str(info.get("should_respond", "")),
            }
        )
        self.last_response_info = {
            **info,
            "response": response,
            "fallback_response": fallback_response,
        }
        return response

    @property
    def enabled(self) -> bool:
        return bool(self.instructions or self.private_facts or self.response_policy or self.rules)

    @property
    def llm_enabled(self) -> bool:
        return bool(self.model_name and self.llm_base_url)

    def _fallback_response(self, question: str) -> str:
        response = self.default_response
        for rule in self.rules:
            if rule.matches(question):
                response = rule.consume()
                break
        return response

    def _llm_decision(self, question: str, fallback_response: str) -> dict[str, Any] | None:
        if not self.llm_enabled:
            return None
        messages = self._build_messages(question, fallback_response)
        for attempt in range(self.retries):
            try:
                response = self._get_client().chat.completions.create(
                    model=self.model_name,
                    messages=messages,
                    temperature=self.temperature,
                    max_tokens=self.max_tokens,
                )
                content = response.choices[0].message.content or ""
                decision = self._parse_decision(content)
                if decision is not None:
                    decision["source"] = "llm"
                    return decision
            except Exception as exc:
                logger.warning(
                    "User simulator LLM call failed "
                    f"(attempt {attempt + 1}/{self.retries}): {exc}"
                )
                if attempt < self.retries - 1:
                    time.sleep(1)
        return None

    def _get_client(self) -> OpenAI:
        if self._client is None:
            self._client = OpenAI(
                base_url=self.llm_base_url,
                api_key=self.api_key or "empty",
                timeout=self.timeout,
            )
        return self._client

    def _build_messages(self, question: str, fallback_response: str) -> list[dict[str, str]]:
        contract = {
            "user_interaction": self.instructions,
            "max_turns": self.max_turns,
            "history": self.history,
            "legacy_response_hints_for_fallback_only": [rule.to_prompt_dict() for rule in self.rules],
            "fallback_response_if_llm_unavailable": fallback_response,
        }
        system = (
            "You are the simulated human user in a mobile benchmark task. "
            "Use only the task contract provided by the benchmark. Decide "
            "whether the user should respond to the agent question. Do not solve "
            "the task, do not operate the phone, do not mention policies, and do "
            "not say you are simulated. If the question asks for information the "
            "contract does not allow the user to provide, set should_respond to "
            "false. Return JSON only, with keys: should_respond (boolean), "
            "response (string), and reason (short string).\n\n"
            "High-level examples:\n"
            "- If the contract says the user knows the target room and the agent "
            "asks which room to use, answer with that room.\n"
            "- If the contract says the agent must discover a verification code "
            "from Messages and the agent asks the user for the code directly, set "
            "should_respond=false.\n"
            "- If the agent asks for information unrelated to the task contract, "
            "set should_respond=false."
        )
        user = (
            "Task user-simulation contract:\n"
            f"{json.dumps(contract, ensure_ascii=False, indent=2)}\n\n"
            "Agent question:\n"
            f"{question}\n\n"
            "Decide whether the user should respond, and if so what the user says."
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ]

    def _parse_decision(self, content: str) -> dict[str, Any] | None:
        text = content.strip()
        if not text:
            return None
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        try:
            payload = json.loads(text)
        except json.JSONDecodeError:
            return {
                "should_respond": True,
                "response": text,
                "reason": "LLM returned plain text instead of JSON",
            }
        if not isinstance(payload, dict):
            return None
        should_respond = bool(payload.get("should_respond", payload.get("respond", True)))
        response = str(payload.get("response", payload.get("answer", ""))).strip()
        if should_respond and not response:
            return None
        return {
            "should_respond": should_respond,
            "response": response if should_respond else "",
            "reason": str(payload.get("reason", "")),
        }


def _filter_init_kwargs(kwargs: dict[str, Any]) -> dict[str, Any]:
    allowed = {
        "model_name",
        "llm_base_url",
        "api_key",
        "temperature",
        "max_tokens",
        "timeout",
        "retries",
    }
    return {key: value for key, value in kwargs.items() if key in allowed}
