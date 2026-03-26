import streamlit as st
from schemas import DIFFICULTY_MAP, CONFLICT_TYPES, TONE_OPTIONS, PERSONALITY_PRESETS
from prompts import build_conversation_map_prompt, build_simulation_system_prompt
from llm import generate_conversation_map, simulate_reply

st.set_page_config(page_title="Social Rehearsal", layout="wide")

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
        all_traits.append(custom_traits.strip())

    scenario = {
        "person": person,
        "conflict_type": conflict_type,
        "conflict": conflict,
        "traits": ", ".join(all_traits) if all_traits else "No traits provided",
        "difficulty": difficulty,
        "difficulty_label": DIFFICULTY_MAP[difficulty]["label"],
        "difficulty_behavior": DIFFICULTY_MAP[difficulty]["behavior"],
        "goal": goal,
        "tone": tone,
    }

    st.session_state.scenario = scenario
    st.session_state.simulation_started = False
    st.session_state.chat_history = []

    with st.spinner("Generating conversation map..."):
        prompt = build_conversation_map_prompt(scenario)
        st.session_state.conversation_map = generate_conversation_map(prompt)

# ---------------------------
# Show conversation map
# ---------------------------
if st.session_state.conversation_map:
    conversation_map = st.session_state.conversation_map

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

    st.markdown("---")

    col1, col2 = st.columns([1, 1])

    with col1:
        if st.button("Start Simulation"):
            st.session_state.simulation_started = True
            st.session_state.chat_history = []
            st.rerun()

    with col2:
        if st.button("Clear Simulation"):
            st.session_state.simulation_started = False
            st.session_state.chat_history = []
            st.rerun()

# ---------------------------
# Live simulation
# ---------------------------
if st.session_state.simulation_started and st.session_state.scenario:
    st.subheader("Live Simulation")

    if len(st.session_state.chat_history) == 0:
        st.info("Start by sending your first message.")

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

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

        st.rerun()