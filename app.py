import html
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
# Global styling
# ---------------------------
def inject_global_css():
    st.markdown(
        """
        <style>
        :root{
            --bg:#FCFBFA;
            --text:#313348;
            --muted:#6F7387;
            --line:#E6E0E4;

            --card:#FCFBFA;
            --card-border:#DDD8DB;

            --green-soft:#EAF3EA;
            --green-main:#7EA273;

            --orange-soft:#F8E7DA;
            --orange-main:#E08038;

            --gray-soft:#ECEBEF;
            --gray-main:#8D8999;

            --button-main:#A7B8AA;
            --button-main-dark:#99AC9C;

            --input-bg:rgba(255,255,255,0.82);
            --input-border:#D7D1D5;
        }

        html, body, [data-testid="stAppViewContainer"], .stApp {
    background: var(--bg) !important;
}

        .block-container {
            padding-top: 4.8rem;
            padding-bottom: 2rem;
            max-width: 1280px;
        }

        .sr-top-title {
            font-size: 3.8rem !important;
            font-weight: 800 !important;
            line-height: 1.02 !important;
            margin: 0 0 0.7rem 0 !important;
            color: var(--text) !important;
            letter-spacing: -0.04em !important;
        }

        .sr-step {
            font-size: 1.15rem !important;
            color: var(--muted) !important;
            margin-bottom: 1.55rem !important;
            font-weight: 500 !important;
        }

        .sr-lead {
    font-size: 1.18rem !important;
    color: #4B4F63 !important;
    line-height: 1.75 !important;
    max-width: 980px !important;
    margin-bottom: 0.9rem !important;
}

        .sr-card {
            background: var(--card);
            border: 1px solid var(--card-border);
            border-radius: 18px;
            box-shadow: 0 1px 0 rgba(0,0,0,0.02);
            padding: 1.2rem 1.25rem;
        }

        .sr-soft-card {
            background: rgba(255,255,255,0.68);
            border: 1px solid var(--card-border);
            border-radius: 18px;
            padding: 1.15rem 1.2rem;
        }

        .sr-divider {
            border-top: 1px solid var(--line);
            margin: 1rem 0 1rem 0;
        }

        .sr-page-spacer {
            height: 10px;
        }

        .sr-dot {
            width: 15px;
            height: 15px;
            border-radius: 999px;
            display: inline-block;
            flex: 0 0 15px;
        }

        .sr-dot-person { background: #9AA89B; }
        .sr-dot-situation { background: #9CB7C7; }

        .sr-panel-title {
            font-size: 1.45rem;
            font-weight: 800;
            margin-bottom: 1.2rem;
            display: flex;
            align-items: center;
            gap: 0.65rem;
            color: var(--text);
        }

        .sr-custom-traits-label {
            font-size: 0.98rem;
            color: var(--muted);
            margin-top: 0.2rem;
            margin-bottom: 0.35rem;
        }

        .sr-difficulty-title {
            font-size: 1.03rem;
            font-weight: 800;
            margin-bottom: 0.45rem;
        }

        .sr-difficulty-label {
            font-size: 1.02rem;
            font-weight: 700;
            margin-bottom: 0.3rem;
        }

        .sr-difficulty-desc {
            font-size: 0.99rem;
            color: #5D6478;
            line-height: 1.65;
        }

        /* ===== Step 1 layout ===== */
.sr-left-card-marker,
.sr-right-card-marker,
.sr-footer-marker,
.sr-traits-box-marker,
.sr-difficulty-box-marker {
    display: none;
}

/* 让左右两列顶部对齐 */
div[data-testid="stHorizontalBlock"] {
    align-items: stretch !important;
}

/* 真正卡片：只作用于 container(border=True) 生成的 wrapper */
div[data-testid="stVerticalBlockBorderWrapper"]:has(.sr-left-card-marker) {
    background: #F2F7F1 !important;
    border: 1px solid var(--card-border) !important;
    border-radius: 22px !important;
    padding: 0.35rem !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.sr-right-card-marker) {
    background: #F3F7FC !important;
    border: 1px solid var(--card-border) !important;
    border-radius: 22px !important;
    padding: 0.35rem !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.sr-footer-marker) {
    background: rgba(255,255,255,0.82) !important;
    border: 1px solid var(--card-border) !important;
    border-radius: 18px !important;
    padding: 0.2rem !important;
    margin-top: 0.8rem !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.sr-traits-box-marker) {
    background: rgba(255,255,255,0.68) !important;
    border: 1px solid #D9D3D7 !important;
    border-radius: 12px !important;
    padding: 0.2rem !important;
}

div[data-testid="stVerticalBlockBorderWrapper"]:has(.sr-difficulty-box-marker) {
    background: rgba(255,255,255,0.78) !important;
    border: 1px solid #DDD8DB !important;
    border-radius: 16px !important;
    padding: 0.2rem !important;
    margin-top: 0.5rem !important;
}

        /* Inputs */
        .stTextInput input,
        .stTextArea textarea,
        .stSelectbox div[data-baseweb="select"] > div,
        .stMultiSelect div[data-baseweb="select"] > div {
            border-radius: 12px !important;
            border: 1px solid var(--input-border) !important;
            background: var(--input-bg) !important;
        }

        .stTextInput input:focus,
        .stTextArea textarea:focus {
            border-color: #9CB19E !important;
            box-shadow: 0 0 0 1px #9CB19E !important;
        }

        /* Buttons */
        .stButton > button {
            border-radius: 14px !important;
            min-height: 50px !important;
            font-weight: 600 !important;
            border: 1px solid #D8D1D5 !important;
            background: rgba(255,255,255,0.75) !important;
            color: var(--text) !important;
        }

        .stButton > button:hover {
            border-color: #C8C1C6 !important;
            background: rgba(255,255,255,0.95) !important;
        }

        .sr-primary-btn .stButton > button {
            border: 1px solid #9DB29F !important;
            background: linear-gradient(90deg, #B4C2B3 0%, #A7B8AA 100%) !important;
            color: white !important;
            font-weight: 700 !important;
        }

        .sr-outline-btn .stButton > button {
            background: rgba(255,255,255,0.72) !important;
            color: var(--text) !important;
        }

        /* Slider -> green */
        .stSlider [data-baseweb="slider"] div[role="slider"] {
            background-color: #A7B8AA !important;
            border-color: #93A794 !important;
        }

        .stSlider [data-baseweb="slider"] > div > div > div {
            background: linear-gradient(90deg, #AFC0B1 0%, #DCC8BE 100%) !important;
        }

        .stSlider [data-baseweb="slider"] * {
            color: #8FA791 !important;
        }

        /* Radio -> green */
        .stRadio input[type="radio"] {
            accent-color: #A7B8AA !important;
        }

        .stRadio > div {
            gap: 0.8rem;
        }

        .streamlit-expanderHeader {
            font-weight: 700 !important;
        }

        .sr-status-card {
            border-radius: 18px;
            overflow: hidden;
            border: 1px solid var(--card-border);
            background: rgba(255,255,255,0.55);
        }

        .sr-status-head {
            padding: 1.25rem 1.4rem;
            display:flex;
            align-items:center;
            justify-content:center;
            gap: 1rem;
            font-weight: 800;
            font-size: 1.55rem;
        }

        .sr-status-body {
            padding: 1.35rem 1.4rem 1.5rem 1.4rem;
            font-size: 1.05rem;
            line-height: 1.8;
        }

        .sr-status-head.success { background: var(--green-soft); color: #4A6344; }
        .sr-status-head.failed { background: var(--orange-soft); color: #A95A2C; }
        .sr-status-head.manual { background: var(--gray-soft); color: #666174; }

        .sr-icon-circle {
            width: 54px;
            height: 54px;
            border-radius: 999px;
            display:flex;
            align-items:center;
            justify-content:center;
            font-size: 1.8rem;
            font-weight: 800;
            color: white;
        }

        .sr-icon-success { background: var(--green-main); }
        .sr-icon-failed { background: var(--orange-main); }
        .sr-icon-manual { background: var(--gray-main); }

        .sr-outcome-card {
            background: rgba(255,255,255,0.65);
            border: 1px solid var(--card-border);
            border-radius: 18px;
            padding: 1.15rem 1.25rem;
        }

        .sr-outcome-title {
            display:flex;
            align-items:center;
            gap: 1rem;
            font-size: 1.8rem;
            font-weight: 800;
            margin-bottom: 0.55rem;
        }
        
        /* ===== Step 2 layout ===== */
.sr-opening-card {
    background: linear-gradient(90deg, #FBFBF8 0%, #FCFBFA 100%);
    border: 1px solid var(--card-border);
    border-radius: 18px;
    padding: 1.25rem 1.35rem;
    margin-bottom: 1rem;
}

.sr-opening-title {
    font-size: 1.15rem;
    font-weight: 800;
    margin-bottom: 0.75rem;
    display: flex;
    align-items: center;
    gap: 0.6rem;
}

.sr-opening-text {
    font-size: 1.05rem;
    line-height: 1.8;
    color: #4A4F61;
}

.sr-dual-card {
    border: 1px solid var(--card-border);
    border-radius: 18px;
    padding: 1.15rem 1.2rem;
    min-height: 210px;
}

.sr-dual-green {
    background: linear-gradient(180deg, #F7FAF8 0%, #FCFBFA 100%);
}

.sr-dual-pink {
    background: linear-gradient(180deg, #FBF7F8 0%, #FCFBFA 100%);
}

.sr-dual-title {
    font-size: 1.05rem;
    font-weight: 800;
    margin-bottom: 0.8rem;
    display: flex;
    align-items: center;
    gap: 0.55rem;
}

.sr-map-section-title {
    font-size: 1.05rem;
    font-weight: 800;
    margin: 0.9rem 0 0.75rem 0;
}

.sr-path-card {
    border: 1px solid var(--card-border);
    border-radius: 18px;
    overflow: hidden;
    background: #FCFBFA;
    height: 100%;
}

.sr-path-head {
    padding: 0.9rem 1rem;
    font-size: 1rem;
    font-weight: 800;
    border-bottom: 1px solid #E6E0E4;
    display: flex;
    align-items: center;
    gap: 0.55rem;
}

.sr-path-head.cooperative {
    background: linear-gradient(90deg, #EEF5F1 0%, #F7FAF8 100%);
}

.sr-path-head.defensive {
    background: linear-gradient(90deg, #F6F1E6 0%, #FBF8F1 100%);
}

.sr-path-head.difficult {
    background: linear-gradient(90deg, #F8ECEC 0%, #FBF6F6 100%);
}

.sr-path-body {
    padding: 1rem 1rem 1.05rem 1rem;
    line-height: 1.75;
    color: #4A4F61;
}

.sr-path-label {
    font-weight: 800;
    color: var(--text);
    margin-top: 0.25rem;
    margin-bottom: 0.25rem;
}

.sr-path-block {
    margin-bottom: 0.75rem;
}

/* ===== Step 3 layout ===== */
.sr-sim-summary {
    background: linear-gradient(180deg, #F7FBF8 0%, #FCFBFA 100%);
    border: 1px solid var(--card-border);
    border-radius: 18px;
    padding: 1rem 1.1rem;
    margin-bottom: 1rem;
}

.sr-sim-summary-grid {
    display: grid;
    grid-template-columns: 1fr 1.35fr;
    gap: 1rem;
}

.sr-sim-summary-box {
    background: rgba(255,255,255,0.78);
    border: 1px solid #DDD8DB;
    border-radius: 14px;
    padding: 0.9rem 1rem;
    min-height: 92px;
}

.sr-sim-summary-title {
    font-size: 1rem;
    font-weight: 800;
    display: flex;
    align-items: center;
    gap: 0.55rem;
    margin-bottom: 0.65rem;
}

.sr-sim-summary-value {
    font-size: 1.05rem;
    line-height: 1.5;
    color: #4A4F61;
}

.sr-sim-goal-row {
    display: flex;
    justify-content: space-between;
    gap: 1rem;
    align-items: center;
}

.sr-turn-pill {
    min-width: 86px;
    text-align: center;
    border-left: 1px solid #E0DBDF;
    padding-left: 1rem;
    font-size: 0.98rem;
    color: #6F7387;
    font-weight: 700;
}

.sr-chat-shell {
    min-height: 420px;
    margin-bottom: 1rem;
}

.sr-chat-inner {
    padding: 0.35rem 0.25rem 0.35rem 0.25rem;
}

.sr-chat-input-shell {
    background: rgba(255,255,255,0.8);
    border: 1px solid var(--card-border);
    border-radius: 18px;
    padding: 0.55rem 0.75rem;
}

.sr-map-back-link {
    font-size: 1rem;
    color: #7A7F92;
    font-weight: 500;
    margin-bottom: 1rem;
}

/* make Streamlit chat bubbles cleaner */
div[data-testid="chat-message-container"] {
    padding-top: 0.55rem !important;
    padding-bottom: 0.55rem !important;
}

div[data-testid="stChatMessageContent"] {
    border-radius: 16px !important;
}

/* chat input */
div[data-testid="stChatInput"] {
    margin-top: 0 !important;
}

div[data-testid="stChatInput"] textarea,
div[data-testid="stChatInput"] input {
    border-radius: 14px !important;
    border: 1px solid var(--input-border) !important;
    background: rgba(255,255,255,0.86) !important;
}

/* ===== Step 4 layout ===== */
.sr-debrief-outcome {
    background: linear-gradient(180deg, #F7FBF7 0%, #FCFBFA 100%);
    border: 1px solid var(--card-border);
    border-radius: 18px;
    padding: 1.2rem 1.3rem;
    margin-bottom: 1rem;
}

.sr-debrief-outcome-title {
    display: flex;
    align-items: center;
    gap: 0.9rem;
    font-size: 1.7rem;
    font-weight: 800;
    margin-bottom: 0.55rem;
}

.sr-debrief-outcome-text {
    font-size: 1.05rem;
    line-height: 1.8;
    color: #4A4F61;
}

.sr-debrief-section-title {
    font-size: 1.08rem;
    font-weight: 800;
    margin: 0.95rem 0 0.7rem 0;
}

.sr-debrief-card {
    border: 1px solid var(--card-border);
    border-radius: 18px;
    padding: 1.05rem 1.15rem;
    min-height: 220px;
}

.sr-debrief-card-success {
    background: linear-gradient(180deg, #FCFBFA 0%, #F7FAF8 100%);
}

.sr-debrief-card-failure {
    background: linear-gradient(180deg, #FCFBFA 0%, #FBF4F6 100%);
}

.sr-debrief-card-title {
    font-size: 1.02rem;
    font-weight: 800;
    margin-bottom: 0.7rem;
}

.sr-debrief-card ul {
    margin: 0;
    padding-left: 1.15rem;
    line-height: 1.85;
    color: #4A4F61;
}

.sr-debrief-advice {
    background: linear-gradient(180deg, #FBFBF8 0%, #FCFBFA 100%);
    border: 1px solid var(--card-border);
    border-radius: 18px;
    padding: 1.05rem 1.15rem;
    margin-top: 0.2rem;
}

.sr-debrief-advice-title {
    font-size: 1.02rem;
    font-weight: 800;
    margin-bottom: 0.7rem;
}

.sr-debrief-advice ul {
    margin: 0;
    padding-left: 1.15rem;
    line-height: 1.85;
    color: #4A4F61;
}

.sr-debrief-note {
    background: rgba(255,255,255,0.72);
    border: 1px solid var(--card-border);
    border-radius: 16px;
    padding: 0.95rem 1.05rem;
    margin-top: 0.9rem;
    color: #4A4F61;
    line-height: 1.8;
}

        </style>
        """,
        unsafe_allow_html=True,
    )


