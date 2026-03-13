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


class NdfResponse(BaseModel):
    """
    Response contract for POST /pricing/ndf.

    All monetary values are in their natural currency (COP or USD).
    All rates are expressed as USD/COP (pesos per dollar).

    ── Pricing ──────────────────────────────────────────────────────────────
    npv_cop         Net present value in COP.
                    Positive = gain for the client (in the declared direction).
                    npv_cop = sign × notional_usd × (forward − strike) × df_cop

    npv_usd         Net present value in USD = npv_cop / spot.

    ── Forward ──────────────────────────────────────────────────────────────
    forward         Implied forward rate USD/COP used for pricing.
                    When use_market_forward=False: F = spot × df_usd / df_cop
                      (interest rate parity, using NDF market curve for df_cop
                       if available, else IBR fallback).
                    When use_market_forward=True: equals the market_forward
                      value supplied in the request.

    forward_points  forward − spot.  Positive = COP trades at a premium
                    (expected depreciation). Unit: COP pesos.

    strike          Contracted forward rate from the request (USD/COP).

    ── Discount factors ─────────────────────────────────────────────────────
    df_usd          SOFR discount factor at maturity: DF_USD(T).
                    DF = 1 at T=0, declines toward 0 as T increases.

    df_cop          COP discount factor at maturity: DF_COP(T).
                    Source depends on curve_source (see below).

    ── Risk ─────────────────────────────────────────────────────────────────
    delta_cop       FX delta in COP.
                    Approximate change in npv_cop for a 1 COP/USD move in spot.
                    = sign × notional_usd × df_cop
                    Example: delta_cop = 490,000 means that if spot rises 1 COP,
                    npv_cop increases by COP 490,000 (for a buy position).

    ── Trade inputs (echoed back for UI convenience) ────────────────────────
    notional_usd    USD notional from the request.
    direction       'buy' (long USD) or 'sell' (short USD).
    spot            USD/COP spot rate used. If not supplied in the request,
                    this is the latest SET-ICAP fixing from cm.fx_spot.
    maturity        Maturity/fixing date as ISO string YYYY-MM-DD.

    ── Metadata ─────────────────────────────────────────────────────────────
    days_to_maturity  Calendar days from today (valuation date) to maturity.

    curve_source    Indicates which COP discount curve was used:
                    'ndf_market'  — NDF market curve bootstrapped from
                                    market_marks.ndf (preferred, captures
                                    convertibility risk and market basis).
                    'ibr_fallback' — IBR OIS curve used (market_marks not
                                    available for this date).
                    'market_forward' — Caller supplied market_forward directly
                                    (use_market_forward=True); df_cop still
                                    uses the same curve logic above.
    """

    npv_cop: float = Field(..., description="Net present value in COP.")
    npv_usd: float = Field(..., description="Net present value in USD.")
    forward: float = Field(..., description="Forward rate USD/COP used for pricing.")
    forward_points: float = Field(..., description="Forward minus spot (COP pesos).")
    strike: float = Field(..., description="Contracted forward rate USD/COP.")
    df_usd: float = Field(..., description="SOFR discount factor at maturity.")
    df_cop: float = Field(..., description="COP discount factor at maturity.")
    delta_cop: float = Field(..., description="FX delta: npv_cop change per 1 COP/USD spot move.")
    notional_usd: float = Field(..., description="USD notional.")
    direction: str = Field(..., description="'buy' or 'sell'.")
    spot: float = Field(..., description="USD/COP spot rate used.")
    maturity: str = Field(..., description="Maturity/fixing date ISO string YYYY-MM-DD.")
    days_to_maturity: int = Field(..., description="Calendar days from valuation date to maturity.")
    curve_source: str = Field(
        ...,
        description=(
            "'ndf_market' = NDF market curve from market_marks (preferred). "
            "'ibr_fallback' = IBR OIS curve (market_marks unavailable). "
            "'market_forward' = caller supplied forward directly."
        ),
    )


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


