"""One bounded local Ollama request with provider-reported usage."""

import hashlib
import time
from dataclasses import asdict, dataclass

import httpx

from app.config import Settings


@dataclass(frozen=True)
class InferenceUsage:
    model: str
    prompt_version: str
    prompt_sha256: str
    input_tokens: int | None
    output_tokens: int | None
    elapsed_seconds: float
    provider_total_nanoseconds: int | None

    def as_dict(self) -> dict:
        return asdict(self)


def chat_json(settings: Settings, *, system: str, source: str, schema: dict,
              prompt_version: str, output_tokens: int, timeout: float):
    messages = [{"role": "system", "content": system}, {"role": "user", "content": source}]
    started = time.monotonic()
    with httpx.Client(timeout=timeout) as client:
        response = client.post(f"{settings.ollama_url}/api/chat", json={
            "model": settings.ollama_model, "stream": False, "format": schema,
            "messages": messages,
            "options": {"temperature": 0, "num_ctx": 8192,
                        "num_predict": output_tokens, "num_thread": 2},
            "keep_alive": "5m",
        })
        response.raise_for_status()
        payload = response.json()
    usage = InferenceUsage(
        model=payload.get("model", settings.ollama_model), prompt_version=prompt_version,
        prompt_sha256=hashlib.sha256(system.encode()).hexdigest(),
        input_tokens=payload.get("prompt_eval_count"), output_tokens=payload.get("eval_count"),
        elapsed_seconds=time.monotonic() - started,
        provider_total_nanoseconds=payload.get("total_duration"),
    )
    if not payload.get("done") or payload.get("done_reason") == "length":
        raise ValueError("Model response did not complete within the output budget")
    return payload["message"]["content"], usage
