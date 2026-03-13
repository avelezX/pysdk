"""
Django views for pricing API.
Wraps the pricing module for the existing Django WSGI server.

The CurveManager is created as a module-level singleton.
It gets initialized on the first /pricing/curves/build call.
"""
import json
import QuantLib as ql
from datetime import datetime, date, timedelta
from django.views.decorators.csrf import csrf_exempt
from server.main_server import responseHttpOk, responseHttpError

from pricing.curves.curve_manager import CurveManager
from pricing.data.market_data import MarketDataLoader
from pricing.instruments.ndf import NdfPricer
from pricing.instruments.ibr_swap import IbrSwapPricer
from pricing.instruments.tes_bond import TesBondPricer
from pricing.instruments.xccy_swap import XccySwapPricer, build_amortization_schedule
from utilities.date_functions import datetime_to_ql, ql_to_datetime

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


def _fetch_historical_spot(loader, fecha: str) -> float | None:
    """
    Fetch USD/COP spot for a historical date.

    Priority:
    1. market_marks.fx_spot — canonical EOD mark stored by run_compute_marks.py.
       This is the same value shown in the mark bar on the frontend, so using it
       ensures the spot used for pricing is consistent with what the user sees.
    2. fetch_usdcop_spot() — currency_hour (SET-ICAP) or cop_fwd_points fallback.
    """
    data = loader._get(
        "market_marks",
        f"select=fx_spot&fecha=eq.{fecha}&limit=1",
    )
    if data and data[0].get("fx_spot") is not None:
        return float(data[0]["fx_spot"])
    return loader.fetch_usdcop_spot(target_date=fecha)


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
        amortization_type=body.get("amortization_type", "bullet"),
        amortization_schedule=body.get("amortization_schedule"),
    )

    return responseHttpOk(_serialize(result))


# ── NDF Settlement ──

