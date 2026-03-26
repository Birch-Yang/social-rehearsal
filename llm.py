import json
import streamlit as st
from openai import OpenAI

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


def generate_conversation_map(prompt: str) -> dict:
    response = client.responses.create(
        model="gpt-5.4-mini",
        input=prompt
    )

    text = response.output_text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return {
            "recommended_opening": "Sorry — the model did not return valid JSON.",
            "tactical_advice": [],
            "risk_phrases": [],
            "response_paths": []
        }


def simulate_reply(system_prompt: str, chat_history: list[dict]) -> str:
    history_text = "\n".join(
        [f"{msg['role'].upper()}: {msg['content']}" for msg in chat_history]
    )

    full_prompt = f"""
{system_prompt}

Conversation so far:
{history_text}

Now continue the conversation as the other person.
Reply only with that person's next message.
"""

    response = client.responses.create(
        model="gpt-5.4-mini",
        input=full_prompt
    )

    return response.output_text.strip()