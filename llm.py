import base64
import os
from openai import OpenAI

def _client():
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def ask_with_image(image_bytes, question):
    model = "gpt-4o"
    data_url = f"data:image/jpeg;base64,{base64.b64encode(image_bytes).decode("ascii")}"

    messages = [
        {"role": "system", "content": os.getenv("SYSTEM_PROMPT")},
        {"role": "user", "content": [{"type": "text", "text": question}, {"type": "image_url", "image_url": {"url": data_url}}]}]

    response = _client().chat.completions.create(model=model, messages=messages, max_tokens=400, temperature=0.2)
    return (response.choices[0].message.content or "").strip()
