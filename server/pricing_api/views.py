"""
Django views for pricing API.
Wraps the pricing module for the existing Django WSGI server.

The CurveManager is created as a module-level singleton.
It gets initialized on the first /pricing/curves/build call.
"""
import json
import QuantLib as ql
from datetime import datetime
from django.views.decorators.csrf import csrf_exempt
from server.main_server import responseHttpOk, responseHttpError

from pricing.curves.curve_manager import CurveManager
from pricing.data.market_data import MarketDataLoader
from pricing.instruments.ndf import NdfPricer
from pricing.instruments.ibr_swap import IbrSwapPricer
from pricing.instruments.tes_bond import TesBondPricer
from pricing.instruments.xccy_swap import XccySwapPricer
from utilities.date_functions import datetime_to_ql

# Module-level singletons
_cm = None
_loader = None


def _get_cm():
    global _cm
    if _cm is None:
        _cm = CurveManager()
    return _cm


def _get_loader():
    global _loader
    if _loader is None:
        _loader = MarketDataLoader()
    return _loader


def _parse_date(s):
    dt = datetime.strptime(s, "%Y-%m-%d")
    return datetime_to_ql(dt)


def _ensure_curves():
    cm = _get_cm()
    if cm.ibr_curve is None and cm.sofr_curve is None:
        return responseHttpError("Curves not built. Call POST /pricing_build first.", 400)
    return None


def _serialize(result):
    """Convert datetime objects to strings for JSON serialization."""
    out = {}
    for k, v in result.items():
        if hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        elif isinstance(v, float):
            out[k] = round(v, 6) if abs(v) < 1e12 else round(v, 2)
        else:
            out[k] = v
    return out


# ── Curve Endpoints ──

@csrf_exempt
def pricing_build(request):
    """Build or rebuild all curves from latest market data."""
    cm = _get_cm()
    loader = _get_loader()
    results = cm.build_all(loader)
    return responseHttpOk({"status": "ok", "curves": results, "full_status": cm.status()})


@csrf_exempt
def pricing_status(request):
    """Get current curve build status and node values."""
    return responseHttpOk(_get_cm().status())


@csrf_exempt
def pricing_bump(request):
    """Bump a curve (parallel shift or single node)."""
    err = _ensure_curves()
    if err:
        return err

    body = json.loads(request.body) if request.body else {}
    cm = _get_cm()
    curve = body.get("curve")
    node = body.get("node")
    rate_pct = body.get("rate_pct")
    bps = body.get("bps")

    if node and rate_pct is not None:
        if curve == "ibr":
            cm.set_ibr_node(node, rate_pct)
        elif curve == "sofr":
            cm.set_sofr_node(int(node), rate_pct)
        else:
            return responseHttpError(f"Unknown curve: {curve}", 400)
        return responseHttpOk({"status": "node_set", "curve": curve, "node": node, "rate_pct": rate_pct})

    elif bps is not None:
        if curve == "ibr":
            cm.bump_ibr(bps)
        elif curve == "sofr":
            cm.bump_sofr(bps)
        else:
            return responseHttpError(f"Unknown curve: {curve}", 400)
        return responseHttpOk({"status": "bumped", "curve": curve, "bps": bps})

    return responseHttpError("Provide either (node + rate_pct) or bps", 400)


@csrf_exempt
def pricing_reset(request):
    """Reset all curves to original market values."""
    _get_cm().reset_to_market()
    return responseHttpOk({"status": "reset"})


# ── NDF ──

