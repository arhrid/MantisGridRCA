from __future__ import annotations

import os
import re
import time
from collections import defaultdict

from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI


DEFAULT_BASE_URL = "https://api.featherless.ai/v1"
RETRIES = 2
BACKOFF = 1.0
BREAKER = 2
REQUEST_TIMEOUT_S = 20.0
CALL_WALL_LIMIT_S = 50.0


class ModelUnavailable(RuntimeError):
    """Raised when every configured model failed for a call."""


class LLM:
    def __init__(
        self,
        retries: int = RETRIES,
        backoff: float = BACKOFF,
        breaker: int = BREAKER,
        request_timeout_s: float = REQUEST_TIMEOUT_S,
        call_wall_limit_s: float = CALL_WALL_LIMIT_S,
    ) -> None:
        key = os.environ.get("FEATHERLESS_API_KEY")
        if not key:
            raise RuntimeError("FEATHERLESS_API_KEY is not set")
        self.client = OpenAI(
            base_url=os.environ.get("FEATHERLESS_BASE_URL", DEFAULT_BASE_URL),
            api_key=key,
            timeout=float(os.environ.get("FEATHERLESS_TIMEOUT_S", request_timeout_s)),
        )
        self.usage = defaultdict(lambda: {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0})
        self.retries = retries
        self.backoff = backoff
        self.breaker = breaker
        self.call_wall_limit_s = float(os.environ.get("RCA_LLM_CALL_WALL_S", call_wall_limit_s))
        self.dead: set[str] = set()
        self.failures: dict[str, int] = defaultdict(int)

    def ask(
        self,
        models: str | list[str],
        prompt: str | list[dict],
        max_tokens: int = 600,
        temperature: float = 0.1,
    ) -> str:
        model_list = [models] if isinstance(models, str) else list(models)
        messages = [{"role": "user", "content": prompt}] if isinstance(prompt, str) else prompt
        last_error: Exception | None = None
        deadline = time.monotonic() + self.call_wall_limit_s
        for model in model_list:
            if time.monotonic() >= deadline:
                break
            if model in self.dead:
                continue
            for attempt in range(self.retries + 1):
                if time.monotonic() >= deadline:
                    break
                try:
                    resp = self.client.chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    if isinstance(resp, dict) and resp.get("error"):
                        raise RuntimeError(resp["error"])
                    if getattr(resp, "error", None):
                        raise RuntimeError(resp.error)
                    if not getattr(resp, "choices", None):
                        raise ModelUnavailable("response had no choices")
                    text = resp.choices[0].message.content or ""
                    usage = getattr(resp, "usage", None)
                    rec = self.usage[model]
                    rec["calls"] += 1
                    rec["prompt_tokens"] += int(getattr(usage, "prompt_tokens", 0) or 0)
                    rec["completion_tokens"] += int(getattr(usage, "completion_tokens", 0) or 0)
                    return re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
                except APIStatusError as e:
                    last_error = e
                    self._failed(model)
                    break
                except (APIConnectionError, APITimeoutError, ModelUnavailable, RuntimeError) as e:
                    last_error = e
                    self._failed(model)
                    if model in self.dead or attempt >= self.retries:
                        break
                    time.sleep(min(self.backoff * (2 ** attempt), max(0.0, deadline - time.monotonic())))
                except Exception as e:
                    last_error = e
                    self._failed(model)
                    break
        raise ModelUnavailable(f"all models failed: {last_error}")

    def _failed(self, model: str) -> None:
        self.failures[model] += 1
        if self.failures[model] >= self.breaker:
            self.dead.add(model)
