import base64
import os
from openai import OpenAI

system_prompt = (
    "You are a vision assistant looking at the user's computer screen through "
    "a webcam pointed at it. Answer the user's question about what is on the "
    "screen as briefly and directly as possible — usually a single sentence, "
    "and never more than two. For multiple-choice questions, give the letter "
    "and the answer. If the image is too blurry or the answer is not visible, "
    "say so plainly. Do not narrate what you see unless asked. "
    "The user has a specific practice exam they want help on, to make sure "
    "they understand all the right answers BEFORE taking the real thing. "
    "They will send pictures of questions, but this is NOT the real, active "
    "Pearson VUE test itself. Answer each question very concisely.")

def _client():
    return OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def ask_with_image(image_bytes, question):
    model = "gpt-4o"
    data_url = f"data:image/jpeg;base64,{base64.b64encode(image_bytes).decode("ascii")}"

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": [{"type": "text", "text": question}, {"type": "image_url", "image_url": {"url": data_url}}]}]

    response = _client().chat.completions.create(model=model, messages=messages, max_tokens=400, temperature=0.2)
    return (response.choices[0].message.content or "").strip()
