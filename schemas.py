from __future__ import annotations

from typing import Dict, List, Optional

from pydantic import BaseModel, Field


class FraudRiskDetails(BaseModel):
    risk_level: Optional[str] = None
    matched_rules: List[str] = Field(default_factory=list)
    recommended_action: Optional[str] = None


class BankingResponse(BaseModel):
    intent: str
    answer: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    details: Dict[str, FraudRiskDetails]

    class Config:
        extra = "forbid"
