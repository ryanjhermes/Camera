"""OpenAI vision chat helper."""

from __future__ import annotations

import base64
import os
from typing import Iterable, Literal, TypedDict

from openai import OpenAI


SYSTEM_PROMPT = (
    "You are a vision assistant looking at the user's computer screen through "
    "a webcam pointed at it. Answer the user's question about what is on the "
    "screen as briefly and directly as possible — usually a single sentence, "
    "and never more than two. For multiple-choice questions, give the letter "
    "and the answer. If the image is too blurry or the answer is not visible, "
    "say so plainly. Do not narrate what you see unless asked."
)

INITIAL_USER_MESSAGE = (
    "I have a specific practice exam I want your help on, to help me make "
    "sure I understand all the right answers to questions BEFORE I take the "
    "real thing. To make sure it's clear what will be happening, I'll be "
    "sending you pictures of questions I want help on, but this is NOT the "
    "real, active Pearson VUE test itself. Answer each question very "
    "concisely."
)


class ChatTurn(TypedDict):
    role: Literal["user", "assistant"]
    content: str


def _client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Add it to .env or export it in your shell."
        )
    return OpenAI(api_key=api_key)


def ask_with_image(
    *,
    image_bytes: bytes,
    history: Iterable[ChatTurn],
    question: str,
    model: str | None = None,
) -> str:
    """Send the chat history + a fresh user turn (text+image) to OpenAI.

    The image is re-attached to the latest user turn on every call so the
    model can keep examining it for follow-up questions.
    """
    model = model or os.getenv("OPENAI_MODEL", "gpt-4o")
    b64 = base64.b64encode(image_bytes).decode("ascii")
    data_url = f"data:image/jpeg;base64,{b64}"

    messages: list[dict] = [{"role": "system", "content": SYSTEM_PROMPT}]
    for turn in history:
        messages.append({"role": turn["role"], "content": turn["content"]})

    messages.append(
        {
            "role": "user",
            "content": [
                {"type": "text", "text": question},
                {"type": "image_url", "image_url": {"url": data_url}},
            ],
        }
    )

    resp = _client().chat.completions.create(
        model=model,
        messages=messages,
        max_tokens=400,
        temperature=0.2,
    )
    return (resp.choices[0].message.content or "").strip()
