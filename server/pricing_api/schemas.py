"""Pydantic request/response models for pricing API."""
from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional
from datetime import datetime

_VALID_AMORT_TYPES = {"bullet", "linear", "custom"}
_VALID_FREQ_MONTHS = {1, 3, 6, 12}


def _parse_date(s: str) -> datetime:
    try:
        return datetime.strptime(s, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"Date must be YYYY-MM-DD, got '{s}'")


class BuildCurvesRequest(BaseModel):
    target_date: Optional[str] = Field(None, description="ISO date string. None = latest.")


class BumpRequest(BaseModel):
    curve: str = Field(..., description="'ibr' or 'sofr'")
    bps: Optional[float] = Field(None, description="Parallel shift in bps")
    node: Optional[str] = Field(None, description="Tenor key (e.g., 'ibr_5y' or '60')")
    rate_pct: Optional[float] = Field(None, description="New rate in percent for the node")


_VALID_DIRECTIONS = {"buy", "sell"}


class NdfRequest(BaseModel):
    notional_usd: float = Field(..., gt=0, description="USD notional amount. Must be positive.")
    strike: float = Field(..., gt=0, description="Contracted forward rate (USD/COP). Must be positive.")
    maturity_date: str = Field(..., description="ISO date string YYYY-MM-DD")
    direction: str = Field("buy", description="'buy' or 'sell'")
    spot: Optional[float] = Field(None, gt=0, description="USD/COP spot rate. Defaults to cm.fx_spot.")
    use_market_forward: bool = Field(False, description="Use market forward instead of implied from curves.")
    market_forward: Optional[float] = Field(None, gt=0, description="Market forward rate (required when use_market_forward=True).")

    @field_validator("maturity_date")
    @classmethod
    def validate_maturity_date(cls, v):
        _parse_date(v)
        return v

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v):
        if v not in _VALID_DIRECTIONS:
            raise ValueError(f"direction must be 'buy' or 'sell', got '{v}'")
        return v

    @model_validator(mode="after")
    def validate_market_forward_required(self):
        if self.use_market_forward and self.market_forward is None:
            raise ValueError("market_forward is required when use_market_forward=True")
        return self


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
    notional_usd: float = Field(..., gt=0, description="USD notional amount. Must be positive.")
    start_date: str = Field(..., description="Trade start date (YYYY-MM-DD).")
    maturity_date: str = Field(..., description="Trade maturity date (YYYY-MM-DD). Must be after start_date.")
    xccy_basis_bps: float = Field(0.0, description="Cross-currency basis spread on COP leg, in bps.")
    pay_usd: bool = Field(True, description="True = client pays USD / receives COP (standard). False = reverse.")
    fx_initial: Optional[float] = Field(None, gt=0, description="USD/COP FX rate at inception. Defaults to current spot.")
    cop_spread_bps: float = Field(0.0, description="Additional spread on COP leg, in bps. Usually 0.")
    usd_spread_bps: float = Field(0.0, description="Spread on USD/SOFR leg, in bps. Use -22 for SOFR-22bps.")
    amortization_type: str = Field("bullet", description="'bullet', 'linear', or 'custom'.")
    amortization_schedule: Optional[list] = Field(None, description="Required for amortization_type='custom'. List of notional factors (0–1) per period.")
    payment_frequency_months: int = Field(3, description="Payment frequency in months: 1=monthly, 3=quarterly, 6=semi-annual, 12=annual.")

    @field_validator("start_date", "maturity_date")
    @classmethod
    def validate_date_format(cls, v):
        _parse_date(v)
        return v

    @field_validator("amortization_type")
    @classmethod
    def validate_amort_type(cls, v):
        if v not in _VALID_AMORT_TYPES:
            raise ValueError(f"amortization_type must be one of {_VALID_AMORT_TYPES}, got '{v}'")
        return v

    @field_validator("payment_frequency_months")
    @classmethod
    def validate_frequency(cls, v):
        if v not in _VALID_FREQ_MONTHS:
            raise ValueError(f"payment_frequency_months must be one of {sorted(_VALID_FREQ_MONTHS)}, got {v}")
        return v

    @model_validator(mode="after")
    def validate_dates_and_schedule(self):
        start = _parse_date(self.start_date)
        maturity = _parse_date(self.maturity_date)
        if maturity <= start:
            raise ValueError("maturity_date must be after start_date")
        if self.amortization_type == "custom" and not self.amortization_schedule:
            raise ValueError("amortization_schedule is required when amortization_type='custom'")
        return self


