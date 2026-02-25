"""Pydantic request/response models for pricing API."""
from pydantic import BaseModel, Field
from typing import Optional


class BuildCurvesRequest(BaseModel):
    target_date: Optional[str] = Field(None, description="ISO date string. None = latest.")


class BumpRequest(BaseModel):
    curve: str = Field(..., description="'ibr' or 'sofr'")
    bps: Optional[float] = Field(None, description="Parallel shift in bps")
    node: Optional[str] = Field(None, description="Tenor key (e.g., 'ibr_5y' or '60')")
    rate_pct: Optional[float] = Field(None, description="New rate in percent for the node")


class NdfRequest(BaseModel):
    notional_usd: float
    strike: float
    maturity_date: str = Field(..., description="ISO date string YYYY-MM-DD")
    direction: str = Field("buy", description="'buy' or 'sell'")
    spot: Optional[float] = None
    use_market_forward: bool = Field(False, description="Use FXEmpire forward instead of implied")
    market_forward: Optional[float] = Field(None, description="Market forward rate if use_market_forward=True")


class IbrSwapRequest(BaseModel):
    notional: float
    tenor_years: Optional[int] = Field(None, description="Tenor in years (e.g., 5)")
    maturity_date: Optional[str] = Field(None, description="ISO date or use tenor_years")
    fixed_rate: float = Field(..., description="Fixed rate as decimal (e.g., 0.095)")
    pay_fixed: bool = True
    spread: float = 0.0


class TesBondRequest(BaseModel):
    issue_date: str
    maturity_date: str
    coupon_rate: float = Field(..., description="Coupon rate as decimal (e.g., 0.07)")
    market_clean_price: Optional[float] = None
    face_value: float = 100.0


class XccySwapRequest(BaseModel):
    notional_usd: float
    start_date: str
    maturity_date: str
    xccy_basis_bps: float = 0.0
    pay_usd: bool = True
    fx_initial: Optional[float] = None
    cop_spread_bps: float = 0.0
    usd_spread_bps: float = 0.0
