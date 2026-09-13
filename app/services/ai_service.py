from openai import OpenAI

from app.core.config import settings

client = OpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=settings.AI_API_KEY,
)


def generate_chat_response(user_text: str, user_id: str) -> str:
    prompt = user_text.strip()
    if not prompt:
        return "[Bot]: Please send a message."

    try:
        response = client.chat.completions.create(
            model="gemini-2.5-flash",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt},
            ],
        )
        answer = response.choices[0].message.content
        if answer and answer.strip():
            return answer.strip()
    except Exception as e:
        print(f"[llm error]: {e}")

    return "[Bot]: Sorry, I couldn't generate a response right now."
