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
MAX_TENSION = 8


# ---------------------------
# Session state initialization
# ---------------------------
def init_session_state():
    defaults = {
        "current_step": 1,  # 1 Setup, 2 Map, 3 Simulation, 4 Debrief
        "scenario": None,
        "conversation_map": None,
        "simulation_started": False,
        "chat_history": [],
        "conversation_status": "ongoing",
        "conversation_status_reason": "",
        "status_banner_shown": False,
        "attempt_history": [],
        "debrief_result": None,
        "tension": 0,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def get_initial_tension(scenario: dict | None) -> int:
    if not scenario:
        return 0

    difficulty = scenario.get("difficulty", 3)

    if difficulty == 1:
        return 1
    elif difficulty == 2:
        return 2
    elif difficulty == 3:
        return 3
    elif difficulty == 4:
        return 4
    else:
        return 5


def reset_simulation_only():
    st.session_state.simulation_started = False
    st.session_state.chat_history = []
    st.session_state.conversation_status = "ongoing"
    st.session_state.conversation_status_reason = ""
    st.session_state.status_banner_shown = False
    st.session_state.debrief_result = None
    st.session_state.tension = get_initial_tension(st.session_state.scenario)


def reset_all():
    st.session_state.current_step = 1
    st.session_state.scenario = None
    st.session_state.conversation_map = None
    st.session_state.simulation_started = False
    st.session_state.chat_history = []
    st.session_state.conversation_status = "ongoing"
    st.session_state.conversation_status_reason = ""
    st.session_state.status_banner_shown = False
    st.session_state.attempt_history = []
    st.session_state.debrief_result = None
    st.session_state.tension = 0


init_session_state()


# ---------------------------
# Helpers
# ---------------------------
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

        if not st.session_state.attempt_history or st.session_state.attempt_history[-1] != attempt_record:
            st.session_state.attempt_history.append(attempt_record)


def render_step_header(step_num: int, title: str):
    st.title("Social Rehearsal")
    st.caption(f"Step {step_num} of 4 — {title}")


def render_tension_meter(tension: int, max_tension: int = MAX_TENSION):
    block_html = []
    for i in range(max_tension):
        if i < tension:
            bg = "#f3f3f3"
            border = "#f3f3f3"
        else:
            bg = "transparent"
            border = "#9a9a9a"

        block_html.append(
            f'<div style="width:22px;height:22px;border:1px solid {border};background:{bg};display:inline-block;margin-right:4px;border-radius:3px;"></div>'
        )

    blocks = "".join(block_html)

    html = f"""
<div style="background:#2b2b2f;border-radius:24px;padding:20px 24px;margin:8px 0 18px 0;">
    <div style="color:white;font-size:18px;display:flex;align-items:center;gap:16px;flex-wrap:wrap;">
        <span style="min-width:90px;font-weight:600;">Tension:</span>
        <div style="display:flex;align-items:center;">{blocks}</div>
        <span style="font-size:14px;opacity:0.8;">{tension}/{max_tension}</span>
    </div>
</div>
"""
    st.markdown(html, unsafe_allow_html=True)
    
def render_score_bar(label: str, score: int, max_score: int = 8):
    block_html = []
    for i in range(max_score):
        if i < score:
            bg = "#f3f3f3"
            border = "#f3f3f3"
        else:
            bg = "transparent"
            border = "#9a9a9a"

        block_html.append(
            f'<div style="width:18px;height:18px;border:1px solid {border};background:{bg};display:inline-block;margin-right:4px;border-radius:3px;"></div>'
        )

    blocks = "".join(block_html)

    html = f"""
<div style="background:#2b2b2f;border-radius:18px;padding:14px 18px;margin:8px 0;">
    <div style="color:white;font-size:16px;display:flex;align-items:center;gap:14px;flex-wrap:wrap;">
        <span style="min-width:110px;font-weight:600;">{label}:</span>
        <div style="display:flex;align-items:center;">{blocks}</div>
        <span style="font-size:13px;opacity:0.8;">{score}/{max_score}</span>
    </div>
</div>
"""
    st.markdown(html, unsafe_allow_html=True)


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
    if conversation_map["risk_phrases"]:
        for item in conversation_map["risk_phrases"]:
            st.write(f"- {item}")
    else:
        st.write("No risk phrases generated.")

    st.subheader("Tactical Advice")
    if conversation_map["tactical_advice"]:
        for item in conversation_map["tactical_advice"]:
            st.write(f"- {item}")
    else:
        st.write("No tactical advice generated.")


def render_debrief(debrief: dict):
    st.subheader("Debrief")

    st.markdown("**Overall Outcome**")
    st.write(debrief["overall_outcome"])

    scores = debrief.get("scores", {})
    st.markdown("**Performance Breakdown**")
    render_score_bar("Clarity", scores.get("clarity", 4))
    render_score_bar("Assertiveness", scores.get("assertiveness", 4))
    render_score_bar("Strategy", scores.get("strategy", 4))
    render_score_bar("Tone", scores.get("tone", 4))

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


def build_history_summary() -> str:
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
    return "\n\n".join(history_blocks) if history_blocks else "No completed attempts recorded."


# ---------------------------
# Page 1: Setup
# ---------------------------
def render_setup_page():
    render_step_header(1, "Setup")
    st.markdown(
        """
Practice difficult conversations before they happen.  
Model the other person, predict likely responses, simulate the interaction, and learn from it.
"""
    )
    st.markdown("---")

    scenario = st.session_state.scenario or {}

    existing_traits = []
    if scenario.get("traits") and scenario.get("traits") != "No traits provided":
        existing_traits = [t.strip() for t in scenario["traits"].split(",") if t.strip()]

    preset_defaults = [t for t in existing_traits if t in PERSONALITY_PRESETS]
    custom_defaults = [t for t in existing_traits if t not in PERSONALITY_PRESETS]

    person = st.text_input(
        "Who are you talking to?",
        value=scenario.get("person", ""),
        placeholder="e.g. roommate, professor, teammate"
    )

    conflict_type_default = scenario.get("conflict_type", CONFLICT_TYPES[0])
    conflict_type_index = CONFLICT_TYPES.index(conflict_type_default) if conflict_type_default in CONFLICT_TYPES else 0
    conflict_type = st.selectbox(
        "Conflict type",
        CONFLICT_TYPES,
        index=conflict_type_index
    )

    conflict = st.text_area(
        "What is the conflict?",
        value=scenario.get("conflict", ""),
        placeholder="Describe the problem clearly."
    )

    traits = st.multiselect(
        "What are their personality traits?",
        PERSONALITY_PRESETS,
        default=preset_defaults
    )

    custom_traits = st.text_input(
        "Add custom trait(s)",
        value=", ".join(custom_defaults),
        placeholder="e.g. sarcastic, controlling"
    )

    difficulty = st.slider(
        "How difficult are they?",
        min_value=1,
        max_value=5,
        value=scenario.get("difficulty", 3)
    )

    st.markdown(f"**Difficulty preview:** {DIFFICULTY_MAP[difficulty]['label']}")
    st.caption(DIFFICULTY_MAP[difficulty]["behavior"])

    goal = st.text_area(
        "What is your goal?",
        value=scenario.get("goal", ""),
        placeholder="e.g. set a clear boundary, ask for accountability"
    )

    tone_default = scenario.get("tone", TONE_OPTIONS[0])
    tone_index = TONE_OPTIONS.index(tone_default) if tone_default in TONE_OPTIONS else 0
    tone = st.selectbox(
        "Your preferred tone",
        TONE_OPTIONS,
        index=tone_index
    )

    st.markdown("---")
    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("Generate Conversation Map", use_container_width=True):
            all_traits = traits[:]
            if custom_traits.strip():
                extra_traits = [t.strip() for t in custom_traits.split(",") if t.strip()]
                all_traits.extend(extra_traits)

            primary_traits = all_traits[:2] if all_traits else []

            new_scenario = {
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

            st.session_state.scenario = new_scenario
            st.session_state.conversation_map = None
            st.session_state.attempt_history = []
            reset_simulation_only()

            with st.spinner("Generating conversation map..."):
                prompt = build_conversation_map_prompt(new_scenario)
                st.session_state.conversation_map = generate_conversation_map(prompt)

            st.session_state.current_step = 2
            st.rerun()

    with col2:
        if st.button("Start Over", use_container_width=True):
            reset_all()
            st.rerun()


# ---------------------------
# Page 2: Conversation Map
# ---------------------------
def render_map_page():
    render_step_header(2, "Conversation Map")
    st.markdown("---")

    if not st.session_state.conversation_map:
        st.warning("No conversation map found yet. Please generate one first.")
        if st.button("Back to Setup"):
            st.session_state.current_step = 1
            st.rerun()
        return

    render_conversation_map(st.session_state.conversation_map)

    st.markdown("---")
    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("Back", use_container_width=True):
            st.session_state.current_step = 1
            st.rerun()

    with col2:
        if st.button("Continue to Simulation", use_container_width=True):
            st.session_state.current_step = 3
            st.session_state.simulation_started = True
            st.rerun()


# ---------------------------
# Page 3: Simulation
# ---------------------------
def render_simulation_page():
    render_step_header(3, "Simulation")
    st.markdown("---")

    if not st.session_state.scenario or not st.session_state.conversation_map:
        st.warning("You need to complete the earlier steps first.")
        if st.button("Back to Setup"):
            st.session_state.current_step = 1
            st.rerun()
        return

    if not st.session_state.simulation_started:
        st.session_state.simulation_started = True

    scenario = st.session_state.scenario

    st.markdown(
        f"""
You are now talking to a simulated **{scenario['person']}**.  
Your goal is to **{scenario['goal']}**. Try to succeed within **{MAX_TURNS} turns**.
"""
    )

    render_tension_meter(st.session_state.tension, MAX_TENSION)

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
                st.toast("The conversation ended.")
            st.session_state.status_banner_shown = True

        if st.session_state.conversation_status == "resolved":
            st.success(f"You succeeded. {st.session_state.conversation_status_reason}")
        else:
            st.error(f"The conversation ended. {st.session_state.conversation_status_reason}")

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

        recent_history = st.session_state.chat_history[-6:]
        transcript = "\n".join(
            [f"{msg['role'].upper()}: {msg['content']}" for msg in recent_history]
        )

        status_prompt = build_conversation_status_prompt(
            st.session_state.scenario,
            transcript,
            st.session_state.tension,
            MAX_TENSION
        )
        status_result = evaluate_conversation_status(status_prompt)

        user_turns = len([m for m in st.session_state.chat_history if m["role"] == "user"])
        if user_turns < 2 and status_result["status"] == "failed":
            status_result["status"] = "ongoing"
            status_result["reason"] = "The conversation is still too early to count as a clear failure."

        tension_delta = status_result.get("tension_delta", 0)
        difficulty = st.session_state.scenario.get("difficulty", 3)

        if difficulty <= 2:
            tension_delta = max(-2, min(1, tension_delta))
        elif difficulty == 3:
            tension_delta = max(-2, min(2, tension_delta))
        elif difficulty >= 4:
            tension_delta = max(-1, min(2, tension_delta))

        st.session_state.tension = max(
            0,
            min(MAX_TENSION, st.session_state.tension + tension_delta)
        )

        st.session_state.conversation_status = status_result["status"]
        st.session_state.conversation_status_reason = status_result["reason"]
        st.session_state.status_banner_shown = False

        if (
            st.session_state.tension >= MAX_TENSION
            and st.session_state.conversation_status == "ongoing"
        ):
            st.session_state.conversation_status = "failed"
            st.session_state.conversation_status_reason = (
                "The conversation hit a breaking point after tension reached its maximum."
            )

        if user_turns >= MAX_TURNS and st.session_state.conversation_status == "ongoing":
            st.session_state.conversation_status = "failed"
            st.session_state.conversation_status_reason = (
                "The conversation hit the maximum number of turns without reaching a clear outcome."
            )

        st.rerun()

    st.markdown("---")

    if st.session_state.conversation_status == "ongoing":
        col1, col2 = st.columns(2)

        with col1:
            if st.button("Back", use_container_width=True):
                st.session_state.current_step = 2
                st.rerun()

        with col2:
            if st.button("Force End", use_container_width=True):
                st.session_state.conversation_status = "failed"
                st.session_state.conversation_status_reason = (
                    "The simulation was ended manually before a clear resolution was reached."
                )
                st.session_state.status_banner_shown = False
                save_attempt_if_finished()
                st.rerun()

    else:
        col1, col2 = st.columns(2)

        with col1:
            if st.button("Back", use_container_width=True):
                st.session_state.current_step = 2
                st.rerun()

        with col2:
            if st.button("Continue to Debrief", use_container_width=True):
                save_attempt_if_finished()

                if not st.session_state.debrief_result:
                    history_summary = build_history_summary()
                    with st.spinner("Generating debrief..."):
                        prompt = build_debrief_prompt(
                            st.session_state.scenario,
                            history_summary
                        )
                        st.session_state.debrief_result = generate_debrief(prompt)

                st.session_state.current_step = 4
                st.rerun()

        st.markdown("")

        col3, col4 = st.columns(2)

        with col3:
            if st.button("Retry Same Scenario", use_container_width=True):
                reset_simulation_only()
                st.session_state.simulation_started = True
                st.rerun()

        with col4:
            if st.button("Retry Harder Version", use_container_width=True):
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

                reset_simulation_only()
                st.session_state.simulation_started = True
                st.rerun()


# ---------------------------
# Page 4: Debrief
# ---------------------------
def render_debrief_page():
    render_step_header(4, "Debrief")
    st.markdown("---")

    if not st.session_state.debrief_result:
        st.warning("No debrief found yet. Finish a simulation first.")
        col1, col2 = st.columns([1, 1])
        with col1:
            if st.button("Back to Simulation", use_container_width=True):
                st.session_state.current_step = 3
                st.rerun()
        with col2:
            if st.button("Start Over", use_container_width=True):
                reset_all()
                st.rerun()
        return

    render_debrief(st.session_state.debrief_result)

    st.markdown("---")
    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("Back", use_container_width=True):
            st.session_state.current_step = 3
            st.rerun()

    with col2:
        if st.button("Start Over", use_container_width=True):
            reset_all()
            st.rerun()


# ---------------------------
# Router
# ---------------------------
if st.session_state.current_step == 1:
    render_setup_page()
elif st.session_state.current_step == 2:
    render_map_page()
elif st.session_state.current_step == 3:
    render_simulation_page()
elif st.session_state.current_step == 4:
    render_debrief_page()
else:
    reset_all()
    render_setup_page()