class PeriodCashflow(BaseModel):
    """One row in the cashflow schedule of a USD/COP CCS."""
    period_num: int = Field(..., description="0 = inception notional exchange, 1..N = coupon periods.")
    date_start: str = Field(..., description="Period start date YYYY-MM-DD.")
    date_end: str = Field(..., description="Payment date YYYY-MM-DD.")
    notional_usd: float = Field(..., description="Outstanding USD notional during period.")
    notional_cop: float = Field(..., description="Outstanding COP notional during period.")
    usd_coupon: Optional[float] = Field(
        None,
        description="Estimated USD interest amount (unsigned). None for settled periods.",
    )
    cop_coupon: Optional[float] = Field(
        None,
        description="Estimated COP interest amount (unsigned). None for settled periods.",
    )
    usd_principal: float = Field(
        ...,
        description=(
            "Net USD principal flow at date_end, client perspective. "
            "Negative = pays (inception), positive = receives (amorts/maturity)."
        ),
    )
    cop_principal: float = Field(
        ...,
        description=(
            "Net COP principal flow at date_end, client perspective. "
            "Positive = receives (inception), negative = pays (amorts/maturity)."
        ),
    )
    usd_net: float = Field(..., description="Total net USD flow this period (coupon + principal).")
    cop_net: float = Field(..., description="Total net COP flow this period (coupon + principal).")
    ibr_fwd_pct: Optional[float] = Field(None, description="IBR forward rate % for this period. None for settled.")
    sofr_fwd_pct: Optional[float] = Field(None, description="SOFR forward rate % for this period. None for settled.")
    status: str = Field(..., description="'settled' (past), 'current' (active accrual), 'future'.")


class XccyCashflowResponse(BaseModel):
    """
    Response for POST /pricing/xccy-swap/cashflows.

    Full cashflow schedule from inception to maturity.
    Period 0 = inception notional exchange. Periods 1..n_periods = coupons + amortizations.

    Sign convention (pay_usd=True):
        usd_net < 0  client pays USD  (coupons + inception notional)
        usd_net > 0  client receives USD (amort returns + final)
        cop_net > 0  client receives COP (coupons + inception notional)
        cop_net < 0  client pays COP (amort returns + final)

    Settled period coupons are None — realized compounded rates are not stored here.
    """
    notional_usd: float
    notional_cop: float
    fx_initial: float = Field(..., description="USD/COP rate at inception.")
    fx_spot: float = Field(..., description="Current USD/COP spot (reference).")
    start_date: str
    maturity_date: str
    amortization_type: str
    pay_usd: bool
    n_periods: int = Field(..., description="Number of coupon periods (excludes inception row).")
    periods: List[PeriodCashflow] = Field(..., description="Period 0 (inception) + periods 1..N.")


class CurrentPeriodInfo(BaseModel):
    """Current accrual period details for an XCCY swap."""
    start: str = Field(..., description="Period start date YYYY-MM-DD.")
    end: str = Field(..., description="Period end date YYYY-MM-DD.")
    days_elapsed: int = Field(..., description="Calendar days elapsed in this period.")
    notional_usd: float = Field(..., description="Outstanding USD notional this period.")
    notional_cop: float = Field(..., description="Outstanding COP notional this period.")
    ibr_fwd_pct: float = Field(..., description="IBR forward rate for this period, in percent.")
    sofr_fwd_pct: float = Field(..., description="SOFR forward rate for this period, in percent.")
    differential_bps: float = Field(..., description="IBR − SOFR forward rate differential, in bps.")


