# Social Rehearsal

Social Rehearsal is an AI-powered conversation simulator for practicing difficult real-life conversations before they happen.

It helps users map likely response paths, simulate the interaction, and receive a structured debrief afterward.

## Live Demo

[Try the app here] 

## Run Locally

```bash
git clone YOUR_REPO_LINK
cd YOUR_REPO_NAME
pip install -r requirements.txt
mkdir -p .streamlit
printf 'OPENAI_API_KEY = "your_api_key_here"\n' > .streamlit/secrets.toml
streamlit run app.py
```

## Why We Built This

Many young people, especially college students, struggle with high-stakes conversations such as setting boundaries, confronting a roommate, asking for accountability, or making a difficult request.

We built Social Rehearsal to give users a low-pressure way to prepare: first by modeling how the other person might respond, then by simulating the conversation, and finally by giving targeted feedback on what worked and what could be improved.

## Features

- **Scenario Setup**  
  Define who you are talking to, what the conflict is, their personality traits, difficulty level, your goal, and your intended tone.

- **Conversation Map**  
  Generate a recommended opening, likely response paths, tactical advice, and risky phrases to avoid.

- **Live Simulation**  
  Practice the conversation with an AI roleplaying the other person in real time.  
  Includes tension tracking and realistic resistance based on difficulty.

- **Debrief**  
  Review the outcome, performance breakdown, success factors, failure patterns, and actionable advice after each attempt.

- **Retry System**  
  Retry the same scenario or generate a harder version for additional practice.

## How It Works

1. Set up a difficult conversation scenario.
2. Generate a conversation map to preview likely dynamics.
3. Practice the conversation in the simulator.
4. Review a structured debrief with strengths, mistakes, and next-step advice.

## Tech Stack

- **Frontend / App Framework:** Streamlit
- **LLM:** OpenAI Responses API (`gpt-5.4-mini`)
- **Language:** Python
- **Architecture:** multi-step stateful workflow with structured prompting and JSON-based 

## Project Structure

```text
app.py        # Streamlit app and page flow
llm.py        # Model calls and JSON parsing
prompts.py    # Prompt templates for each stage
schemas.py    # Shared constants and option lists

