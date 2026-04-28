# AML & Fraud Detection Co-Pilot

A Banking FAQ Chatbot demo that showcases prompt engineering, few-shot learning, chain-of-thought reasoning, structured JSON output, guardrails, and a simple Streamlit UI.

## Features

- Natural language banking Q&A: account types, loan eligibility, interest rates, KYC process
- Engineered prompt template library with system role, formatting, and safety guardrails
- Few-shot examples for at least 3 banking intent categories
- Chain-of-thought reasoning for complex loan eligibility questions
- Structured JSON response validation using Pydantic
- Input guardrails for PII detection, off-topic filtering, and prompt injection defense
- Streamlit UI for interactive chatbot use

## Setup

1. Create and activate a Python environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install requirements:

```bash
pip install -r requirements.txt
```

3. Set your OpenAI API key:

```bash
export OPENAI_API_KEY="your_api_key_here"
```

4. Run the Streamlit app:

```bash
streamlit run app.py
```

## Usage

- Click a recommended question in the sidebar to populate the chat input.
- Enter any AML, fraud detection, or basic banking question and press **Send**.
- The app shows the answer, chain-of-thought reasoning, and a validated JSON response.
- If a question is completely unrelated, the assistant returns a plain-text message asking you to contact the bank.

## Files

- `app.py` - Streamlit chatbot UI
- `bank_faq.py` - prompt builder, guardrails, OpenAI integration, response parsing
- `schemas.py` - Pydantic models for structured response validation
- `prompts/banking_faq.yaml` - prompt template library with examples and guardrails
- `evaluation.py` - batch evaluator for 20 sample queries
- `evaluation_report.md` - evaluation plan and sample results

## Evaluation

Run `python evaluation.py` to execute the built-in test suite of 20 banking queries and generate a structured results summary.
