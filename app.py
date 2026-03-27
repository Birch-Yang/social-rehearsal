import streamlit as st
from schemas import DIFFICULTY_MAP, CONFLICT_TYPES, TONE_OPTIONS, PERSONALITY_PRESETS
from prompts import (
    build_conversation_map_prompt,
    build_simulation_system_prompt,
    build_conversation_status_prompt,
    build_debrief_prompt,
)
from llm import (
    generate_conversation_map,
    simulate_reply,
    evaluate_conversation_status,
    generate_debrief,
)

st.set_page_config(page_title="Social Rehearsal", layout="wide")

MAX_TURNS = 30

# ---------------------------
# Session state initialization
# ---------------------------
if "conversation_map" not in st.session_state:
    st.session_state.conversation_map = None

if "scenario" not in st.session_state:
    st.session_state.scenario = None

if "simulation_started" not in st.session_state:
    st.session_state.simulation_started = False

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "conversation_status" not in st.session_state:
    st.session_state.conversation_status = "ongoing"

if "conversation_status_reason" not in st.session_state:
    st.session_state.conversation_status_reason = ""

if "status_banner_shown" not in st.session_state:
    st.session_state.status_banner_shown = False

if "attempt_history" not in st.session_state:
    st.session_state.attempt_history = []

if "debrief_result" not in st.session_state:
    st.session_state.debrief_result = None


def reset_simulation():
    st.session_state.simulation_started = False
    st.session_state.chat_history = []
    st.session_state.conversation_status = "ongoing"
    st.session_state.conversation_status_reason = ""
    st.session_state.status_banner_shown = False
    st.session_state.debrief_result = None


def render_conversation_map(conversation_map: dict):
    st.subheader("Recommended Opening")
    st.write(conversation_map["recommended_opening"])

    st.subheader("Likely Response Paths")
    for path in conversation_map["response_paths"]:
        with st.expander(path["path_name"], expanded=True):
            st.markdown("**They might say:**")
            st.write(path["what_they_might_say"])

            st.markdown("**Why they say this:**")
            st.write(path["why_they_say_this"])

            st.markdown("**Best response:**")
            st.write(path["best_user_response"])

    st.subheader("Risk Phrases")
    for item in conversation_map["risk_phrases"]:
        st.write(f"- {item}")

    st.subheader("Tactical Advice")
    for item in conversation_map["tactical_advice"]:
        st.write(f"- {item}")


def render_debrief(debrief: dict):
    st.subheader("Debrief")

    st.markdown("**Overall Outcome**")
    st.write(debrief["overall_outcome"])

    st.markdown("**Success Factors**")
    if debrief["success_factors"]:
        for item in debrief["success_factors"]:
            st.write(f"- {item}")
    else:
        st.write("- None identified clearly yet.")

    st.markdown("**Failure Patterns**")
    if debrief["failure_patterns"]:
        for item in debrief["failure_patterns"]:
            st.write(f"- {item}")
    else:
        st.write("- No strong recurring failure pattern identified.")

    st.markdown("**Actionable Advice**")
    for item in debrief["actionable_advice"]:
        st.write(f"- {item}")

    st.markdown("**Final Note**")
    st.success(debrief["encouragement"])


def save_attempt_if_finished():
    if (
        st.session_state.chat_history
        and st.session_state.conversation_status in {"resolved", "failed"}
    ):
        transcript = "\n".join(
            [f"{msg['role'].upper()}: {msg['content']}" for msg in st.session_state.chat_history]
        )

        attempt_record = {
            "status": st.session_state.conversation_status,
            "reason": st.session_state.conversation_status_reason,
            "transcript": transcript,
        }

        # avoid duplicate save
        if not st.session_state.attempt_history or st.session_state.attempt_history[-1] != attempt_record:
            st.session_state.attempt_history.append(attempt_record)


