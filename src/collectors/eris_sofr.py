"""
Collector for SOFR OIS par swap rates from Eris Futures (CME Group).

Source: Eris Futures daily par coupon curve CSV files.
  - URL pattern: http://files.erisfutures.com/ftp/Eris_{YYYYMMDD}_EOD_ParCouponCurve_SOFR.csv
  - Archive: http://files.erisfutures.com/ftp/archives/{YYYY}/{MM}/
  - 24 tenors from 1D to 50Y
  - Published daily ~15:40 ET on business days
  - Free, no API key required.

Docs: https://www.erisfutures.com/sofrdata
"""

import requests
import pandas as pd
from datetime import date, timedelta
from io import StringIO


BASE_URL = "http://files.erisfutures.com/ftp"
ARCHIVE_URL = f"{BASE_URL}/archives"

# Map Eris symbols to tenor in months (skip sub-monthly tenors)
SYMBOL_TO_MONTHS = {
    "SOFR1M": 1,
    "SOFR3M": 3,
    "SOFR6M": 6,
    "SOFR9M": 9,
    "SOFR12M": 12,
    "SOFR18M": 18,
    "SOFR2Y": 24,
    "SOFR3Y": 36,
    "SOFR4Y": 48,
    "SOFR5Y": 60,
    "SOFR6Y": 72,
    "SOFR7Y": 84,
    "SOFR8Y": 96,
    "SOFR9Y": 108,
    "SOFR10Y": 120,
    "SOFR12Y": 144,
    "SOFR15Y": 180,
    "SOFR20Y": 240,
    "SOFR25Y": 300,
    "SOFR30Y": 360,
    "SOFR40Y": 480,
    "SOFR50Y": 600,
}


def _build_url(dt: date) -> str:
    """Build Eris CSV URL for a given date."""
    return f"{BASE_URL}/Eris_{dt.strftime('%Y%m%d')}_EOD_ParCouponCurve_SOFR.csv"


def _build_archive_url(dt: date) -> str:
    """Build Eris archive CSV URL for a given date."""
    return (
        f"{ARCHIVE_URL}/{dt.strftime('%Y')}/{dt.strftime('%m')}/"
        f"Eris_{dt.strftime('%Y%m%d')}_EOD_ParCouponCurve_SOFR.csv"
    )


def _fetch_csv(dt: date) -> pd.DataFrame | None:
    """Try to fetch the Eris CSV for a specific date. Returns None if not found."""
    for url_builder in [_build_url, _build_archive_url]:
        url = url_builder(dt)
        try:
            resp = requests.get(url, timeout=30)
            if resp.status_code == 200 and len(resp.text) > 50:
                return pd.read_csv(StringIO(resp.text))
        except requests.RequestException:
            pass
    return None


def fetch_sofr_curve(target_date: date | None = None) -> pd.DataFrame:
    """
    Fetch SOFR par swap curve for a specific date.
    If the exact date has no data (weekend/holiday), tries the previous 5 business days.

    Returns DataFrame with columns: fecha, tenor_months, swap_rate
    """
    if target_date is None:
        target_date = date.today()

    empty = pd.DataFrame(columns=["fecha", "tenor_months", "swap_rate"])

    # Try target date and previous days (in case of weekends/holidays)
    for offset in range(6):
        dt = target_date - timedelta(days=offset)
        raw = _fetch_csv(dt)
        if raw is not None:
            return _parse_curve(raw)

    return empty


def _parse_curve(raw: pd.DataFrame) -> pd.DataFrame:
    """Parse Eris CSV into standardized format."""
    rows = []
    for _, row in raw.iterrows():
        symbol = str(row.get("Symbol", "")).strip()
        if symbol not in SYMBOL_TO_MONTHS:
            continue

        fair_coupon = row.get("FairCoupon (%)")
        if fair_coupon is None:
            # Try alternate column name
            fair_coupon = row.get("FairCoupon(%)")
        if fair_coupon is None:
            continue

        try:
            rate = float(fair_coupon)
        except (ValueError, TypeError):
            continue

        eval_date = str(row.get("EvaluationDate", "")).strip()
        # Format could be YYYY-MM-DD or MM/DD/YYYY
        if "/" in eval_date:
            parts = eval_date.split("/")
            if len(parts) == 3:
                eval_date = f"{parts[2]}-{parts[0].zfill(2)}-{parts[1].zfill(2)}"

        rows.append({
            "fecha": eval_date,
            "tenor_months": SYMBOL_TO_MONTHS[symbol],
            "swap_rate": rate,
        })

    if not rows:
        return pd.DataFrame(columns=["fecha", "tenor_months", "swap_rate"])
    return pd.DataFrame(rows).sort_values("tenor_months").reset_index(drop=True)


def fetch_sofr_curve_range(start_date: date, end_date: date | None = None) -> pd.DataFrame:
    """
    Fetch SOFR par swap curves for a date range.
    Skips weekends automatically.

    Returns DataFrame with columns: fecha, tenor_months, swap_rate
    """
    if end_date is None:
        end_date = date.today()

    all_frames = []
    current = start_date
    while current <= end_date:
        # Skip weekends
        if current.weekday() < 5:
            raw = _fetch_csv(current)
            if raw is not None:
                df = _parse_curve(raw)
                if not df.empty:
                    all_frames.append(df)
        current += timedelta(days=1)

    if not all_frames:
        return pd.DataFrame(columns=["fecha", "tenor_months", "swap_rate"])
    return pd.concat(all_frames, ignore_index=True)