inject_global_css()


# ---------------------------
# Helpers
# ---------------------------
def html_escape(s):
    return html.escape(str(s))


def save_attempt_if_finished():
    if (
        st.session_state.chat_history
        and st.session_state.conversation_status in {"resolved", "failed", "manual_end"}
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


def render_step_header(step_num: int, title: str, lead: str | None = None):
    st.markdown('<div class="sr-top-title">Social Rehearsal</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="sr-step">Step {step_num} of 4 — {title}</div>', unsafe_allow_html=True)
    if lead:
        st.markdown(f'<div class="sr-lead">{html_escape(lead)}</div>', unsafe_allow_html=True)


def render_tension_meter(tension: int, max_tension: int = MAX_TENSION):
    block_html = []
    for i in range(max_tension):
        if i < tension:
            bg = "#A8BB88"
            border = "#A8BB88"
        else:
            bg = "transparent"
            border = "#B7B0B5"

        block_html.append(
            f'<div style="width:20px;height:20px;border:1px solid {border};background:{bg};display:inline-block;margin-right:4px;border-radius:4px;"></div>'
        )

    blocks = "".join(block_html)

    html = f"""
<div style="background:#FCFBFA;border:1px solid #DDD8DB;border-radius:18px;padding:16px 18px;margin:10px 0 18px 0;">
    <div style="color:#313348;font-size:16px;display:flex;align-items:center;gap:14px;flex-wrap:wrap;">
        <span style="min-width:90px;font-weight:700;">Tension:</span>
        <div style="display:flex;align-items:center;">{blocks}</div>
        <span style="font-size:13px;color:#6F7387;">{tension}/{max_tension}</span>
    </div>
</div>
"""
    st.markdown(html, unsafe_allow_html=True)
    
def render_simulation_summary_card(scenario: dict, user_turns: int):
    st.markdown(
        f"""
        <div class="sr-sim-summary">
            <div class="sr-sim-summary-grid">
                <div class="sr-sim-summary-box">
                    <div class="sr-sim-summary-title">
                        <span class="sr-dot sr-dot-person"></span>
                        Talking to
                    </div>
                    <div class="sr-sim-summary-value">{html_escape(scenario['person'])}</div>
                </div>
                <div class="sr-sim-summary-box">
                    <div class="sr-sim-summary-title">
                        <span class="sr-dot sr-dot-situation"></span>
                        Goal
                    </div>
                    <div class="sr-sim-goal-row">
                        <div class="sr-sim-summary-value">{html_escape(scenario['goal'])}</div>
                        <div class="sr-turn-pill">{user_turns} / {MAX_TURNS}</div>
                    </div>
                </div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_score_bar(label: str, score: int, max_score: int = 8):
    block_html = []
    for i in range(max_score):
        if i < score:
            bg = "#A8BB88"
            border = "#A8BB88"
        else:
            bg = "transparent"
            border = "#B7B0B5"

        block_html.append(
            f'<div style="width:18px;height:18px;border:1px solid {border};background:{bg};display:inline-block;margin-right:4px;border-radius:4px;"></div>'
        )

    blocks = "".join(block_html)

    html = f"""
<div style="background:#FCFBFA;border:1px solid #DDD8DB;border-radius:16px;padding:12px 16px;margin:8px 0;">
    <div style="color:#313348;font-size:15px;display:flex;align-items:center;gap:14px;flex-wrap:wrap;">
        <span style="min-width:110px;font-weight:700;">{html_escape(label)}:</span>
        <div style="display:flex;align-items:center;">{blocks}</div>
        <span style="font-size:13px;color:#6F7387;">{score}/{max_score}</span>
    </div>
</div>
"""
    st.markdown(html, unsafe_allow_html=True)


def render_conversation_map(conversation_map: dict):
    st.markdown(
        f"""
        <div class="sr-opening-card">
            <div class="sr-opening-title">
                <span class="sr-dot sr-dot-person" style="opacity:0.7;"></span>
                Recommended Opening
            </div>
            <div class="sr-opening-text">{html_escape(conversation_map["recommended_opening"])}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    col1, col2 = st.columns(2, gap="large")

    with col1:
        tactical_items = conversation_map.get("tactical_advice", [])
        tactical_html = "".join(f"<li>{html_escape(item)}</li>" for item in tactical_items) if tactical_items else "<li>No tactical advice generated.</li>"

        st.markdown(
            f"""
            <div class="sr-dual-card sr-dual-green">
                <div class="sr-dual-title">
                    <span class="sr-dot sr-dot-person"></span>
                    Tactical Advice
                </div>
                <div style="line-height:1.9; color:#4A4F61;">
                    <ul style="margin:0; padding-left:1.2rem;">
                        {tactical_html}
                    </ul>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        risk_items = conversation_map.get("risk_phrases", [])
        risk_html = "".join(f"<li>{html_escape(item)}</li>" for item in risk_items) if risk_items else "<li>No risk phrases generated.</li>"

        st.markdown(
            f"""
            <div class="sr-dual-card sr-dual-pink">
                <div class="sr-dual-title">
                    <span class="sr-dot" style="background:#DFA0A0;"></span>
                    Risk Phrases
                </div>
                <div style="line-height:1.9; color:#4A4F61;">
                    <ul style="margin:0; padding-left:1.2rem;">
                        {risk_html}
                    </ul>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.markdown('<div class="sr-map-section-title">Likely Response Paths</div>', unsafe_allow_html=True)

    path_cols = st.columns(3, gap="large")
    paths = conversation_map.get("response_paths", [])

    path_styles = {
        "Cooperative": ("cooperative", "sr-dot-person"),
        "Defensive": ("defensive", ""),
        "Dismissive or Difficult": ("difficult", ""),
    }

    for i, path in enumerate(paths[:3]):
        path_name = path.get("path_name", "Path")
        style_name, dot_class = path_styles.get(path_name, ("cooperative", "sr-dot-person"))

        if dot_class:
            dot_html = f'<span class="sr-dot {dot_class}"></span>'
        elif style_name == "defensive":
            dot_html = '<span class="sr-dot" style="background:#DDBB70;"></span>'
        else:
            dot_html = '<span class="sr-dot" style="background:#DFA0A0;"></span>'

        with path_cols[i]:
            st.markdown(
                f"""
                <div class="sr-path-card">
                    <div class="sr-path-head {style_name}">
                        {dot_html}
                        {html_escape(path_name)}
                    </div>
                    <div class="sr-path-body">
                        <div class="sr-path-block">
                            <div class="sr-path-label">They might say:</div>
                            <div>{html_escape(path.get("what_they_might_say", ""))}</div>
                        </div>
                        <div class="sr-path-block">
                            <div class="sr-path-label">Why they say this:</div>
                            <div>{html_escape(path.get("why_they_say_this", ""))}</div>
                        </div>
                        <div class="sr-path-block" style="margin-bottom:0;">
                            <div class="sr-path-label">Best response:</div>
                            <div>{html_escape(path.get("best_user_response", ""))}</div>
                        </div>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )


def derive_status_visuals():
    status = st.session_state.conversation_status
    reason = st.session_state.conversation_status_reason

    if status == "resolved":
        return {
            "head_cls": "success",
            "icon_cls": "sr-icon-success",
            "icon": "✓",
            "title": "Conversation Successful",
            "line1": "You succeeded.",
            "line2": reason or "You reached a workable agreement.",
        }
    if status == "manual_end":
        return {
            "head_cls": "manual",
            "icon_cls": "sr-icon-manual",
            "icon": "!",
            "title": "Conversation Ended Manually",
            "line1": "The exercise was intentionally ended.",
            "line2": "You are welcome to continue or review your results.",
        }
    return {
        "head_cls": "failed",
        "icon_cls": "sr-icon-failed",
        "icon": "✕",
        "title": "Conversation Failed",
        "line1": "You did not succeed.",
        "line2": reason or "You were unable to resolve the issue before it escalated.",
    }


def render_simulation_end_state():
    visuals = derive_status_visuals()
    st.markdown(
        f"""
        <div class="sr-status-card">
            <div class="sr-status-head {visuals['head_cls']}">
                <div class="sr-icon-circle {visuals['icon_cls']}">{visuals['icon']}</div>
                <div>{html_escape(visuals['title'])}</div>
            </div>
            <div class="sr-status-body">
                <div>{html_escape(visuals['line1'])}</div>
                <div style="margin-top:0.7rem;">{html_escape(visuals['line2'])}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_debrief(debrief: dict):
    st.markdown(
        f"""
        <div class="sr-debrief-outcome">
            <div class="sr-debrief-outcome-title">
                <div class="sr-icon-circle sr-icon-success">✓</div>
                <div>Overall Outcome</div>
            </div>
            <div class="sr-debrief-outcome-text">
                {html_escape(debrief["overall_outcome"])}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    scores = debrief.get("scores", {})
    st.markdown('<div class="sr-debrief-section-title">Performance Breakdown</div>', unsafe_allow_html=True)
    render_score_bar("Clarity", scores.get("clarity", 4))
    render_score_bar("Assertiveness", scores.get("assertiveness", 4))
    render_score_bar("Strategy", scores.get("strategy", 4))
    render_score_bar("Tone", scores.get("tone", 4))

    col1, col2 = st.columns(2, gap="large")

    with col1:
        success_items = debrief.get("success_factors", [])
        success_html = "".join(f"<li>{html_escape(item)}</li>" for item in success_items) if success_items else "<li>None identified clearly yet.</li>"

        st.markdown(
            f"""
            <div class="sr-debrief-card sr-debrief-card-success">
                <div class="sr-debrief-card-title">Success Factors</div>
                <ul>
                    {success_html}
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with col2:
        failure_items = debrief.get("failure_patterns", [])
        failure_html = "".join(f"<li>{html_escape(item)}</li>" for item in failure_items) if failure_items else "<li>No strong recurring failure pattern identified.</li>"

        st.markdown(
            f"""
            <div class="sr-debrief-card sr-debrief-card-failure">
                <div class="sr-debrief-card-title">Failure Patterns</div>
                <ul>
                    {failure_html}
                </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )

    advice_items = debrief.get("actionable_advice", [])
    advice_html = "".join(f"<li>{html_escape(item)}</li>" for item in advice_items)

    st.markdown(
        f"""
        <div class="sr-debrief-advice">
            <div class="sr-debrief-advice-title">Actionable Advice</div>
            <ul>
                {advice_html}
            </ul>
        </div>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        f"""
        <div class="sr-debrief-note">
            <strong>Final Note</strong><br>
            {html_escape(debrief["encouragement"])}
        </div>
        """,
        unsafe_allow_html=True,
    )

    

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
    render_step_header(
        1,
        "Setup",
        "Practice difficult conversations before they happen. Model the other person, predict likely responses, simulate the interaction, and learn from it.",
    )

    scenario = st.session_state.scenario or {}

    existing_traits = []
    if scenario.get("traits") and scenario.get("traits") != "No traits provided":
        existing_traits = [t.strip() for t in scenario["traits"].split(",") if t.strip()]

    preset_defaults = [t for t in existing_traits if t in PERSONALITY_PRESETS]
    custom_defaults = [t for t in existing_traits if t not in PERSONALITY_PRESETS]

    person = scenario.get("person", "")
    conflict_type_default = scenario.get("conflict_type", CONFLICT_TYPES[0])
    conflict_type_index = CONFLICT_TYPES.index(conflict_type_default) if conflict_type_default in CONFLICT_TYPES else 0
    conflict = scenario.get("conflict", "")
    difficulty = scenario.get("difficulty", 3)
    goal = scenario.get("goal", "")
    tone_default = scenario.get("tone", TONE_OPTIONS[0])
    tone_index = TONE_OPTIONS.index(tone_default) if tone_default in TONE_OPTIONS else 0

    left, right = st.columns(2, gap="medium")

    with left:
        with st.container(border=True):
            st.markdown('<div class="sr-left-card-marker"></div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="sr-panel-title"><span class="sr-dot sr-dot-person"></span>The Person</div>',
                unsafe_allow_html=True,
            )

            person = st.text_input(
                "Who are you talking to?",
                value=person,
                placeholder="Enter a name, e.g., roommate, professor"
            )

            conflict_type = st.selectbox(
                "Conflict type",
                CONFLICT_TYPES,
                index=conflict_type_index
            )

            with st.container(border=True):
                st.markdown('<div class="sr-traits-box-marker"></div>', unsafe_allow_html=True)
                traits = st.multiselect(
                    "Personality traits",
                    PERSONALITY_PRESETS,
                    default=preset_defaults
                )

            st.markdown('<div class="sr-custom-traits-label">Add custom traits</div>', unsafe_allow_html=True)
            custom_traits = st.text_input(
                "Add custom traits",
                value=", ".join(custom_defaults),
                placeholder="e.g. sarcastic, controlling",
                label_visibility="collapsed"
            )

            with st.container(border=True):
                st.markdown('<div class="sr-difficulty-box-marker"></div>', unsafe_allow_html=True)
                st.markdown('<div class="sr-difficulty-title">How difficult are they?</div>', unsafe_allow_html=True)

                difficulty = st.slider(
                    "How difficult are they?",
                    min_value=1,
                    max_value=5,
                    value=difficulty,
                    label_visibility="collapsed"
                )

                st.markdown(
                    f"""
                    <div class="sr-difficulty-label">{DIFFICULTY_MAP[difficulty]['label']}</div>
                    <div class="sr-difficulty-desc">{DIFFICULTY_MAP[difficulty]["behavior"]}</div>
                    """,
                    unsafe_allow_html=True,
                )

    with right:
        with st.container(border=True):
            st.markdown('<div class="sr-right-card-marker"></div>', unsafe_allow_html=True)
            st.markdown(
                '<div class="sr-panel-title"><span class="sr-dot sr-dot-situation"></span>The Situation</div>',
                unsafe_allow_html=True,
            )

            conflict = st.text_area(
                "What is the conflict?",
                value=conflict,
                placeholder="Describe the situation...",
                height=170
            )

            goal = st.text_area(
                "What is your goal?",
                value=goal,
                placeholder="Describe your objective...",
                height=170
            )

            tone = st.radio(
                "Your preferred tone",
                TONE_OPTIONS,
                index=tone_index,
                horizontal=True
            )

    with st.container(border=True):
        st.markdown('<div class="sr-footer-marker"></div>', unsafe_allow_html=True)
        footer_cols = st.columns([1.25, 4.1, 2.35])

        with footer_cols[0]:
            st.markdown('<div class="sr-outline-btn">', unsafe_allow_html=True)
            if st.button("Start Over", use_container_width=True):
                reset_all()
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with footer_cols[2]:
            st.markdown('<div class="sr-primary-btn">', unsafe_allow_html=True)
            if st.button("Next: Generate Conversation Map", use_container_width=True):
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
            st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------
# Page 2: Conversation Map
# ---------------------------
def render_map_page():
    render_step_header(
        2,
        "Conversation Map",
        "Preview how this conversation may unfold and decide how to respond.",
    )
    st.markdown('<div class="sr-divider"></div>', unsafe_allow_html=True)

    if not st.session_state.conversation_map:
        st.warning("No conversation map found yet. Please generate one first.")
        if st.button("Back to Setup"):
            st.session_state.current_step = 1
            st.rerun()
        return

    render_conversation_map(st.session_state.conversation_map)

    st.markdown('<div class="sr-divider"></div>', unsafe_allow_html=True)

    with st.container(border=True):
        footer_cols = st.columns([1.25, 4.1, 2.35])

        with footer_cols[0]:
            st.markdown('<div class="sr-outline-btn">', unsafe_allow_html=True)
            if st.button("Back", use_container_width=True):
                st.session_state.current_step = 1
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)

        with footer_cols[2]:
            st.markdown('<div class="sr-primary-btn">', unsafe_allow_html=True)
            if st.button("Continue to Simulation", use_container_width=True):
                st.session_state.current_step = 3
                st.session_state.simulation_started = True
                st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)


# ---------------------------
# Page 3: Simulation
# ---------------------------
def render_simulation_page():
    render_step_header(3, "Simulation")
    st.markdown('<div class="sr-divider"></div>', unsafe_allow_html=True)

    if not st.session_state.scenario or not st.session_state.conversation_map:
        st.warning("You need to complete the earlier steps first.")
        if st.button("Back to Setup"):
            st.session_state.current_step = 1
            st.rerun()
        return

    if not st.session_state.simulation_started:
        st.session_state.simulation_started = True

    scenario = st.session_state.scenario
    user_turns = len([m for m in st.session_state.chat_history if m["role"] == "user"])

    st.markdown('<div class="sr-map-back-link">← Back to Conversation Map</div>', unsafe_allow_html=True)

    render_simulation_summary_card(scenario, user_turns)
    render_tension_meter(st.session_state.tension, MAX_TENSION)

    if user_turns >= MAX_TURNS and st.session_state.conversation_status == "ongoing":
        st.session_state.conversation_status = "failed"
        st.session_state.conversation_status_reason = (
            "The conversation hit the maximum number of turns without reaching a clear outcome."
        )
        st.session_state.status_banner_shown = False

    if st.session_state.conversation_status != "ongoing":
        save_attempt_if_finished()
        render_simulation_end_state()
    else:
        with st.container(border=True):
            if len(st.session_state.chat_history) == 0:
                st.info("Start by sending your first message.")

            for msg in st.session_state.chat_history:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        with st.container(border=True):
            user_input = st.chat_input("Type your message...")

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

    st.markdown('<div class="sr-divider"></div>', unsafe_allow_html=True)

    if st.session_state.conversation_status == "ongoing":
        col1, col2 = st.columns(2)

        with col1:
            if st.button("Back", use_container_width=True):
                st.session_state.current_step = 2
                st.rerun()

        with col2:
            if st.button("Force End", use_container_width=True):
                st.session_state.conversation_status = "manual_end"
                st.session_state.conversation_status_reason = (
                    "The exercise was intentionally ended."
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
    st.markdown('<div class="sr-divider"></div>', unsafe_allow_html=True)

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

    st.markdown('<div class="sr-divider"></div>', unsafe_allow_html=True)
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