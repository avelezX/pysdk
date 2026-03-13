"""
FastAPI pricing endpoints.

The CurveManager is created as a singleton at module level.
It gets initialized on the first /pricing/curves/build call.
"""
from __future__ import annotations

import QuantLib as ql
from datetime import datetime
from fastapi import APIRouter, HTTPException

from pricing.curves.curve_manager import CurveManager
from pricing.data.market_data import MarketDataLoader
from pricing.instruments.ndf import NdfPricer
from pricing.instruments.ibr_swap import IbrSwapPricer
from pricing.instruments.tes_bond import TesBondPricer
from pricing.instruments.xccy_swap import XccySwapPricer
from utilities.date_functions import datetime_to_ql

from server.pricing_api.schemas import (
    BuildCurvesRequest,
    BumpRequest,
    NdfRequest,
    NdfResponse,
    IbrSwapRequest,
    TesBondRequest,
    XccySwapRequest,
    XccySwapResponse,
    XccyCashflowResponse,
    RepricePortfolioRequest,
)

router = APIRouter(prefix="/pricing", tags=["pricing"])

# Singleton instances
_cm: CurveManager | None = None
_loader: MarketDataLoader | None = None


def _get_cm() -> CurveManager:
    global _cm
    if _cm is None:
        _cm = CurveManager()
    return _cm


def _get_loader() -> MarketDataLoader:
    global _loader
    if _loader is None:
        _loader = MarketDataLoader()
    return _loader


def _ensure_curves_built():
    cm = _get_cm()
    if cm.ibr_curve is None and cm.sofr_curve is None:
        raise HTTPException(
            status_code=400,
            detail="Curves not built. Call POST /pricing/curves/build first.",
        )


def _parse_date(s: str) -> ql.Date:
    dt = datetime.strptime(s, "%Y-%m-%d")
    return datetime_to_ql(dt)


# ── Curve Endpoints ──


@router.post("/curves/build")
def build_curves(req: BuildCurvesRequest = None):
    """Build or rebuild all curves from latest market data."""
    cm = _get_cm()
    loader = _get_loader()
    results = cm.build_all(loader)
    return {"status": "ok", "curves": results, "full_status": cm.status()}


@router.get("/curves/status")
def curves_status():
    """Get current curve build status and node values."""
    return _get_cm().status()


@router.post("/curves/bump")
def bump_curve(req: BumpRequest):
    """Bump a curve (parallel shift or single node)."""
    _ensure_curves_built()
    cm = _get_cm()

    if req.node and req.rate_pct is not None:
        if req.curve == "ibr":
            cm.set_ibr_node(req.node, req.rate_pct)
        elif req.curve == "sofr":
            cm.set_sofr_node(int(req.node), req.rate_pct)
        else:
            raise HTTPException(400, f"Unknown curve: {req.curve}")
        return {"status": "node_set", "curve": req.curve, "node": req.node, "rate_pct": req.rate_pct}

    elif req.bps is not None:
        if req.curve == "ibr":
            cm.bump_ibr(req.bps)
        elif req.curve == "sofr":
            cm.bump_sofr(req.bps)
        else:
            raise HTTPException(400, f"Unknown curve: {req.curve}")
        return {"status": "bumped", "curve": req.curve, "bps": req.bps}

    raise HTTPException(400, "Provide either (node + rate_pct) or bps")


@router.post("/curves/reset")
def reset_curves():
    """Reset all curves to original market values."""
    _get_cm().reset_to_market()
    return {"status": "reset"}


# ── NDF Endpoints ──


