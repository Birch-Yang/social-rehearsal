import json
import re
import streamlit as st
from openai import OpenAI

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])


def _safe_json_loads(text: str, fallback: dict) -> dict:
    text = text.strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    match = re.search(r"\{.*\}", text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(0))
        except json.JSONDecodeError:
            pass

    return fallback


def generate_conversation_map(prompt: str) -> dict:
    response = client.responses.create(
        model="gpt-5.4-mini",
        input=prompt
    )

    text = response.output_text.strip()

    fallback = {
        "recommended_opening": "Sorry — the model did not return valid JSON.",
        "tactical_advice": [],
        "risk_phrases": [],
        "response_paths": []
    }

    return _safe_json_loads(text, fallback)


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


def evaluate_conversation_status(prompt: str) -> dict:
    try:
        response = client.responses.create(
            model="gpt-5.4-mini",
            input=prompt
        )

        text = response.output_text.strip()

        fallback = {
            "status": "ongoing",
            "reason": "Could not reliably evaluate conversation status.",
            "tension_delta": 0
        }

        result = _safe_json_loads(text, fallback)

        if result.get("status") not in {"ongoing", "resolved", "failed"}:
            return fallback

        if "reason" not in result or not isinstance(result["reason"], str):
            result["reason"] = "No reason provided."

        if result.get("tension_delta") not in {-2, -1, 0, 1, 2}:
            result["tension_delta"] = 0

        return result

    except Exception:
        return {
            "status": "ongoing",
            "reason": "Status evaluation temporarily failed, so the conversation will continue.",
            "tension_delta": 0
        }


def generate_debrief(prompt: str) -> dict:
    response = client.responses.create(
        model="gpt-5.4-mini",
        input=prompt
    )

    text = response.output_text.strip()

    fallback = {
        "overall_outcome": "Unresolved",
        "scores": {
            "clarity": 4,
            "assertiveness": 4,
            "strategy": 4,
            "tone": 4
        },
        "success_factors": [],
        "failure_patterns": [],
        "actionable_advice": [
            "Try to stay specific about the behavior you want changed."
        ],
        "encouragement": "Good luck — you have a clearer plan now."
    }

    result = _safe_json_loads(text, fallback)

    scores = result.get("scores", {})
    normalized_scores = {
        "clarity": scores.get("clarity", 4),
        "assertiveness": scores.get("assertiveness", 4),
        "strategy": scores.get("strategy", 4),
        "tone": scores.get("tone", 4),
    }

    for key, value in normalized_scores.items():
        if not isinstance(value, int):
            normalized_scores[key] = 4
        else:
            normalized_scores[key] = max(0, min(8, value))

    result["scores"] = normalized_scores

    result.setdefault("overall_outcome", fallback["overall_outcome"])
    result.setdefault("success_factors", [])
    result.setdefault("failure_patterns", [])
    result.setdefault("actionable_advice", fallback["actionable_advice"])
    result.setdefault("encouragement", fallback["encouragement"])

    return result