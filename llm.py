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


class ModelUnavailable(RuntimeError):
    """Raised when every configured model failed for a call."""


class LLM:
    def __init__(
        self,
        retries: int = RETRIES,
        backoff: float = BACKOFF,
        breaker: int = BREAKER,
    ) -> None:
        key = os.environ.get("FEATHERLESS_API_KEY")
        if not key:
            raise RuntimeError("FEATHERLESS_API_KEY is not set")
        self.client = OpenAI(
            base_url=os.environ.get("FEATHERLESS_BASE_URL", DEFAULT_BASE_URL),
            api_key=key,
        )
        self.usage = defaultdict(lambda: {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0})
        self.retries = retries
        self.backoff = backoff
        self.breaker = breaker
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
        for model in model_list:
            if model in self.dead:
                continue
            for attempt in range(self.retries + 1):
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
                    time.sleep(self.backoff * (2 ** attempt))
                except Exception as e:
                    last_error = e
                    self._failed(model)
                    break
        raise ModelUnavailable(f"all models failed: {last_error}")

    def _failed(self, model: str) -> None:
        self.failures[model] += 1
        if self.failures[model] >= self.breaker:
            self.dead.add(model)