class XccySwapResponse(BaseModel):
    """
    Response contract for POST /pricing/xccy-swap.

    ── Valuation ────────────────────────────────────────────────────────────
    npv_cop             Net present value in COP from the client's perspective.
                        Positive = gain for the client.
                        npv_cop = sign × (−usd_total × fx_spot + cop_total)
    npv_usd             NPV converted to USD = npv_cop / fx_spot.

    ── Leg PVs ──────────────────────────────────────────────────────────────
    usd_leg_pv          PV of future USD interest cashflows (USD).
    cop_leg_pv          PV of future COP interest cashflows (COP).
    usd_notional_exchange_pv  PV of USD notional flows (USD, gross outflows).
    cop_notional_exchange_pv  PV of COP notional flows (COP, gross inflows).
    usd_total           usd_leg_pv + usd_notional_exchange_pv (USD).
    cop_total           cop_leg_pv + cop_notional_exchange_pv (COP).

    ── Notionals & FX ───────────────────────────────────────────────────────
    notional_usd        Original USD notional.
    notional_cop        COP notional = notional_usd × fx_initial.
    fx_initial          USD/COP rate used for the notional exchange at inception.
    fx_spot             Current USD/COP spot rate used for NPV conversion.

    ── Risk ─────────────────────────────────────────────────────────────────
    fx_delta_cop        d(npv_cop)/d(fx_spot) = sign × (−usd_total).
                        Approximate change in npv_cop for a 1 COP/USD move in spot.

    ── Carry ────────────────────────────────────────────────────────────────
    carry_daily_cop     Net daily carry in COP for the current accrual period.
                        = sign × (N_cop × (IBR_fwd + cop_spread) − N_usd × (SOFR_fwd + usd_spread) × spot) / 360
                        Positive = client earns positive carry (COP leg pays more than USD leg).
    carry_accrued_cop   Accrued carry in COP for days elapsed in the current period.
                        = carry_daily_cop × days_elapsed.

    ── Period metadata ──────────────────────────────────────────────────────
    days_open           Calendar days since trade inception (0 at inception).
    periods_remaining   Number of coupon periods still open (including current).
    current_period      Rates and notionals for the active accrual period.
                        None when the swap has fully expired.

    ── Trade inputs ─────────────────────────────────────────────────────────
    xccy_basis_bps      Cross-currency basis spread on the COP leg.
    amortization_type   'bullet', 'linear', or 'custom'.
    start_date          Trade start date ISO string.
    maturity_date       Trade maturity date ISO string.
    """

    # Valuation
    npv_cop: float = Field(..., description="Net present value in COP.")
    npv_usd: float = Field(..., description="Net present value in USD.")

    # Leg PVs
    usd_leg_pv: float = Field(..., description="PV of future USD interest cashflows (USD).")
    cop_leg_pv: float = Field(..., description="PV of future COP interest cashflows (COP).")
    usd_notional_exchange_pv: float = Field(..., description="PV of USD notional flows (USD, gross).")
    cop_notional_exchange_pv: float = Field(..., description="PV of COP notional flows (COP, gross).")
    usd_total: float = Field(..., description="usd_leg_pv + usd_notional_exchange_pv (USD).")
    cop_total: float = Field(..., description="cop_leg_pv + cop_notional_exchange_pv (COP).")

    # Notionals & FX
    notional_usd: float = Field(..., description="Original USD notional.")
    notional_cop: float = Field(..., description="COP notional at inception FX.")
    fx_initial: float = Field(..., description="USD/COP FX rate at inception.")
    fx_spot: float = Field(..., description="Current USD/COP spot rate.")

    # Risk
    fx_delta_cop: float = Field(..., description="d(npv_cop)/d(spot): npv_cop change per 1 COP/USD move.")

    # Carry
    carry_daily_cop: float = Field(..., description="Net daily carry in COP for the current accrual period.")
    carry_accrued_cop: float = Field(..., description="Accrued carry in COP for days elapsed in the current period.")

    # Period metadata
    days_open: int = Field(..., description="Calendar days since inception (0 at inception).")
    periods_remaining: int = Field(..., description="Coupon periods still open (including current).")
    current_period: Optional[CurrentPeriodInfo] = Field(
        None, description="Active accrual period rates and notionals. None when swap has expired."
    )

    # Trade inputs
    xccy_basis_bps: float = Field(..., description="Cross-currency basis spread on COP leg, in bps.")
    amortization_type: str = Field(..., description="'bullet', 'linear', or 'custom'.")
    start_date: str = Field(..., description="Trade start date YYYY-MM-DD.")
    maturity_date: str = Field(..., description="Trade maturity date YYYY-MM-DD.")


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