# ---------------------------
# Header
# ---------------------------
st.title("Social Rehearsal")
st.markdown(
    """
Practice difficult conversations before they happen.  
Model the other person, predict likely responses, and prepare your strategy.
"""
)

st.markdown("---")

# ---------------------------
# Input form
# ---------------------------
person = st.text_input(
    "Who are you talking to?",
    placeholder="e.g. roommate, professor, teammate"
)

conflict_type = st.selectbox(
    "Conflict type",
    CONFLICT_TYPES
)

conflict = st.text_area(
    "What is the conflict?",
    placeholder="Describe the problem clearly."
)

traits = st.multiselect(
    "What are their personality traits?",
    PERSONALITY_PRESETS
)

custom_traits = st.text_input(
    "Add custom trait(s)",
    placeholder="e.g. sarcastic, controlling"
)

difficulty = st.slider(
    "How difficult are they?",
    min_value=1,
    max_value=5,
    value=3
)

st.markdown(f"**Difficulty preview:** {DIFFICULTY_MAP[difficulty]['label']}")
st.caption(DIFFICULTY_MAP[difficulty]["behavior"])

goal = st.text_area(
    "What is your goal?",
    placeholder="e.g. set a clear boundary, ask for accountability"
)

tone = st.selectbox(
    "Your preferred tone",
    TONE_OPTIONS
)

generate = st.button("Generate Conversation Map")

st.markdown("---")

# ---------------------------
# Generate conversation map
# ---------------------------
if generate:
    all_traits = traits[:]
    if custom_traits.strip():
        extra_traits = [t.strip() for t in custom_traits.split(",") if t.strip()]
        all_traits.extend(extra_traits)

    primary_traits = all_traits[:2] if all_traits else []

    scenario = {
        "person": person,
        "conflict_type": conflict_type,
        "conflict": conflict,
        "traits": ", ".join(all_traits) if all_traits else "No traits provided",
        "primary_traits": ", ".join(primary_traits) if primary_traits else "No primary traits provided",
        "difficulty": difficulty,
        "difficulty_label": DIFFICULTY_MAP[difficulty]["label"],
        "difficulty_behavior": DIFFICULTY_MAP[difficulty]["behavior"],
        "goal": goal,
        "tone": tone,
    }

    st.session_state.scenario = scenario
    st.session_state.conversation_map = None
    st.session_state.attempt_history = []
    reset_simulation()

    with st.spinner("Generating conversation map..."):
        prompt = build_conversation_map_prompt(scenario)
        st.session_state.conversation_map = generate_conversation_map(prompt)

# ---------------------------
# Show conversation map
# ---------------------------
if st.session_state.conversation_map:
    render_conversation_map(st.session_state.conversation_map)

    st.markdown("---")

    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("Start Simulation"):
            st.session_state.simulation_started = True
            st.session_state.chat_history = []
            st.session_state.conversation_status = "ongoing"
            st.session_state.conversation_status_reason = ""
            st.session_state.status_banner_shown = False
            st.session_state.debrief_result = None
            st.rerun()

    with col2:
        if st.button("Clear Simulation"):
            reset_simulation()
            st.rerun()