# ── Position schemas for reprice-portfolio ──

class NdfPosition(BaseModel):
    notional_usd: float = Field(..., gt=0)
    strike: float = Field(..., gt=0)
    maturity_date: str = Field(..., description="ISO date string YYYY-MM-DD")
    direction: str = Field("buy", description="'buy' or 'sell'")
    spot: Optional[float] = Field(None, gt=0)
    use_market_forward: bool = False
    market_forward: Optional[float] = Field(None, gt=0)
    position_id: Optional[str] = Field(None, description="Optional identifier for the position")

    @field_validator("maturity_date")
    @classmethod
    def validate_maturity_date(cls, v):
        _parse_date(v)
        return v

    @field_validator("direction")
    @classmethod
    def validate_direction(cls, v):
        if v not in _VALID_DIRECTIONS:
            raise ValueError(f"direction must be 'buy' or 'sell', got '{v}'")
        return v

    @model_validator(mode="after")
    def validate_market_forward_required(self):
        if self.use_market_forward and self.market_forward is None:
            raise ValueError("market_forward is required when use_market_forward=True")
        return self


class IbrSwapPosition(BaseModel):
    notional: float
    tenor_years: Optional[int] = None
    maturity_date: Optional[str] = None
    fixed_rate: float = Field(..., description="Fixed rate as decimal (e.g., 0.095)")
    pay_fixed: bool = True
    spread: float = 0.0
    position_id: Optional[str] = Field(None, description="Optional identifier for the position")


class XccySwapPosition(BaseModel):
    notional_usd: float = Field(..., gt=0)
    start_date: str
    maturity_date: str
    xccy_basis_bps: float = 0.0
    pay_usd: bool = True
    fx_initial: Optional[float] = Field(None, gt=0)
    cop_spread_bps: float = 0.0
    usd_spread_bps: float = 0.0
    amortization_type: str = "bullet"
    amortization_schedule: Optional[list] = None
    payment_frequency_months: int = Field(3, description="Payment frequency in months: 1=monthly, 3=quarterly, 6=semi-annual, 12=annual")
    position_id: Optional[str] = Field(None, description="Optional identifier for the position")

    @field_validator("start_date", "maturity_date")
    @classmethod
    def validate_date_format(cls, v):
        _parse_date(v)
        return v

    @field_validator("amortization_type")
    @classmethod
    def validate_amort_type(cls, v):
        if v not in _VALID_AMORT_TYPES:
            raise ValueError(f"amortization_type must be one of {_VALID_AMORT_TYPES}, got '{v}'")
        return v

    @field_validator("payment_frequency_months")
    @classmethod
    def validate_frequency(cls, v):
        if v not in _VALID_FREQ_MONTHS:
            raise ValueError(f"payment_frequency_months must be one of {sorted(_VALID_FREQ_MONTHS)}, got {v}")
        return v

    @model_validator(mode="after")
    def validate_dates_and_schedule(self):
        start = _parse_date(self.start_date)
        maturity = _parse_date(self.maturity_date)
        if maturity <= start:
            raise ValueError("maturity_date must be after start_date")
        if self.amortization_type == "custom" and not self.amortization_schedule:
            raise ValueError("amortization_schedule is required when amortization_type='custom'")
        return self


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
