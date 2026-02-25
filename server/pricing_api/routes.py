"""
FastAPI pricing endpoints.

The CurveManager is created as a singleton at module level.
It gets initialized on the first /pricing/curves/build call.
"""
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
    IbrSwapRequest,
    TesBondRequest,
    XccySwapRequest,
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


@router.post("/ndf")
def price_ndf(req: NdfRequest):
    """Price a USD/COP NDF."""
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
    else:
        result = ndf.price(
            notional_usd=req.notional_usd,
            strike=req.strike,
            maturity_date=mat,
            direction=req.direction,
            spot=req.spot,
        )

    # Convert datetime to string for JSON
    if "maturity" in result and hasattr(result["maturity"], "isoformat"):
        result["maturity"] = result["maturity"].isoformat()

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
    """Price a TES bond with full analytics."""
    _ensure_curves_built()
    cm = _get_cm()
    if cm.tes_curve is None:
        raise HTTPException(400, "TES curve not built. Provide bond data via /curves/build.")

    tes = TesBondPricer(cm)
    result = tes.analytics(
        issue_date=_parse_date(req.issue_date),
        maturity_date=_parse_date(req.maturity_date),
        coupon_rate=req.coupon_rate,
        market_clean_price=req.market_clean_price,
        face_value=req.face_value,
    )

    if "maturity" in result and hasattr(result["maturity"], "isoformat"):
        result["maturity"] = result["maturity"].isoformat()

    return result


# ── Cross-Currency Swap Endpoints ──


@router.post("/xccy-swap")
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
    )

    for key in ("start_date", "maturity_date"):
        if key in result and hasattr(result[key], "isoformat"):
            result[key] = result[key].isoformat()

    return result