@router.post("/ndf", response_model=NdfResponse)
def price_ndf(req: NdfRequest):
    """Price a USD/COP Non-Deliverable Forward (NDF).

    ── Request fields ────────────────────────────────────────────────────────
    notional_usd        USD notional of the trade. Must be positive.
    strike              Agreed forward rate at inception (USD/COP). Must be positive.
    maturity_date       Fixing/settlement date in YYYY-MM-DD format.
    direction           'buy' = long USD (client pays COP, receives USD at maturity);
                        'sell' = short USD (client pays USD, receives COP).
    spot                (optional) USD/COP spot override. Defaults to cm.fx_spot
                        (latest SET-ICAP fixing loaded by build_curves).
    use_market_forward  When True, supply market_forward instead of computing
                        the forward from interest-rate parity.
    market_forward      Required when use_market_forward=True. The market-quoted
                        forward rate (USD/COP) to use directly for pricing.
                        Useful when the desk has a specific agreed rate that
                        differs from the model-implied forward.

    ── How the forward is determined ────────────────────────────────────────
    • use_market_forward=False (default):
        F = spot × DF_USD(T) / DF_COP(T)
        DF_COP source depends on curve availability (see curve_source in response).
    • use_market_forward=True:
        F = market_forward (exact value from request, no curve needed for forward).
        DF_COP is still read from the active COP curve for discounting.

    ── COP discount curve priority ───────────────────────────────────────────
    1. NDF market curve (built from market_marks.ndf when available).
       Captures convertibility risk and NDF supply/demand.
       → curve_source = 'ndf_market'
    2. IBR OIS curve (fallback when market_marks are unavailable).
       Theoretical interest-rate-parity curve; misses NDF basis.
       → curve_source = 'ibr_fallback'

    ── Response fields ───────────────────────────────────────────────────────
    See NdfResponse schema for full field documentation.
    """
    _ensure_curves_built()
    cm = _get_cm()
    ndf = NdfPricer(cm)
    mat = _parse_date(req.maturity_date)

    if req.use_market_forward and req.market_forward is not None:
        result = ndf.price_from_market_points(
            notional_usd=req.notional_usd,
            strike=req.strike,
            maturity_date=mat,
            market_forward=req.market_forward,
            direction=req.direction,
            spot=req.spot,
        )
        curve_source = "market_forward"
    else:
        result = ndf.price(
            notional_usd=req.notional_usd,
            strike=req.strike,
            maturity_date=mat,
            direction=req.direction,
            spot=req.spot,
        )
        curve_source = "ndf_market" if cm.ndf_curve is not None else "ibr_fallback"

    # Convert datetime to string for JSON
    if "maturity" in result and hasattr(result["maturity"], "isoformat"):
        result["maturity"] = result["maturity"].isoformat()

    result["days_to_maturity"] = int(mat - cm.valuation_date)
    result["curve_source"] = curve_source

    return result


@router.get("/ndf/implied-curve")
def ndf_implied_curve():
    """Get implied forward curve vs market forwards."""
    _ensure_curves_built()
    cm = _get_cm()
    loader = _get_loader()
    ndf = NdfPricer(cm)

    cop_fwd = loader.fetch_cop_forwards()
    if cop_fwd.empty:
        raise HTTPException(404, "No COP forward data available")

    df = ndf.implied_curve(cop_fwd)
    return df.to_dict(orient="records")


# ── IBR Swap Endpoints ──


@router.post("/ibr-swap")
def price_ibr_swap(req: IbrSwapRequest):
    """Price an IBR OIS swap."""
    _ensure_curves_built()
    cm = _get_cm()
    ibr = IbrSwapPricer(cm)

    if req.tenor_years is not None:
        tenor = ql.Period(req.tenor_years, ql.Years)
        result = ibr.price(req.notional, tenor, req.fixed_rate, req.pay_fixed, req.spread)
    elif req.maturity_date is not None:
        mat = _parse_date(req.maturity_date)
        result = ibr.price(req.notional, mat, req.fixed_rate, req.pay_fixed, req.spread)
    else:
        raise HTTPException(400, "Provide either tenor_years or maturity_date")

    return result


