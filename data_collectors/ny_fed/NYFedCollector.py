"""
Collector for US reference rates from the NY Fed Markets API.

Rates collected:
  - SOFR (Secured Overnight Financing Rate)
  - SOFR Averages & Index (30d, 90d, 180d compounded averages)
  - EFFR (Effective Federal Funds Rate) + target range
  - OBFR (Overnight Bank Funding Rate)

API docs: https://markets.newyorkfed.org/static/docs/markets-api.html
No API key required.
"""

import requests
import pandas as pd


BASE_URL = "https://markets.newyorkfed.org/api/rates"


def _fetch_json(endpoint: str) -> dict:
    url = f"{BASE_URL}/{endpoint}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.json()


def fetch_sofr(start_date=None, end_date=None):
    if start_date and end_date:
        data = _fetch_json(f"secured/sofr/search.json?startDate={start_date}&endDate={end_date}")
    else:
        data = _fetch_json("secured/sofr/last/30.json")

    rows = []
    for entry in data.get("refRates", []):
        rows.append({
            "fecha": entry["effectiveDate"],
            "rate_type": "SOFR",
            "rate": entry.get("percentRate"),
            "volume_billions": entry.get("volumeInBillions"),
            "target_from": None,
            "target_to": None,
        })
    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["fecha", "rate_type", "rate", "volume_billions", "target_from", "target_to"]
    )


def fetch_sofr_averages():
    data = _fetch_json("all/latest.json")
    rows = []
    for entry in data.get("refRates", []):
        if entry.get("type") != "SOFRAI":
            continue
        fecha = entry["effectiveDate"]
        avg30 = entry.get("average30day")
        avg90 = entry.get("average90day")
        avg180 = entry.get("average180day")

        if avg30 is not None:
            rows.append({"fecha": fecha, "rate_type": "SOFR_AVG_30D", "rate": avg30,
                         "volume_billions": None, "target_from": None, "target_to": None})
        if avg90 is not None:
            rows.append({"fecha": fecha, "rate_type": "SOFR_AVG_90D", "rate": avg90,
                         "volume_billions": None, "target_from": None, "target_to": None})
        if avg180 is not None:
            rows.append({"fecha": fecha, "rate_type": "SOFR_AVG_180D", "rate": avg180,
                         "volume_billions": None, "target_from": None, "target_to": None})

    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["fecha", "rate_type", "rate", "volume_billions", "target_from", "target_to"]
    )


def fetch_effr(start_date=None, end_date=None):
    if start_date and end_date:
        data = _fetch_json(f"unsecured/effr/search.json?startDate={start_date}&endDate={end_date}")
    else:
        data = _fetch_json("unsecured/effr/last/30.json")

    rows = []
    for entry in data.get("refRates", []):
        rows.append({
            "fecha": entry["effectiveDate"],
            "rate_type": "EFFR",
            "rate": entry.get("percentRate"),
            "volume_billions": entry.get("volumeInBillions"),
            "target_from": entry.get("targetRateFrom"),
            "target_to": entry.get("targetRateTo"),
        })
    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["fecha", "rate_type", "rate", "volume_billions", "target_from", "target_to"]
    )


def fetch_obfr(start_date=None, end_date=None):
    if start_date and end_date:
        data = _fetch_json(f"unsecured/obfr/search.json?startDate={start_date}&endDate={end_date}")
    else:
        data = _fetch_json("unsecured/obfr/last/30.json")

    rows = []
    for entry in data.get("refRates", []):
        rows.append({
            "fecha": entry["effectiveDate"],
            "rate_type": "OBFR",
            "rate": entry.get("percentRate"),
            "volume_billions": entry.get("volumeInBillions"),
            "target_from": None,
            "target_to": None,
        })
    return pd.DataFrame(rows) if rows else pd.DataFrame(
        columns=["fecha", "rate_type", "rate", "volume_billions", "target_from", "target_to"]
    )
