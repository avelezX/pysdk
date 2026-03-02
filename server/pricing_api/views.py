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
    body = json.loads(request.body)

    market_ytm = body.get("market_ytm")
    valuation_date_str = body.get("valuation_date")

    # When market_ytm is supplied, we bypass the TES curve entirely.
    if market_ytm is None:
        err = _ensure_curves()
        if err:
            return err
        if cm.tes_curve is None:
            return responseHttpError("TES curve not built", 400)

    original_eval_date = None
    if valuation_date_str is not None:
        original_eval_date = ql.Settings.instance().evaluationDate
        hist_date = _parse_date(valuation_date_str)
        cm.set_valuation_date(hist_date)

    try:
        tes = TesBondPricer(cm)
        result = tes.analytics(
            issue_date=_parse_date(body["issue_date"]),
            maturity_date=_parse_date(body["maturity_date"]),
            coupon_rate=body["coupon_rate"],
            market_clean_price=body.get("market_clean_price"),
            face_value=body.get("face_value", 100.0),
            market_ytm=market_ytm,
        )
    finally:
        if original_eval_date is not None:
            cm.set_valuation_date(original_eval_date)

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


# ── Portfolio Repricing ──

@csrf_exempt
def pricing_reprice_portfolio(request):
    """Reprice a portfolio of derivatives (XCCY swaps, NDFs, IBR swaps).

    Supports optional historical repricing via valuation_date (backward compatible):

    - When valuation_date is None: uses currently loaded curves (existing behavior).
    - When valuation_date is provided: rebuilds all curves from EOD market data for
      that date (IBR, SOFR, FX spot) before pricing, then restores the original state.

    Request body (all position lists optional, default to []):
        xccy_positions: list of XCCY position objects
        ndf_positions: list of NDF position objects
        ibr_swap_positions: list of IBR swap position objects
        valuation_date: ISO date string YYYY-MM-DD (optional)
    """
    cm = _get_cm()
    loader = _get_loader()
    body = json.loads(request.body) if request.body else {}

    valuation_date_str = body.get("valuation_date")

    original_eval_date = None
    original_ibr_market = None
    original_sofr_market = None
    original_fx_spot = None
    curves_rebuilt_for_history = False

    if valuation_date_str is not None:
        original_eval_date = ql.Settings.instance().evaluationDate
        original_ibr_market = dict(cm._ibr_market)
        original_sofr_market = dict(cm._sofr_market)
        original_fx_spot = cm.fx_spot

        hist_date = _parse_date(valuation_date_str)
        cm.set_valuation_date(hist_date)

        ibr_data = loader.fetch_ibr_quotes(target_date=valuation_date_str)
        if ibr_data:
            cm.build_ibr_curve(ibr_data)

        sofr_data = loader.fetch_sofr_curve(target_date=valuation_date_str)
        if not sofr_data.empty:
            cm.build_sofr_curve(sofr_data)

        fx = loader.fetch_usdcop_spot(target_date=valuation_date_str)
        if fx:
            cm.set_fx_spot(fx)

        curves_rebuilt_for_history = True

    try:
        err = _ensure_curves()
        if err:
            return err

        xccy_pricer = XccySwapPricer(cm)
        ndf_pricer = NdfPricer(cm)
        ibr_pricer = IbrSwapPricer(cm)

        xccy_results = []
        ndf_results = []
        ibr_results = []
        total_npv_cop = 0.0

        for pos in body.get("xccy_positions", []):
            result = xccy_pricer.price(
                notional_usd=pos["notional_usd"],
                start_date=_parse_date(pos["start_date"]),
                maturity_date=_parse_date(pos["maturity_date"]),
                xccy_basis_bps=pos.get("xccy_basis_bps", 0.0),
                pay_usd=pos.get("pay_usd", True),
                fx_initial=pos.get("fx_initial"),
                cop_spread_bps=pos.get("cop_spread_bps", 0.0),
                usd_spread_bps=pos.get("usd_spread_bps", 0.0),
            )
            row = _serialize(result)
            if pos.get("position_id"):
                row["position_id"] = pos["position_id"]
            xccy_results.append(row)
            total_npv_cop += result.get("npv_cop", 0.0)

        for pos in body.get("ndf_positions", []):
            mat = _parse_date(pos["maturity_date"])
            if pos.get("use_market_forward") and pos.get("market_forward"):
                result = ndf_pricer.price_from_market_points(
                    notional_usd=pos["notional_usd"],
                    strike=pos["strike"],
                    maturity_date=mat,
                    market_forward=pos["market_forward"],
                    direction=pos.get("direction", "buy"),
                    spot=pos.get("spot"),
                )
            else:
                result = ndf_pricer.price(
                    notional_usd=pos["notional_usd"],
                    strike=pos["strike"],
                    maturity_date=mat,
                    direction=pos.get("direction", "buy"),
                    spot=pos.get("spot"),
                )
            row = _serialize(result)
            if pos.get("position_id"):
                row["position_id"] = pos["position_id"]
            ndf_results.append(row)
            total_npv_cop += result.get("npv_cop", 0.0)

        for pos in body.get("ibr_swap_positions", []):
            if pos.get("tenor_years"):
                tenor = ql.Period(int(pos["tenor_years"]), ql.Years)
                result = ibr_pricer.price(
                    pos["notional"], tenor, pos["fixed_rate"],
                    pos.get("pay_fixed", True), pos.get("spread", 0.0),
                )
            elif pos.get("maturity_date"):
                mat = _parse_date(pos["maturity_date"])
                result = ibr_pricer.price(
                    pos["notional"], mat, pos["fixed_rate"],
                    pos.get("pay_fixed", True), pos.get("spread", 0.0),
                )
            else:
                return responseHttpError(
                    f"IBR swap position '{pos.get('position_id', '?')}' requires "
                    "either tenor_years or maturity_date.",
                    400,
                )
            row = _serialize(result)
            if pos.get("position_id"):
                row["position_id"] = pos["position_id"]
            ibr_results.append(row)
            total_npv_cop += result.get("npv", 0.0)

        fx_spot_used = cm.fx_spot
        return responseHttpOk({
            "valuation_date": valuation_date_str,
            "fx_spot": fx_spot_used,
            "xccy_swaps": xccy_results,
            "ndfs": ndf_results,
            "ibr_swaps": ibr_results,
            "total_npv_cop": round(total_npv_cop, 2),
            "total_npv_usd": round(total_npv_cop / fx_spot_used, 2) if fx_spot_used else None,
        })

    finally:
        if curves_rebuilt_for_history:
            cm.set_valuation_date(original_eval_date)
            loader_ibr = loader.fetch_ibr_quotes()
            if loader_ibr:
                cm.build_ibr_curve(loader_ibr)
            loader_sofr = loader.fetch_sofr_curve()
            if not loader_sofr.empty:
                cm.build_sofr_curve(loader_sofr)
            if original_fx_spot is not None:
                cm.set_fx_spot(original_fx_spot)