@router.get("/ibr/par-curve")
def ibr_par_curve():
    """Get IBR par swap rate curve for standard tenors."""
    _ensure_curves_built()
    cm = _get_cm()
    ibr = IbrSwapPricer(cm)
    df = ibr.par_curve()
    return df.to_dict(orient="records")


# ── TES Bond Endpoints ──


@router.post("/tes-bond")
def price_tes_bond(req: TesBondRequest):
    """Price a TES bond with full analytics.

    Supports two historical-repricing modes (backward compatible — all new params
    are optional and default to existing behavior):

    1. market_ytm: When provided, uses this YTM directly instead of fetching from
       the TES curve. The TES curve does NOT need to be built. Ideal for historical
       marks pricing where the frontend supplies the EOD YTM per bond.

    2. valuation_date: When provided, shifts the QuantLib evaluation date so that
       accrual, duration, and convexity are computed as of that historical date.
       Falls back to today when None.
    """
    cm = _get_cm()

    # When market_ytm is supplied, we bypass the TES curve entirely.
    # The bond is still priced relative to its own fixed cash-flows; the caller
    # provides the market yield (e.g. from xerenity.get_tes_yield_curve_for_date).
    if req.market_ytm is None:
        # Standard path: need the TES curve to derive price/yield.
        _ensure_curves_built()
        if cm.tes_curve is None:
            raise HTTPException(400, "TES curve not built. Provide bond data via /curves/build.")

    # Override valuation date when pricing a historical mark.
    original_eval_date = None
    if req.valuation_date is not None:
        original_eval_date = ql.Settings.instance().evaluationDate
        hist_date = _parse_date(req.valuation_date)
        cm.set_valuation_date(hist_date)

    try:
        tes = TesBondPricer(cm)
        result = tes.analytics(
            issue_date=_parse_date(req.issue_date),
            maturity_date=_parse_date(req.maturity_date),
            coupon_rate=req.coupon_rate,
            market_clean_price=req.market_clean_price,
            face_value=req.face_value,
            market_ytm=req.market_ytm,
        )
    finally:
        # Restore the global evaluation date so we don't affect other requests.
        if original_eval_date is not None:
            cm.set_valuation_date(original_eval_date)

    if "maturity" in result and hasattr(result["maturity"], "isoformat"):
        result["maturity"] = result["maturity"].isoformat()

    return result


# ── Cross-Currency Swap Endpoints ──


@router.post("/xccy-swap", response_model=XccySwapResponse)
def price_xccy_swap(req: XccySwapRequest):
    """Price a USD/COP cross-currency swap."""
    _ensure_curves_built()
    cm = _get_cm()
    xccy = XccySwapPricer(cm)

    result = xccy.price(
        notional_usd=req.notional_usd,
        start_date=_parse_date(req.start_date),
        maturity_date=_parse_date(req.maturity_date),
        xccy_basis_bps=req.xccy_basis_bps,
        pay_usd=req.pay_usd,
        fx_initial=req.fx_initial,
        cop_spread_bps=req.cop_spread_bps,
        usd_spread_bps=req.usd_spread_bps,
        amortization_type=req.amortization_type,
        amortization_schedule=req.amortization_schedule,
        payment_frequency=ql.Period(req.payment_frequency_months, ql.Months),
    )

    # Convert top-level datetime objects to ISO strings for schema validation
    for key in ("start_date", "maturity_date"):
        if key in result and hasattr(result[key], "strftime"):
            result[key] = result[key].strftime("%Y-%m-%d")

    return result


