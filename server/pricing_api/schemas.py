"""Pydantic request/response models for pricing API."""
from pydantic import BaseModel, Field
from typing import List, Optional


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
    market_ytm: Optional[float] = Field(
        None,
        description=(
            "Market YTM as decimal (e.g., 0.0925 for 9.25%). "
            "When provided, bypasses the TES curve and uses this yield directly. "
            "Enables historical pricing with EOD marks."
        ),
    )
    valuation_date: Optional[str] = Field(
        None,
        description=(
            "ISO date string YYYY-MM-DD. When provided, sets QuantLib evaluation "
            "date to this date for historical repricing. Defaults to today."
        ),
    )


class XccySwapRequest(BaseModel):
    notional_usd: float
    start_date: str
    maturity_date: str
    xccy_basis_bps: float = 0.0
    pay_usd: bool = True
    fx_initial: Optional[float] = None
    cop_spread_bps: float = 0.0
    usd_spread_bps: float = 0.0
    amortization_type: str = "bullet"
    amortization_schedule: Optional[list] = None
    payment_frequency_months: int = Field(3, description="Payment frequency in months: 1=monthly, 3=quarterly, 6=semi-annual, 12=annual")


# ── Position schemas for reprice-portfolio ──

class NdfPosition(BaseModel):
    notional_usd: float
    strike: float
    maturity_date: str = Field(..., description="ISO date string YYYY-MM-DD")
    direction: str = Field("buy", description="'buy' or 'sell'")
    spot: Optional[float] = None
    use_market_forward: bool = False
    market_forward: Optional[float] = None
    position_id: Optional[str] = Field(None, description="Optional identifier for the position")


class IbrSwapPosition(BaseModel):
    notional: float
    tenor_years: Optional[int] = None
    maturity_date: Optional[str] = None
    fixed_rate: float = Field(..., description="Fixed rate as decimal (e.g., 0.095)")
    pay_fixed: bool = True
    spread: float = 0.0
    position_id: Optional[str] = Field(None, description="Optional identifier for the position")


class XccySwapPosition(BaseModel):
    notional_usd: float
    start_date: str
    maturity_date: str
    xccy_basis_bps: float = 0.0
    pay_usd: bool = True
    fx_initial: Optional[float] = None
    cop_spread_bps: float = 0.0
    usd_spread_bps: float = 0.0
    amortization_type: str = "bullet"
    amortization_schedule: Optional[list] = None
    payment_frequency_months: int = Field(3, description="Payment frequency in months: 1=monthly, 3=quarterly, 6=semi-annual, 12=annual")
    position_id: Optional[str] = Field(None, description="Optional identifier for the position")


class RepricePortfolioRequest(BaseModel):
    xccy_positions: List[XccySwapPosition] = Field(
        default_factory=list,
        description="List of XCCY swap positions to reprice",
    )
    ndf_positions: List[NdfPosition] = Field(
        default_factory=list,
        description="List of NDF positions to reprice",
    )
    ibr_swap_positions: List[IbrSwapPosition] = Field(
        default_factory=list,
        description="List of IBR swap positions to reprice",
    )
    valuation_date: Optional[str] = Field(
        None,
        description=(
            "ISO date string YYYY-MM-DD for historical repricing. "
            "When provided, curves are rebuilt from EOD market data for that date. "
            "When None, uses the currently built curves (today's market data)."
        ),
    )