@csrf_exempt
def pricing_ndf(request):
    """Price a USD/COP NDF."""
    err = _ensure_curves()
    if err:
        return err

    body = json.loads(request.body)
    cm = _get_cm()
    ndf = NdfPricer(cm)
    mat = _parse_date(body["maturity_date"])

    if body.get("use_market_forward") and body.get("market_forward"):
        result = ndf.price_from_market_points(
            notional_usd=body["notional_usd"],
            strike=body["strike"],
            maturity_date=mat,
            market_forward=body["market_forward"],
            direction=body.get("direction", "buy"),
            spot=body.get("spot"),
        )
    else:
        result = ndf.price(
            notional_usd=body["notional_usd"],
            strike=body["strike"],
            maturity_date=mat,
            direction=body.get("direction", "buy"),
            spot=body.get("spot"),
        )

    return responseHttpOk(_serialize(result))


@csrf_exempt
def pricing_ndf_implied_curve(request):
    """Get implied forward curve vs market forwards."""
    err = _ensure_curves()
    if err:
        return err

    cm = _get_cm()
    loader = _get_loader()
    ndf = NdfPricer(cm)
    cop_fwd = loader.fetch_cop_forwards()

    if cop_fwd.empty:
        return responseHttpError("No COP forward data available", 404)

    df = ndf.implied_curve(cop_fwd)
    return responseHttpOk(df.to_dict(orient="records"))


# ── IBR Swap ──

@csrf_exempt
def pricing_ibr_swap(request):
    """Price an IBR OIS swap."""
    err = _ensure_curves()
    if err:
        return err

    body = json.loads(request.body)
    cm = _get_cm()
    ibr = IbrSwapPricer(cm)

    if "tenor_years" in body and body["tenor_years"]:
        tenor = ql.Period(int(body["tenor_years"]), ql.Years)
        result = ibr.price(
            body["notional"], tenor, body["fixed_rate"],
            body.get("pay_fixed", True), body.get("spread", 0.0),
        )
    elif "maturity_date" in body and body["maturity_date"]:
        mat = _parse_date(body["maturity_date"])
        result = ibr.price(
            body["notional"], mat, body["fixed_rate"],
            body.get("pay_fixed", True), body.get("spread", 0.0),
        )
    else:
        return responseHttpError("Provide tenor_years or maturity_date", 400)

    return responseHttpOk(_serialize(result))


@csrf_exempt
def pricing_ibr_par_curve(request):
    """Get IBR par swap rate curve for standard tenors."""
    err = _ensure_curves()
    if err:
        return err

    cm = _get_cm()
    ibr = IbrSwapPricer(cm)
    df = ibr.par_curve()
    records = df.to_dict(orient="records")
    return responseHttpOk(records)


# ── TES Bond ──

@csrf_exempt
def pricing_tes_bond(request):
    """Price a TES bond with full analytics."""
    err = _ensure_curves()
    if err:
        return err

    cm = _get_cm()
    if cm.tes_curve is None:
        return responseHttpError("TES curve not built", 400)

    body = json.loads(request.body)
    tes = TesBondPricer(cm)
    result = tes.analytics(
        issue_date=_parse_date(body["issue_date"]),
        maturity_date=_parse_date(body["maturity_date"]),
        coupon_rate=body["coupon_rate"],
        market_clean_price=body.get("market_clean_price"),
        face_value=body.get("face_value", 100.0),
    )

    return responseHttpOk(_serialize(result))


# ── Xccy Swap ──

@csrf_exempt
def pricing_xccy_swap(request):
    """Price a USD/COP cross-currency swap."""
    err = _ensure_curves()
    if err:
        return err

    body = json.loads(request.body)
    cm = _get_cm()
    xccy = XccySwapPricer(cm)

    result = xccy.price(
        notional_usd=body["notional_usd"],
        start_date=_parse_date(body["start_date"]),
        maturity_date=_parse_date(body["maturity_date"]),
        xccy_basis_bps=body.get("xccy_basis_bps", 0.0),
        pay_usd=body.get("pay_usd", True),
        fx_initial=body.get("fx_initial"),
        cop_spread_bps=body.get("cop_spread_bps", 0.0),
        usd_spread_bps=body.get("usd_spread_bps", 0.0),
    )

    return responseHttpOk(_serialize(result))
