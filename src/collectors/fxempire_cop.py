"""
Collector for USD/COP forward rates from FXEmpire.

Source: FXEmpire USD/COP Forward Rates page.
  - URL: https://www.fxempire.com/currencies/usd-cop/forward-rates
  - Tenors: Spot Next, 1M, 2M, 3M, 6M, 9M, 1Y
  - Data: Bid, Ask, Mid, Forward Points, Spot Rate
  - Updated intraday on business days
  - Free, no API key required.
"""

import requests
import pandas as pd
from datetime import date
from bs4 import BeautifulSoup


PAGE_URL = "https://www.fxempire.com/currencies/usd-cop/forward-rates"

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/131.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

TENOR_MAP = {
    "spot next": ("SN", 0),
    "one week": ("1W", 0),
    "two weeks": ("2W", 0),
    "one month": ("1M", 1),
    "two months": ("2M", 2),
    "three months": ("3M", 3),
    "four months": ("4M", 4),
    "five months": ("5M", 5),
    "six months": ("6M", 6),
    "seven months": ("7M", 7),
    "eight months": ("8M", 8),
    "nine months": ("9M", 9),
    "ten months": ("10M", 10),
    "eleven months": ("11M", 11),
    "one year": ("1Y", 12),
    "two years": ("2Y", 24),
    "three years": ("3Y", 36),
    "five years": ("5Y", 60),
    "seven years": ("7Y", 84),
    "ten years": ("10Y", 120),
}

EMPTY_COLS = ["fecha", "tenor", "tenor_months", "bid", "ask", "mid", "fwd_points"]


def _parse_number(text: str) -> float | None:
    """Parse a number string like '3,651.73' or '206,700.00' into a float."""
    if not text:
        return None
    cleaned = text.strip().replace(",", "")
    try:
        return float(cleaned)
    except (ValueError, TypeError):
        return None


def _fetch_page() -> str | None:
    """Fetch the FXEmpire forward rates page HTML."""
    try:
        resp = requests.get(PAGE_URL, headers=HEADERS, timeout=30)
        if resp.status_code == 200:
            return resp.text
    except requests.RequestException:
        pass
    return None


def _parse_forward_rates(html: str) -> list[dict]:
    """Parse the forward rates table from FXEmpire HTML."""
    soup = BeautifulSoup(html, "lxml")
    rows = []

    # Find the forward rates table — look for tables with tenor keywords
    tables = soup.find_all("table")
    target_table = None
    for table in tables:
        text = table.get_text().lower()
        if ("month" in text or "year" in text) and ("bid" in text or "ask" in text):
            target_table = table
            break

    if not target_table:
        return rows

    tbody = target_table.find("tbody") or target_table

    for tr in tbody.find_all("tr"):
        cells = tr.find_all(["td", "th"])
        if len(cells) < 4:
            continue

        tenor_text = cells[0].get_text().strip().lower()
        if tenor_text not in TENOR_MAP:
            continue

        label, months = TENOR_MAP[tenor_text]
        bid = _parse_number(cells[1].get_text())
        ask = _parse_number(cells[2].get_text())
        mid = _parse_number(cells[3].get_text()) if len(cells) > 3 else None
        fwd_points = _parse_number(cells[4].get_text()) if len(cells) > 4 else None

        if bid is None and ask is None:
            continue

        rows.append({
            "fecha": date.today().isoformat(),
            "tenor": label,
            "tenor_months": months,
            "bid": bid,
            "ask": ask,
            "mid": mid,
            "fwd_points": fwd_points,
        })

    return rows


def fetch_cop_forwards() -> pd.DataFrame:
    """
    Fetch current USD/COP forward rates from FXEmpire.

    Returns DataFrame with columns:
      fecha, tenor, tenor_months, bid, ask, mid, fwd_points
    """
    html = _fetch_page()
    if html is None:
        return pd.DataFrame(columns=EMPTY_COLS)

    rows = _parse_forward_rates(html)
    if not rows:
        return pd.DataFrame(columns=EMPTY_COLS)

    return pd.DataFrame(rows).sort_values("tenor_months").reset_index(drop=True)
