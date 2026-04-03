from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class Greeks(BaseModel):
    delta: float
    gamma: float
    vega: float
    theta: float


class Opportunity(BaseModel):
    id: str
    symbol: str
    structure: str
    thesis: str
    dte: int = Field(ge=0)
    score: int = Field(ge=0, le=100)
    expected_return: float
    expected_shortfall: float
    win_rate: float = Field(ge=0, le=100)
    spread_bps: int = Field(ge=0)
    max_loss: float
    catalysts: list[str]
    top_drivers: list[str]
    greeks: Greeks


class OpportunitiesResponse(BaseModel):
    as_of: datetime
    source: str
    items: list[Opportunity]


class TradeDetail(BaseModel):
    id: str
    symbol: str
    structure: str
    thesis: str
    score: int
    max_loss: float
    expected_shortfall: float
    greeks: Greeks
    top_drivers: list[str]
    notes: list[str]


class RiskMetric(BaseModel):
    label: str
    current: float
    limit: float
    unit: str


class ExposureBucket(BaseModel):
    bucket: str
    value: int


class RiskSnapshot(BaseModel):
    execution_mode: str
    entitlement: str
    metrics: list[RiskMetric]
    concentration: list[ExposureBucket]


class HealthResponse(BaseModel):
    status: str
    environment: str
    provider: str
