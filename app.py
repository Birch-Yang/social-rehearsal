import streamlit as st

st.set_page_config(page_title="Social Rehearsal", layout="wide")

st.title("Social Rehearsal")
st.caption("Practice the conversation before it happens.")

person = st.text_input("Who are you talking to?")
conflict = st.text_area("What is the conflict?")
traits = st.text_input("What are their personality traits?")
difficulty = st.slider("How difficult are they?", 1, 5, 3)

if st.button("Generate"):
    st.success("Setup saved. Next step: connect LLM output.")
    st.write({
        "person": person,
        "conflict": conflict,
        "traits": traits,
        "difficulty": difficulty
    })