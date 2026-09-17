from __future__ import annotations

import os
import time
from collections import defaultdict

from openai import OpenAI


class LLM:
    def __init__(self) -> None:
        self.client = OpenAI(
            base_url=os.environ.get("FEATHERLESS_BASE_URL", "https://api.featherless.ai/v1"),
            api_key=os.environ["FEATHERLESS_API_KEY"],
        )
        self.usage = defaultdict(lambda: {"prompt_tokens": 0, "completion_tokens": 0, "calls": 0})
        self.dead: set[str] = set()
        self.failures: dict[str, int] = defaultdict(int)

    def ask(self, models: list[str], prompt: str, max_tokens: int = 600, temperature: float = 0.1) -> str:
        last_error: Exception | None = None
        for model in models:
            if model in self.dead:
                continue
            for attempt in range(2):
                try:
                    resp = self.client.chat.completions.create(
                        model=model,
                        messages=[{"role": "user", "content": prompt}],
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    if isinstance(resp, dict) and resp.get("error"):
                        raise RuntimeError(resp["error"])
                    if getattr(resp, "error", None):
                        raise RuntimeError(resp.error)
                    text = resp.choices[0].message.content or ""
                    usage = getattr(resp, "usage", None)
                    rec = self.usage[model]
                    rec["calls"] += 1
                    rec["prompt_tokens"] += int(getattr(usage, "prompt_tokens", 0) or 0)
                    rec["completion_tokens"] += int(getattr(usage, "completion_tokens", 0) or 0)
                    return text
                except Exception as e:
                    last_error = e
                    self.failures[model] += 1
                    if self.failures[model] >= 2:
                        self.dead.add(model)
                    time.sleep(0.5 * (attempt + 1))
                    break
        raise RuntimeError(f"all models failed: {last_error}")
