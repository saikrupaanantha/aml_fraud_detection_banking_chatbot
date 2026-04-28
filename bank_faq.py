from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from openai import OpenAI, OpenAIError
import yaml
from pydantic import ValidationError

from schemas import BankingResponse


PROMPT_PATH = Path(__file__).resolve().parent / "prompts" / "banking_faq.yaml"


class GuardrailViolation(Exception):
    def __init__(self, message: str, reason: str):
        super().__init__(message)
        self.reason = reason


class OffTopicError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class OpenAIAPIError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


class BankingFAQAssistant:
    def __init__(self, prompt_file: Path = PROMPT_PATH):
        self.prompt_template = self._load_prompt_template(prompt_file)
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.client = OpenAI(api_key=self.api_key)
        self.model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    @staticmethod
    def _load_prompt_template(path: Path) -> Dict[str, Any]:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        return data

    @staticmethod
    def detect_pii(text: str) -> List[str]:
        patterns = {
            "email": r"[\w.+-]+@[\w-]+\.[\w.-]+",
            "phone": r"\b\+?\d[\d\s()-]{7,}\b",
            "ssn": r"\b\d{3}-\d{2}-\d{4}\b",
            "credit_card": r"\b(?:\d[ -]*?){13,16}\b",
        }
        matches = []
        for name, pattern in patterns.items():
            if re.search(pattern, text):
                matches.append(name)
        return matches

    @staticmethod
    def detect_prompt_injection(text: str) -> bool:
        injection_patterns = [
            r"ignore (previous|all) instructions",
            r"disregard (previous|all) messages",
            r"respond with.*<json>",
            r"system prompt",
            r"you are in a sandbox",
        ]
        return any(re.search(pattern, text, re.IGNORECASE) for pattern in injection_patterns)

    @staticmethod
    def detect_off_topic(text: str) -> bool:
        valid_keywords = [
            "account",
            "loan",
            "interest",
            "rate",
            "credit",
            "deposit",
            "savings",
            "checking",
            "kyc",
            "aml",
            "fraud",
            "suspicious",
            "transaction",
            "money laundering",
            "compliance",
            "risk",
            "screening",
            "sanction",
            "onboarding",
            "wire",
            "transfer",
            "account takeover",
            "chargeback",
            "online banking",
            "branch",
            "mortgage",
            "card",
            "balance",
            "withdrawal",
            "deposit",
            "statement",
        ]
        text_lower = text.lower()
        return not any(keyword in text_lower for keyword in valid_keywords)

    @staticmethod
    def detect_greeting(text: str) -> bool:
        greetings = ["hi", "hello", "hey", "good morning", "good afternoon", "good evening"]
        text_lower = text.lower().strip()
        return any(text_lower == greeting or text_lower.startswith(greeting + " ") for greeting in greetings)

    def build_prompt(self, user_message: str) -> List[Dict[str, str]]:
        system_instructions = self.prompt_template["system"]["instructions"].strip()
        output_schema = self.prompt_template["output_format"]["schema"].strip()
        guardrails = "\n".join(f"- {line}" for line in self.prompt_template["guardrails"])

        messages = [
            {"role": "system", "content": system_instructions},
            {
                "role": "system",
                "content": (
                    "Follow the output schema exactly. Use only valid JSON. "
                    "If you cannot answer safely, return a refusal JSON with the same keys and a low confidence.\n"
                    "Guardrails:\n" + guardrails + "\n\n" + "Required schema:\n" + output_schema
                ),
            },
        ]

        for example in self.prompt_template.get("few_shot_examples", []):
            messages.append({"role": "user", "content": example["user"]})
            messages.append({"role": "assistant", "content": example["response"].strip()})

        messages.append({"role": "user", "content": user_message})
        return messages

    def call_model(self, messages: List[Dict[str, str]]) -> str:
        if not self.api_key:
            raise RuntimeError("OPENAI_API_KEY is required to call the model.")

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.2,
                max_tokens=450,
                n=1,
            )
            return response.choices[0].message.content.strip()
        except OpenAIError as exc:
            raise OpenAIAPIError(str(exc)) from exc

    @staticmethod
    def _extract_json(text: str) -> str:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if not match:
            raise ValueError("No JSON object found in model output.")
        return match.group(0)

    def parse_response(self, raw_text: str) -> BankingResponse:
        json_text = self._extract_json(raw_text)
        parsed = json.loads(json_text)
        return BankingResponse(**parsed)

    def refusal_response(self, reason: str, answer: str | None = None) -> BankingResponse:
        return BankingResponse(
            intent="refusal",
            answer=answer or "I cannot answer that request. Please contact your bank or support team for help.",
            confidence=0.0,
            reasoning=reason,
            details={
                "fraud_risk_assessment": {
                    "risk_level": None,
                    "matched_rules": [],
                    "recommended_action": None,
                }
            },
        )

    def ask(self, user_message: str) -> BankingResponse:
        if self.detect_greeting(user_message):
            return BankingResponse(
                intent="greeting",
                answer=(
                    "Hi! I'm your AML & Fraud Detection Co-Pilot. "
                    "I can help with AML, fraud detection, KYC, and banking questions. "
                    "How can I assist you today?"
                ),
                confidence=1.0,
                reasoning="The user greeted the assistant, so I respond with a friendly introduction and offer help.",
                details={
                    "fraud_risk_assessment": {
                        "risk_level": "low",
                        "matched_rules": ["greeting"],
                        "recommended_action": "Continue the conversation",
                    }
                },
            )

        pii = self.detect_pii(user_message)
        if pii:
            return self.refusal_response(
                f"Contains sensitive data types: {', '.join(pii)}",
                "I cannot process questions containing personal data. Please contact your bank directly."
            )

        if self.detect_prompt_injection(user_message):
            return self.refusal_response(
                "User input contains hidden or malicious instruction.",
                "I cannot answer that request safely. Please ask a clear banking or AML/fraud question."
            )

        if self.detect_off_topic(user_message):
            raise OffTopicError(
                "That is not a valid AML/fraud or banking question. Please contact your bank for support."
            )

        messages = self.build_prompt(user_message)
        raw = self.call_model(messages)

        try:
            return self.parse_response(raw)
        except (ValueError, ValidationError) as exc:
            return self.refusal_response(
                f"Unable to parse model response: {exc}",
                "I could not process that answer cleanly. Please try a different banking or AML/fraud question."
            )