@router.post("/xccy-swap/cashflows", response_model=XccyCashflowResponse)
def xccy_swap_cashflows(req: XccySwapRequest):
    """
    Full cashflow schedule for a USD/COP cross-currency swap.

    Returns one row per period:
      - Period 0: inception notional exchange (pay USD / receive COP)
      - Periods 1..N: quarterly coupons + amortization returns

    Settled period coupon estimates are None (realized rates not stored).
    All other fields (notionals, principal flows) are deterministic from trade terms.
    """
    _ensure_curves_built()
    cm = _get_cm()
    xccy = XccySwapPricer(cm)

    fx = req.fx_initial or cm.fx_spot
    periods = xccy.cashflows(
        notional_usd=req.notional_usd,
        start_date=_parse_date(req.start_date),
        maturity_date=_parse_date(req.maturity_date),
        xccy_basis_bps=req.xccy_basis_bps,
        pay_usd=req.pay_usd,
        fx_initial=req.fx_initial,
        cop_spread_bps=req.cop_spread_bps,
        usd_spread_bps=req.usd_spread_bps,
        amortization_type=req.amortization_type,
        amortization_schedule=req.amortization_schedule,
        payment_frequency=ql.Period(req.payment_frequency_months, ql.Months),
    )

    return {
        "notional_usd":      req.notional_usd,
        "notional_cop":      req.notional_usd * fx,
        "fx_initial":        fx,
        "fx_spot":           cm.fx_spot,
        "start_date":        req.start_date,
        "maturity_date":     req.maturity_date,
        "amortization_type": req.amortization_type,
        "pay_usd":           req.pay_usd,
        "n_periods":         len(periods) - 1,  # exclude inception row
        "periods":           periods,
    }


# ── Portfolio Repricing Endpoint ──


def _serialize_portfolio_result(result: dict) -> dict:
    """Convert datetime/date objects to ISO strings for JSON serialization."""
    out = {}
    for k, v in result.items():
        if hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        elif isinstance(v, float):
            out[k] = round(v, 6) if abs(v) < 1e12 else round(v, 2)
        else:
            out[k] = v
    return out