@csrf_exempt
def pricing_ndf_settlement(request):
    """Calculate the realized P&L for a settled (expired) NDF.

    At maturity the NDF fixes against the BanRep TRM (serie 25).
    Settlement P&L in COP:
        pyl_cop = sign * notional_usd * (trm_fixing - strike)
    where sign = +1 for 'buy' (long USD), -1 for 'sell' (short USD).

    TRM de liquidacion: la TRM es un promedio de las operaciones del dia
    anterior, publicada al dia habil siguiente al fixing_date. Se usa gte
    sobre maturity_date + 1 para capturar el primer dia habil posterior
    (maneja viernes → lunes, festivos, etc.).

    Does NOT require curves to be built — it is a pure arithmetic calculation
    over confirmed market data (BanRep TRM).

    Request body:
        notional_usd  (float)  – USD notional, positive
        strike        (float)  – contracted forward rate USD/COP
        maturity_date (str)    – fixing date YYYY-MM-DD
        direction     (str)    – 'buy' or 'sell' (default: 'buy')

    Response:
        trm_fixing    (float)  – BanRep TRM on (or before) maturity_date
        trm_date      (str)    – actual fecha of the TRM record used
        pyl_cop       (float)  – realized P&L in COP
        pyl_usd       (float)  – realized P&L in USD (pyl_cop / trm_fixing)
        strike        (float)  – contracted rate
        notional_usd  (float)
        direction     (str)
        maturity_date (str)
    """
    body = json.loads(request.body)
    notional_usd = float(body["notional_usd"])
    strike = float(body["strike"])
    maturity_date = body["maturity_date"]
    direction = body.get("direction", "buy")

    loader = _get_loader()

    # TRM de liquidación: la TRM publicada el día SIGUIENTE al fixing date.
    # La TRM es un promedio de las transacciones del día anterior — se publica
    # al día hábil siguiente. Si el día siguiente cae en fin de semana o festivo,
    # se toma el primer día hábil posterior (gte + order asc).
    next_date = (datetime.strptime(maturity_date, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    data = loader._get(
        "banrep_series_value_v2",
        f"select=valor,fecha&id_serie=eq.25"
        f"&fecha=gte.{next_date}&order=fecha.asc&limit=1",
    )
    if not data or data[0].get("valor") is None:
        return responseHttpError(
            f"TRM de liquidacion no disponible para fecha {maturity_date} "
            f"(se busca a partir de {next_date})", 404
        )

    trm_fixing = float(data[0]["valor"])
    trm_date = data[0]["fecha"]

    sign = 1.0 if direction == "buy" else -1.0
    pyl_cop = sign * notional_usd * (trm_fixing - strike)
    pyl_usd = pyl_cop / trm_fixing

    return responseHttpOk({
        "trm_fixing": round(trm_fixing, 4),
        "trm_date": trm_date,
        "pyl_cop": round(pyl_cop, 2),
        "pyl_usd": round(pyl_usd, 2),
        "strike": strike,
        "notional_usd": notional_usd,
        "direction": direction,
        "maturity_date": maturity_date,
    })


# ── Market Marks ──

@csrf_exempt
def pricing_marks_dates(request):
    """Return list of available dates in market_marks table (most recent first)."""
    loader = _get_loader()
    data = loader._get("market_marks", "select=fecha&order=fecha.desc&limit=120")
    dates = [row["fecha"] for row in data] if data else []
    return responseHttpOk({"dates": dates})


def _mark_status(row: dict) -> str:
    """Classify a market_marks row as 'complete', 'partial', or 'missing'."""
    NDF_TENORS = ["1", "3", "6", "12"]
    has_spot = row.get("fx_spot") is not None
    has_sofr_on = row.get("sofr_on") is not None
    ibr = row.get("ibr") or {}
    has_ibr = any(ibr.get(k) is not None for k in ["ibr_1d", "ibr_1m", "ibr_3m", "ibr_6m", "ibr_12m"])
    sofr = row.get("sofr") or {}
    has_sofr = any(sofr.get(k) is not None for k in ["1", "3", "12", "60", "120"])
    ndf = row.get("ndf") or {}
    has_ndf = any(
        (ndf.get(t) or {}).get("F_market") is not None for t in NDF_TENORS
    )
    if has_spot and has_sofr_on and has_ibr and has_sofr and has_ndf:
        all_ndf = all((ndf.get(t) or {}).get("F_market") is not None for t in NDF_TENORS)
        return "complete" if all_ndf else "partial"
    if has_spot or has_sofr_on or has_ibr or has_sofr or has_ndf:
        return "partial"
    return "missing"


@csrf_exempt
def pricing_marks(request):
    """Return market_marks rows normalized for display.

    Optional query param ?fecha=YYYY-MM-DD returns a single row:
      {"mark": {...} | null}

    Without fecha, returns up to 120 rows most-recent first:
      {"marks": [...], "count": N}

    Each row: fecha, status, fx_spot, sofr_on, ibr (JSONB), sofr (JSONB), ndf (JSONB)
    status: 'complete' | 'partial' | 'missing'
    """
    loader = _get_loader()
    fecha = request.GET.get("fecha")
    if fecha:
        data = loader._get(
            "market_marks",
            f"select=fecha,fx_spot,sofr_on,ibr,sofr,ndf&fecha=eq.{fecha}&limit=1",
        )
        row = data[0] if data else None
        if row:
            row["status"] = _mark_status(row)
        return responseHttpOk({"mark": row})
    data = loader._get(
        "market_marks",
        "select=fecha,fx_spot,sofr_on,ibr,sofr,ndf&order=fecha.desc&limit=120",
    )
    rows = data if data else []
    for row in rows:
        row["status"] = _mark_status(row)
    return responseHttpOk({"marks": rows, "count": len(rows)})


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

        fx = _fetch_historical_spot(loader, valuation_date_str)
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


# ── Full Portfolio Reprice — carry, DV01, P&L per position ──

def _ql_date_to_str(d: ql.Date) -> str:
    return date(d.year(), d.month(), d.dayOfMonth()).isoformat()


def _overnight_rates(cm) -> tuple:
    """Return (ibr_overnight, sofr_overnight) as decimals from the curves."""
    eval_date = ql.Settings.instance().evaluationDate
    next_day = eval_date + 1
    day_count = ql.Actual360()
    try:
        ibr_overnight = cm.ibr_handle.forwardRate(
            eval_date, next_day, day_count, ql.Continuous
        ).rate()
    except Exception:
        ibr_overnight = 0.0
    try:
        sofr_overnight = cm.sofr_handle.forwardRate(
            eval_date, next_day, day_count, ql.Continuous
        ).rate()
    except Exception:
        sofr_overnight = 0.0
    return ibr_overnight, sofr_overnight


def _price_ndf_full(ndf_pricer, pos: dict, cm, ibr_overnight: float, sofr_overnight: float) -> dict:
    """Price an NDF and compute carry, DV01, FX risk."""
    mat = _parse_date(pos["maturity_date"])
    direction = pos.get("direction", "buy")
    notional_usd = pos["notional_usd"]
    strike = pos["strike"]
    spot_override = pos.get("spot")

    result = ndf_pricer.price(
        notional_usd=notional_usd,
        strike=strike,
        maturity_date=mat,
        direction=direction,
        spot=spot_override,
    )
    npv_cop = result["npv_cop"]
    df_cop = result["df_cop"]
    df_usd = result["df_usd"]
    spot = result["spot"]
    sign = 1.0 if direction == "buy" else -1.0

    # Days to maturity
    eval_date = ql.Settings.instance().evaluationDate
    eval_py = date(eval_date.year(), eval_date.month(), eval_date.dayOfMonth())
    mat_py = date(mat.year(), mat.month(), mat.dayOfMonth())
    days_to_maturity = max(0, (mat_py - eval_py).days)

    # Daily carry: theta from rate differential
    # For buy-USD NDF: carry = notional * spot * (r_ibr - r_sofr) / 365
    carry_cop_daily = sign * notional_usd * spot * (ibr_overnight - sofr_overnight) / 365
    carry_usd_daily = carry_cop_daily / spot if spot else 0.0

    # DV01 IBR: bump +1bp → reprice → diff (in COP)
    cm.bump_ibr(1.0)
    r_ibr_bump = ndf_pricer.price(
        notional_usd=notional_usd, strike=strike,
        maturity_date=mat, direction=direction, spot=spot_override,
    )
    cm.bump_ibr(-1.0)
    dv01_cop = r_ibr_bump["npv_cop"] - npv_cop

    # DV01 SOFR: bump +1bp → reprice → diff (in COP)
    cm.bump_sofr(1.0)
    r_sofr_bump = ndf_pricer.price(
        notional_usd=notional_usd, strike=strike,
        maturity_date=mat, direction=direction, spot=spot_override,
    )
    cm.bump_sofr(-1.0)
    dv01_usd_curve = r_sofr_bump["npv_cop"] - npv_cop

    # FX risk: d(NPV_COP)/d(spot) = sign * N * df_usd
    fx_delta = sign * notional_usd * df_usd
    fx_exposure_usd = sign * notional_usd * df_usd

    # Days open (from trade_date if available)
    trade_date_str = pos.get("trade_date")
    if trade_date_str:
        trade_py = datetime.strptime(trade_date_str, "%Y-%m-%d").date()
        days_open = max(0, (eval_py - trade_py).days)
    else:
        days_open = 0
    accrued_cop = carry_cop_daily * days_open

    out = _serialize(result)
    out["days_to_maturity"] = days_to_maturity
    out["carry_cop_daily"] = round(carry_cop_daily, 2)
    out["carry_usd_daily"] = round(carry_usd_daily, 4)
    out["days_open"] = days_open
    out["accrued_cop"] = round(accrued_cop, 2)
    out["dv01_cop"] = round(dv01_cop, 2)
    out["dv01_usd"] = round(dv01_usd_curve, 2)
    out["dv01_total"] = round(dv01_cop + dv01_usd_curve, 2)
    out["fx_delta"] = round(fx_delta, 2)
    out["fx_exposure_usd"] = round(fx_exposure_usd, 2)
    return out


def _price_ibr_full(ibr_pricer, pos: dict, cm, ibr_overnight: float) -> dict:
    """Price an IBR swap and compute carry metrics."""
    notional = pos["notional"]
    fixed_rate = pos["fixed_rate"]
    pay_fixed = pos.get("pay_fixed", True)
    spread_bps = pos.get("spread_bps", 0.0)
    spread = spread_bps / 10000.0 if spread_bps else pos.get("spread", 0.0)

    if pos.get("maturity_date"):
        mat = _parse_date(pos["maturity_date"])
        result = ibr_pricer.price(notional, mat, fixed_rate, pay_fixed, spread)
    else:
        tenor = ql.Period(int(pos["tenor_years"]), ql.Years)
        result = ibr_pricer.price(notional, tenor, fixed_rate, pay_fixed, spread)

    # Carry: daily differential between IBR overnight and fixed rate
    sign_carry = 1.0 if pay_fixed else -1.0
    ibr_overnight_pct = ibr_overnight * 100
    carry_daily_cop = notional * (ibr_overnight - fixed_rate) * sign_carry / 365
    carry_daily_diff_bps = (ibr_overnight - fixed_rate) * 10000 * sign_carry

    # Period carry (approximate using fair rate as proxy for next-period IBR)
    fair_rate = result.get("fair_rate", ibr_overnight)
    ibr_fwd_period_pct = fair_rate * 100
    carry_period_diff_bps = (ibr_overnight - fixed_rate) * 10000 * sign_carry
    carry_period_cop = notional * (ibr_overnight - fixed_rate) * sign_carry

    # Days open (from start_date if available)
    start_date_str = pos.get("start_date")
    if start_date_str:
        eval_date_ql = ql.Settings.instance().evaluationDate
        eval_py_ibr = date(eval_date_ql.year(), eval_date_ql.month(), eval_date_ql.dayOfMonth())
        start_py_ibr = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        days_open = max(0, (eval_py_ibr - start_py_ibr).days)
    else:
        days_open = 0
    accrued_carry_cop = carry_daily_cop * days_open

    out = _serialize(result)
    out["ibr_overnight_pct"] = round(ibr_overnight_pct, 4)
    out["carry_daily_cop"] = round(carry_daily_cop, 2)
    out["carry_daily_diff_bps"] = round(carry_daily_diff_bps, 2)
    out["days_open"] = days_open
    out["accrued_carry_cop"] = round(accrued_carry_cop, 2)
    out["ibr_fwd_period_pct"] = round(ibr_fwd_period_pct, 4)
    out["carry_period_cop"] = round(carry_period_cop, 2)
    out["carry_period_diff_bps"] = round(carry_period_diff_bps, 2)
    return out


def _xccy_cashflows(cm, schedule, usd_notionals: list, cop_notionals: list,
                    cop_spread: float, usd_spread: float, eval_date_py=None) -> list:
    """Build per-period cashflow schedule for an XCCY swap."""
    day_counter = ql.Actual360()
    dates = list(schedule)
    cashflows = []
    initial_usd = usd_notionals[0] if usd_notionals else 1.0
    n_periods = len(dates) - 1
    spot = cm.fx_spot or 1.0

    if eval_date_py is None:
        ql_eval = ql.Settings.instance().evaluationDate
        eval_date_py = date(ql_eval.year(), ql_eval.month(), ql_eval.dayOfMonth())

    for i in range(1, len(dates)):
        start = dates[i - 1]
        end = dates[i]
        start_py = date(start.year(), start.month(), start.dayOfMonth())
        end_py = date(end.year(), end.month(), end.dayOfMonth())
        notional_usd_i = usd_notionals[i - 1] if i - 1 < len(usd_notionals) else 0.0
        notional_cop_i = cop_notionals[i - 1] if i - 1 < len(cop_notionals) else 0.0
        remaining_pct = notional_usd_i / initial_usd if initial_usd else 1.0

        try:
            usd_fwd = cm.sofr_handle.forwardRate(start, end, day_counter, ql.Simple).rate()
            cop_fwd = cm.ibr_handle.forwardRate(start, end, day_counter, ql.Simple).rate()
        except Exception:
            usd_fwd = 0.0
            cop_fwd = 0.0

        tau = day_counter.yearFraction(start, end)
        usd_rate = usd_fwd + usd_spread
        cop_rate = cop_fwd + cop_spread
        usd_interest = notional_usd_i * usd_rate * tau
        cop_interest = notional_cop_i * cop_rate * tau

        # Amortization principal at period end
        if i < n_periods:
            usd_principal = (usd_notionals[i - 1] - usd_notionals[i]) if i < len(usd_notionals) else 0.0
            cop_principal = (cop_notionals[i - 1] - cop_notionals[i]) if i < len(cop_notionals) else 0.0
        else:
            usd_principal = usd_notionals[-1] if usd_notionals else 0.0
            cop_principal = cop_notionals[-1] if cop_notionals else 0.0

        usd_df = cm.sofr_handle.discount(end)
        cop_df = cm.ibr_handle.discount(end)
        net_cop = cop_interest - usd_interest * spot

        # Period status and carry devengado
        days_in_period = max(1, (end_py - start_py).days)
        if end_py <= eval_date_py:
            status = 'settled'
            days_elapsed = days_in_period
        elif start_py <= eval_date_py < end_py:
            status = 'current'
            days_elapsed = (eval_date_py - start_py).days
        else:
            status = 'future'
            days_elapsed = 0

        daily_carry_cop = net_cop / days_in_period
        accrued_carry_cop = daily_carry_cop * days_elapsed
        diff_bps = (cop_rate - usd_rate) * 10000

        cashflows.append({
            "period": i,
            "start": start_py.isoformat(),
            "end": end_py.isoformat(),
            "payment_date": end_py.isoformat(),
            "notional_usd": round(notional_usd_i, 2),
            "notional_cop": round(notional_cop_i, 2),
            "remaining_pct": round(remaining_pct, 4),
            "usd_rate": round(usd_rate, 6),
            "cop_rate": round(cop_rate, 6),
            "usd_interest": round(usd_interest, 2),
            "cop_interest": round(cop_interest, 2),
            "usd_principal": round(usd_principal, 2),
            "cop_principal": round(cop_principal, 2),
            "usd_df": round(usd_df, 6),
            "cop_df": round(cop_df, 6),
            "net_cop": round(net_cop, 2),
            "status": status,
            "days_in_period": days_in_period,
            "days_elapsed": days_elapsed,
            "daily_carry_cop": round(daily_carry_cop, 2),
            "accrued_carry_cop": round(accrued_carry_cop, 2),
            "diff_bps": round(diff_bps, 2),
        })
    return cashflows


def _price_xccy_full(xccy_pricer, pos: dict, cm, ibr_overnight: float, sofr_overnight: float) -> dict:
    """Price an XCCY swap with carry, DV01, P&L, and cashflows."""
    kwargs = dict(
        notional_usd=pos["notional_usd"],
        start_date=_parse_date(pos["start_date"]),
        maturity_date=_parse_date(pos["maturity_date"]),
        pay_usd=pos.get("pay_usd", True),
        fx_initial=pos.get("fx_initial"),
        cop_spread_bps=pos.get("cop_spread_bps", 0.0),
        usd_spread_bps=pos.get("usd_spread_bps", 0.0),
        amortization_type=pos.get("amortization_type", "bullet"),
        amortization_schedule=pos.get("amortization_schedule"),
    )

    result = xccy_pricer.price(**kwargs)
    npv_cop = result["npv_cop"]
    spot = cm.fx_spot
    sign = 1.0 if pos.get("pay_usd", True) else -1.0

    # P&L from inception decomposition
    try:
        pnl = xccy_pricer.pnl_inception(**kwargs)
        pnl_rate_cop = pnl.get("pnl_rates_cop", 0.0)
        pnl_fx_cop = pnl.get("pnl_fx_cop", 0.0)
    except Exception:
        pnl_rate_cop = 0.0
        pnl_fx_cop = 0.0
    pnl_rate_usd = pnl_rate_cop / spot if spot else 0.0
    pnl_fx_usd = pnl_fx_cop / spot if spot else 0.0

    # DV01 IBR: bump +1bp
    cm.bump_ibr(1.0)
    result_ibr = xccy_pricer.price(**kwargs)
    cm.bump_ibr(-1.0)
    dv01_ibr = result_ibr["npv_cop"] - npv_cop

    # DV01 SOFR: bump +1bp
    cm.bump_sofr(1.0)
    result_sofr = xccy_pricer.price(**kwargs)
    cm.bump_sofr(-1.0)
    dv01_sofr = result_sofr["npv_cop"] - npv_cop

    # FX risk: d(NPV_COP)/d(spot) = sign * (-usd_total) * 1
    usd_total = result.get("usd_total", 0.0)
    fx_delta = sign * (-usd_total)
    fx_exposure_usd = sign * usd_total

    # Carry: overnight differential on notional COP
    notional_cop = result.get("notional_cop", 0.0)
    carry_cop = sign * notional_cop * (ibr_overnight - sofr_overnight) / 365
    carry_usd = carry_cop / spot if spot else 0.0
    carry_rate_cop_pct = ibr_overnight * 100
    carry_rate_usd_pct = sofr_overnight * 100
    carry_differential_bps = (ibr_overnight - sofr_overnight) * 10000

    # Par basis
    # Only meaningful for NEW swaps (start_date >= today). For mid-life swaps
    # the par basis under the fixed-FX notional structure encodes the full
    # IBR-SOFR rate differential (~550 bps for 10% vs 4.5%), which is not
    # comparable to the market XCCY basis (~-30 to -50 bps). Return null for
    # mid-life positions to avoid displaying a misleading metric.
    try:
        eval_date_ql = ql.Settings.instance().evaluationDate
        start_ql = _parse_date(pos["start_date"])
        is_midlife_pos = start_ql < eval_date_ql
        if is_midlife_pos:
            par_basis_bps = None
        else:
            par_basis_bps = xccy_pricer.par_xccy_basis(
                notional_usd=pos["notional_usd"],
                start_date=_parse_date(pos["start_date"]),
                maturity_date=_parse_date(pos["maturity_date"]),
                fx_initial=pos.get("fx_initial"),
                amortization_type=pos.get("amortization_type", "bullet"),
                amortization_schedule=pos.get("amortization_schedule"),
            )
    except Exception:
        par_basis_bps = None

    # Build cashflow schedule — always from original start_date so payment
    # dates and amortization factors match the pricer. For mid-life swaps,
    # filter out past periods for display but keep the full schedule structure.
    carry_accrued_cop = 0.0
    days_open = 0
    try:
        start_ql = _parse_date(pos["start_date"])
        mat_ql = _parse_date(pos["maturity_date"])
        eval_date = ql.Settings.instance().evaluationDate
        eval_date_py = date(eval_date.year(), eval_date.month(), eval_date.dayOfMonth())
        is_midlife = start_ql < eval_date
        cop_cal = cm.ibr_index.fixingCalendar()
        usd_cal = cm.sofr_index.fixingCalendar()
        joint_cal = ql.JointCalendar(cop_cal, usd_cal)
        schedule = ql.Schedule(
            start_ql, mat_ql,
            ql.Period(3, ql.Months),
            joint_cal,
            ql.Following, ql.Following,
            ql.DateGeneration.Forward, False,
        )
        fx = pos.get("fx_initial") or spot
        usd_notionals = build_amortization_schedule(
            schedule, pos["notional_usd"],
            pos.get("amortization_type", "bullet"),
            pos.get("amortization_schedule"),
        )
        cop_notionals = [n * fx for n in usd_notionals]
        cop_spread = (pos.get("cop_spread_bps", 0.0)) / 10000.0
        usd_spread = (pos.get("usd_spread_bps", 0.0)) / 10000.0
        if is_midlife:
            # Filter to future periods only for cashflow display
            ibr_ref = cm.ibr_handle.currentLink().referenceDate()
            sofr_ref = cm.sofr_handle.currentLink().referenceDate()
            curve_floor = max(eval_date, ibr_ref, sofr_ref)
            full_dates = list(schedule)
            first_future = 0
            for idx in range(1, len(full_dates)):
                if full_dates[idx] > curve_floor:
                    first_future = idx - 1
                    break
            future_dates = list(full_dates[first_future:])
            future_usd = list(usd_notionals[first_future:])
            future_cop = list(cop_notionals[first_future:])
            if future_dates[0] < curve_floor:
                future_dates[0] = curve_floor
            # Build a filtered schedule for cashflow display
            future_schedule = ql.Schedule(future_dates, joint_cal,
                                          ql.Following)
            cashflows = _xccy_cashflows(cm, future_schedule, future_usd, future_cop, cop_spread, usd_spread, eval_date_py)
        else:
            cashflows = _xccy_cashflows(cm, schedule, usd_notionals, cop_notionals, cop_spread, usd_spread, eval_date_py)
        n_periods = len(cashflows)
        carry_accrued_cop = sum(cf["accrued_carry_cop"] for cf in cashflows if cf.get("status") == "current")
        start_py_pos = datetime.strptime(pos["start_date"], "%Y-%m-%d").date()
        days_open = max(0, (eval_date_py - start_py_pos).days)
    except Exception:
        cashflows = []
        n_periods = 0

    out = _serialize(result)
    out["pnl_rate_cop"] = round(pnl_rate_cop, 2)
    out["pnl_rate_usd"] = round(pnl_rate_usd, 4)
    out["pnl_fx_cop"] = round(pnl_fx_cop, 2)
    out["pnl_fx_usd"] = round(pnl_fx_usd, 4)
    out["usd_principal_pv"] = result.get("usd_notional_exchange_pv", 0.0)
    out["cop_principal_pv"] = result.get("cop_notional_exchange_pv", 0.0)
    out["carry_cop"] = round(carry_cop, 2)
    out["carry_usd"] = round(carry_usd, 4)
    out["carry_rate_cop_pct"] = round(carry_rate_cop_pct, 4)
    out["carry_rate_usd_pct"] = round(carry_rate_usd_pct, 4)
    out["carry_differential_bps"] = round(carry_differential_bps, 2)
    out["dv01_ibr"] = round(dv01_ibr, 2)
    out["dv01_sofr"] = round(dv01_sofr, 2)
    out["dv01_total"] = round(dv01_ibr + dv01_sofr, 2)
    out["fx_delta"] = round(fx_delta, 2)
    out["fx_exposure_usd"] = round(fx_exposure_usd, 2)
    out["par_basis_bps"] = round(par_basis_bps, 4) if par_basis_bps is not None else None
    out["carry_accrued_cop"] = round(carry_accrued_cop, 2)
    out["days_open"] = days_open
    out["n_periods"] = n_periods
    out["cashflows"] = cashflows
    return out


@csrf_exempt
def pricing_portfolio_reprice(request):
    """Full portfolio reprice: carry, DV01, P&L, cashflows per position.

    Endpoint: POST /pricing/portfolio/reprice
    Request keys: xccy_positions, ndf_positions, ibr_swap_positions, valuation_date
    Each position uses 'id' (not 'position_id') for identification.

    Response keys: xccy_results, ndf_results, ibr_swap_results, summary
    """
    cm = _get_cm()
    loader = _get_loader()
    body = json.loads(request.body) if request.body else {}

    valuation_date_str = body.get("valuation_date")
    original_eval_date = None
    original_fx_spot = None
    curves_rebuilt_for_history = False

    if valuation_date_str is not None:
        original_eval_date = ql.Settings.instance().evaluationDate
        original_fx_spot = cm.fx_spot

        hist_date = _parse_date(valuation_date_str)
        cm.set_valuation_date(hist_date)

        ibr_data = loader.fetch_ibr_quotes(target_date=valuation_date_str)
        if ibr_data:
            cm.build_ibr_curve(ibr_data)

        sofr_data = loader.fetch_sofr_curve(target_date=valuation_date_str)
        if not sofr_data.empty:
            cm.build_sofr_curve(sofr_data)

        fx = _fetch_historical_spot(loader, valuation_date_str)
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

        ibr_overnight, sofr_overnight = _overnight_rates(cm)

        xccy_results = []
        ndf_results = []
        ibr_results = []

        for pos in body.get("ndf_positions", []):
            pos_id = pos.get("id") or pos.get("position_id")
            try:
                row = _price_ndf_full(ndf_pricer, pos, cm, ibr_overnight, sofr_overnight)
                row["id"] = pos_id
                ndf_results.append(row)
            except Exception as exc:
                ndf_results.append({
                    "id": pos_id, "error": str(exc),
                    "npv_cop": 0.0, "npv_usd": 0.0,
                })

        for pos in body.get("ibr_swap_positions", []):
            pos_id = pos.get("id") or pos.get("position_id")
            try:
                row = _price_ibr_full(ibr_pricer, pos, cm, ibr_overnight)
                row["id"] = pos_id
                ibr_results.append(row)
            except Exception as exc:
                ibr_results.append({
                    "id": pos_id, "error": str(exc),
                    "npv": 0.0,
                })

        for pos in body.get("xccy_positions", []):
            pos_id = pos.get("id") or pos.get("position_id")
            try:
                row = _price_xccy_full(xccy_pricer, pos, cm, ibr_overnight, sofr_overnight)
                row["id"] = pos_id
                xccy_results.append(row)
            except Exception as exc:
                xccy_results.append({
                    "id": pos_id, "error": str(exc),
                    "npv_cop": 0.0, "npv_usd": 0.0, "cashflows": [],
                })

        spot = cm.fx_spot or 1.0
        total_npv_cop = (
            sum(r.get("npv_cop", 0.0) for r in xccy_results if not r.get("error"))
            + sum(r.get("npv_cop", 0.0) for r in ndf_results if not r.get("error"))
            + sum(r.get("npv", 0.0) for r in ibr_results if not r.get("error"))
        )
        total_carry_cop = (
            sum(r.get("carry_cop", 0.0) for r in xccy_results if not r.get("error"))
            + sum(r.get("carry_cop_daily", 0.0) for r in ndf_results if not r.get("error"))
            + sum(r.get("carry_daily_cop", 0.0) for r in ibr_results if not r.get("error"))
        )
        total_pnl_rate_cop = sum(r.get("pnl_rate_cop", 0.0) for r in xccy_results if not r.get("error"))
        total_pnl_fx_cop = sum(r.get("pnl_fx_cop", 0.0) for r in xccy_results if not r.get("error"))

        return responseHttpOk({
            "xccy_results": xccy_results,
            "ndf_results": ndf_results,
            "ibr_swap_results": ibr_results,
            "summary": {
                "total_npv_cop": round(total_npv_cop, 2),
                "total_npv_usd": round(total_npv_cop / spot, 2),
                "total_carry_cop": round(total_carry_cop, 2),
                "total_carry_usd": round(total_carry_cop / spot, 2),
                "total_pnl_rate_cop": round(total_pnl_rate_cop, 2),
                "total_pnl_fx_cop": round(total_pnl_fx_cop, 2),
                "fx_spot": round(spot, 2),
            },
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
