from __future__ import annotations

import json

import streamlit as st
from dotenv import load_dotenv

from bank_faq import BankingFAQAssistant, GuardrailViolation, OffTopicError, OpenAIAPIError
from schemas import BankingResponse

load_dotenv()

st.set_page_config(page_title="AML & Fraud Detection Co-Pilot", layout="centered")
st.title("AML & Fraud Detection Co-Pilot")
st.write("An AML and fraud detection assistant with prompt engineering, guardrails, and structured JSON responses.")

assistant = BankingFAQAssistant()

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

query = st.text_area("Enter your AML / fraud detection question", height=180, key="query")
run_button = st.button("Send")

if run_button:
    if not query.strip():
        st.error("Please enter a question first.")
    else:
        try:
            result = assistant.ask(query)
            st.success("Response validated successfully.")
            st.subheader("Answer")
            st.write(result.answer)

            if result.intent != "greeting":
                st.subheader("Structured JSON Response")
                st.code(json.dumps(result.model_dump(by_alias=True), indent=2), language="json")

                st.subheader("Reasoning")
                st.write(result.reasoning)

                if result.details and result.details.get("fraud_risk_assessment"):
                    risk = result.details["fraud_risk_assessment"]
                    st.subheader("Fraud Risk Assessment")
                    st.write(
                        {
                            "risk_level": risk.risk_level,
                            "matched_rules": risk.matched_rules,
                            "recommended_action": risk.recommended_action,
                        }
                    )

        except GuardrailViolation as exc:
            st.error(f"Guardrail triggered: {exc.reason}")
        except OffTopicError as exc:
            st.error(exc.message)
        except OpenAIAPIError as exc:
            st.error(f"OpenAI API error: {exc.message}")
        except Exception as exc:
            st.error(f"Unable to answer request: {exc}")

st.markdown("---")