@router.post("/reprice-portfolio")
def reprice_portfolio(req: RepricePortfolioRequest):
    """Reprice a portfolio of derivatives (XCCY swaps, NDFs, IBR swaps).

    Supports optional historical repricing via valuation_date (backward compatible):

    - When valuation_date is None: uses currently loaded curves (existing behavior).
    - When valuation_date is provided: rebuilds all curves from EOD market data for
      that date (IBR, SOFR, FX spot) before pricing, then restores the original state.

    All position lists default to empty, so callers can send only the instrument
    types they hold.

    Returns:
        dict with per-instrument results and portfolio summary NPV.
    """
    cm = _get_cm()
    loader = _get_loader()

    # ── Historical repricing: rebuild curves for the requested date ──
    original_eval_date = None
    original_ibr_market = None
    original_sofr_market = None
    original_fx_spot = None
    curves_rebuilt_for_history = False

    if req.valuation_date is not None:
        # Save current state so we can restore after pricing.
        original_eval_date = ql.Settings.instance().evaluationDate
        original_ibr_market = dict(cm._ibr_market)
        original_sofr_market = dict(cm._sofr_market)
        original_fx_spot = cm.fx_spot

        # Set valuation date.
        hist_date = _parse_date(req.valuation_date)
        cm.set_valuation_date(hist_date)

        # Fetch historical market data for the requested date and rebuild curves.
        ibr_data = loader.fetch_ibr_quotes(target_date=req.valuation_date)
        if ibr_data:
            cm.build_ibr_curve(ibr_data)

        sofr_data = loader.fetch_sofr_curve(target_date=req.valuation_date)
        if not sofr_data.empty:
            cm.build_sofr_curve(sofr_data)

        fx = loader.fetch_usdcop_spot(target_date=req.valuation_date)
        if fx:
            cm.set_fx_spot(fx)

        curves_rebuilt_for_history = True

    try:
        _ensure_curves_built()

        xccy_pricer = XccySwapPricer(cm)
        ndf_pricer = NdfPricer(cm)
        ibr_pricer = IbrSwapPricer(cm)

        xccy_results = []
        ndf_results = []
        ibr_results = []

        total_npv_cop = 0.0

        # Price XCCY swaps
        for pos in req.xccy_positions:
            result = xccy_pricer.price(
                notional_usd=pos.notional_usd,
                start_date=_parse_date(pos.start_date),
                maturity_date=_parse_date(pos.maturity_date),
                xccy_basis_bps=pos.xccy_basis_bps,
                pay_usd=pos.pay_usd,
                fx_initial=pos.fx_initial,
                cop_spread_bps=pos.cop_spread_bps,
                usd_spread_bps=pos.usd_spread_bps,
                amortization_type=pos.amortization_type,
                amortization_schedule=pos.amortization_schedule,
                payment_frequency=ql.Period(pos.payment_frequency_months, ql.Months),
            )
            serialized = _serialize_portfolio_result(result)
            if pos.position_id is not None:
                serialized["position_id"] = pos.position_id
            xccy_results.append(serialized)
            total_npv_cop += result.get("npv_cop", 0.0)

        # Price NDFs
        for pos in req.ndf_positions:
            mat = _parse_date(pos.maturity_date)
            if pos.use_market_forward and pos.market_forward is not None:
                result = ndf_pricer.price_from_market_points(
                    notional_usd=pos.notional_usd,
                    strike=pos.strike,
                    maturity_date=mat,
                    market_forward=pos.market_forward,
                    direction=pos.direction,
                    spot=pos.spot,
                )
            else:
                result = ndf_pricer.price(
                    notional_usd=pos.notional_usd,
                    strike=pos.strike,
                    maturity_date=mat,
                    direction=pos.direction,
                    spot=pos.spot,
                )
            serialized = _serialize_portfolio_result(result)
            if pos.position_id is not None:
                serialized["position_id"] = pos.position_id
            ndf_results.append(serialized)
            total_npv_cop += result.get("npv_cop", 0.0)

        # Price IBR swaps
        for pos in req.ibr_swap_positions:
            if pos.tenor_years is not None:
                tenor = ql.Period(pos.tenor_years, ql.Years)
                result = ibr_pricer.price(
                    pos.notional, tenor, pos.fixed_rate, pos.pay_fixed, pos.spread
                )
            elif pos.maturity_date is not None:
                mat = _parse_date(pos.maturity_date)
                result = ibr_pricer.price(
                    pos.notional, mat, pos.fixed_rate, pos.pay_fixed, pos.spread
                )
            else:
                raise HTTPException(
                    400,
                    f"IBR swap position '{pos.position_id}' requires "
                    "either tenor_years or maturity_date.",
                )
            serialized = _serialize_portfolio_result(result)
            if pos.position_id is not None:
                serialized["position_id"] = pos.position_id
            ibr_results.append(serialized)
            # IBR NPV is already in COP.
            total_npv_cop += result.get("npv", 0.0)

        fx_spot_used = cm.fx_spot
        return {
            "valuation_date": req.valuation_date,
            "fx_spot": fx_spot_used,
            "xccy_swaps": xccy_results,
            "ndfs": ndf_results,
            "ibr_swaps": ibr_results,
            "total_npv_cop": round(total_npv_cop, 2),
            "total_npv_usd": round(total_npv_cop / fx_spot_used, 2) if fx_spot_used else None,
        }

    finally:
        # Restore original curves and evaluation date so the singleton is not
        # left in the historical state for subsequent requests.
        if curves_rebuilt_for_history:
            cm.set_valuation_date(original_eval_date)
            if original_ibr_market:
                # Rebuild curves from original market data to restore the handle.
                loader_ibr = loader.fetch_ibr_quotes()
                if loader_ibr:
                    cm.build_ibr_curve(loader_ibr)
            if original_sofr_market:
                loader_sofr = loader.fetch_sofr_curve()
                if not loader_sofr.empty:
                    cm.build_sofr_curve(loader_sofr)
            if original_fx_spot is not None:
                cm.set_fx_spot(original_fx_spot)