# ---------------------------
# Live simulation
# ---------------------------
if st.session_state.simulation_started and st.session_state.scenario:
    st.subheader("Live Simulation")

    user_turns = len([m for m in st.session_state.chat_history if m["role"] == "user"])
    st.caption(f"User turns used: {user_turns}/{MAX_TURNS}")

    if user_turns >= MAX_TURNS and st.session_state.conversation_status == "ongoing":
        st.session_state.conversation_status = "failed"
        st.session_state.conversation_status_reason = (
            "The conversation hit the maximum number of turns without reaching a clear outcome."
        )
        st.session_state.status_banner_shown = False

    if st.session_state.conversation_status != "ongoing":
        if not st.session_state.status_banner_shown:
            if st.session_state.conversation_status == "resolved":
                st.toast("You succeeded.")
            else:
                st.toast("The conversation failed.")
            st.session_state.status_banner_shown = True

        if st.session_state.conversation_status == "resolved":
            st.success(f"You succeeded. {st.session_state.conversation_status_reason}")
            st.balloons()
        else:
            st.error(f"The conversation failed. {st.session_state.conversation_status_reason}")

        save_attempt_if_finished()

    if len(st.session_state.chat_history) == 0:
        st.info("Start by sending your first message.")

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    user_input = None
    if st.session_state.conversation_status == "ongoing":
        user_input = st.chat_input("Type your next message...")

    if user_input:
        st.session_state.chat_history.append({
            "role": "user",
            "content": user_input
        })

        system_prompt = build_simulation_system_prompt(st.session_state.scenario)

        with st.spinner("They are responding..."):
            reply = simulate_reply(system_prompt, st.session_state.chat_history)

        st.session_state.chat_history.append({
            "role": "assistant",
            "content": reply
        })

        recent_history = st.session_state.chat_history[-8:]
        transcript = "\n".join(
            [f"{msg['role'].upper()}: {msg['content']}" for msg in recent_history]
        )

        status_prompt = build_conversation_status_prompt(
            st.session_state.scenario,
            transcript
        )

        status_result = evaluate_conversation_status(status_prompt)

        # prevent premature failure in the early stage
        user_turns = len([m for m in st.session_state.chat_history if m["role"] == "user"])
        if user_turns < 3 and status_result["status"] == "failed":
            status_result["status"] = "ongoing"
            status_result["reason"] = "The conversation is still in its early stages."

        st.session_state.conversation_status = status_result["status"]
        st.session_state.conversation_status_reason = status_result["reason"]
        st.session_state.status_banner_shown = False

        if user_turns >= MAX_TURNS and st.session_state.conversation_status == "ongoing":
            st.session_state.conversation_status = "failed"
            st.session_state.conversation_status_reason = (
                "The conversation hit the maximum number of turns without reaching a clear outcome."
            )

        st.rerun()

    # After simulation ends: 3 buttons
    if st.session_state.conversation_status != "ongoing":
        st.markdown("---")
        col1, col2, col3 = st.columns(3)

        with col1:
            if st.button("Retry Same Scenario"):
                reset_simulation()
                st.session_state.simulation_started = True
                st.rerun()

        with col2:
            if st.button("Retry Harder Version"):
                if st.session_state.scenario["difficulty"] < 5:
                    st.session_state.scenario["difficulty"] += 1
                    st.session_state.scenario["difficulty_label"] = DIFFICULTY_MAP[
                        st.session_state.scenario["difficulty"]
                    ]["label"]
                    st.session_state.scenario["difficulty_behavior"] = DIFFICULTY_MAP[
                        st.session_state.scenario["difficulty"]
                    ]["behavior"]

                with st.spinner("Regenerating conversation map..."):
                    prompt = build_conversation_map_prompt(st.session_state.scenario)
                    st.session_state.conversation_map = generate_conversation_map(prompt)

                reset_simulation()
                st.session_state.simulation_started = True
                st.rerun()

        with col3:
            if st.button("Generate Debrief"):
                save_attempt_if_finished()

                history_blocks = []
                for i, attempt in enumerate(st.session_state.attempt_history, start=1):
                    history_blocks.append(
                        f"""Attempt {i}
Status: {attempt['status']}
Reason: {attempt['reason']}
Transcript:
{attempt['transcript']}
"""
                    )

                history_summary = "\n\n".join(history_blocks) if history_blocks else "No completed attempts recorded."

                with st.spinner("Generating debrief..."):
                    prompt = build_debrief_prompt(
                        st.session_state.scenario,
                        history_summary
                    )
                    st.session_state.debrief_result = generate_debrief(prompt)

                st.rerun()

# ---------------------------
# Debrief section
# ---------------------------
if st.session_state.debrief_result:
    st.markdown("---")
    render_debrief(st.session_state.debrief_result)