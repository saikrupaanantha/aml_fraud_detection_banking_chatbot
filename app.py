from __future__ import annotations

import json
import re

import streamlit as st
from dotenv import load_dotenv

from bank_faq import BankingFAQAssistant, GuardrailViolation, OffTopicError, OpenAIAPIError
from schemas import BankingResponse

load_dotenv()

st.set_page_config(page_title="AML & Fraud Detection Co-Pilot", page_icon="🛡️", layout="centered")
st.title("🛡️ AML & Fraud Detection Co-Pilot")
st.write("An AML and fraud detection assistant with prompt engineering, guardrails, and structured JSON responses.")

assistant = BankingFAQAssistant()


def render_pointwise_text(text: str) -> None:
    if not text:
        return

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if len(lines) > 1:
        for line in lines:
            st.markdown(f"- ✅ {line}")
        return

    sentences = [part.strip() for part in re.split(r'(?<=[.!?])\s+', text) if part.strip()]
    if len(sentences) > 1:
        for sentence in sentences:
            st.markdown(f"- ✅ {sentence}")
        return

    st.write(text)


recommended_questions = [
    "What are red flags for money laundering in transaction monitoring?",
    "How should we handle multiple suspicious transfers from one account?",
    "What KYC documents are required for high-risk customers?",
    "How does the bank classify fraud risk for new accounts?",
    "When should a case be escalated to the AML team?",
    "What are the common fraud indicators for online banking?",
    "How do sanctions screenings affect customer onboarding?",
    "What are the fees for a standard checking account?",
    "How do I report suspicious AML activity?",
    "What should I do if I see an unauthorized transaction?",
]

with st.sidebar:
    st.header("Recommended questions")
    for idx, question in enumerate(recommended_questions):
        if st.button(question, key=f"sample_{idx}"):
            st.session_state.query = question
    st.markdown("---")
    st.write("Model:")
    st.write(f"`{assistant.model}`")

if "query" not in st.session_state:
    st.session_state.query = ""

st.markdown(
    """
    <style>
    textarea {
        width: 100% !important;
        min-height: 48px !important;
        max-height: 300px !important;
        resize: vertical !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

query = st.text_area(
    "Enter your AML / fraud detection question",
    key="query",
    placeholder="Type your question here...",
    height=80,
)
run_button = st.button("Send")

if run_button:
    if not query.strip():
        st.error("Please enter a question first.")
    else:
        try:
            result = assistant.ask(query)
            st.success("Response validated successfully.")
            st.subheader("Answer")
            if result.intent == "greeting":
                st.write(result.answer)
            else:
                render_pointwise_text(result.answer)

            json_block = None
            risk_block = None
            if result.intent != "greeting":
                json_block = json.dumps(result.model_dump(by_alias=True), indent=2)
                with st.expander("Structured JSON Response", expanded=False):
                    st.code(json_block, language="json")

                st.subheader("Reasoning")
                st.write(result.reasoning)

                if result.details and result.details.get("fraud_risk_assessment"):
                    risk = result.details["fraud_risk_assessment"]
                    risk_block = {
                        "risk_level": risk.risk_level,
                        "matched_rules": risk.matched_rules,
                        "recommended_action": risk.recommended_action,
                    }
                    with st.expander("Fraud Risk Assessment", expanded=False):
                        st.write(risk_block)

        except GuardrailViolation as exc:
            st.error(f"Guardrail triggered: {exc.reason}")
        except OffTopicError as exc:
            st.error(exc.message)
        except OpenAIAPIError as exc:
            st.error(f"OpenAI API error: {exc.message}")
        except Exception as exc:
            st.error(f"Unable to answer request: {exc}")

st.markdown("---")
