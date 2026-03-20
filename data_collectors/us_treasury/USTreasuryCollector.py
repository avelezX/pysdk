"""
Collector for US Treasury yield curve data from treasury.gov XML feed.

Sources:
  - Nominal UST: daily_treasury_yield_curve (1Mo..30Yr) since 1990
  - TIPS real:   daily_treasury_real_yield_curve (5Yr..30Yr) since 2003

API docs: https://home.treasury.gov/treasury-daily-interest-rate-xml-feed
"""

import requests
import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime, date


BASE_URL = "https://home.treasury.gov/resource-center/data-chart-center/interest-rates/pages/xml"

NOMINAL_FIELDS = {
    "d:BC_1MONTH": 1,
    "d:BC_2MONTH": 2,
    "d:BC_3MONTH": 3,
    "d:BC_4MONTH": 4,
    "d:BC_6MONTH": 6,
    "d:BC_1YEAR": 12,
    "d:BC_2YEAR": 24,
    "d:BC_3YEAR": 36,
    "d:BC_5YEAR": 60,
    "d:BC_7YEAR": 84,
    "d:BC_10YEAR": 120,
    "d:BC_20YEAR": 240,
    "d:BC_30YEAR": 360,
}

TIPS_FIELDS = {
    "d:TC_5YEAR": 60,
    "d:TC_7YEAR": 84,
    "d:TC_10YEAR": 120,
    "d:TC_20YEAR": 240,
    "d:TC_30YEAR": 360,
}

NS = {
    "d": "http://schemas.microsoft.com/ado/2007/08/dataservices",
    "m": "http://schemas.microsoft.com/ado/2007/08/dataservices/metadata",
    "a": "http://www.w3.org/2005/Atom",
}


def _fetch_xml(data_type: str, year: int) -> str:
    url = f"{BASE_URL}?data={data_type}&field_tdr_date_value={year}"
    resp = requests.get(url, timeout=30)
    resp.raise_for_status()
    return resp.text


def _parse_yield_entries(xml_text: str, field_map: dict, curve_type: str) -> list:
    root = ET.fromstring(xml_text)
    rows = []

    for entry in root.findall(".//a:entry", NS):
        content = entry.find("a:content", NS)
        if content is None:
            continue
        props = content.find("m:properties", NS)
        if props is None:
            continue

        date_el = props.find("d:NEW_DATE", NS)
        if date_el is None or date_el.text is None:
            continue

        try:
            dt = datetime.fromisoformat(date_el.text.replace("Z", "")).date()
        except ValueError:
            continue

        fecha = dt.isoformat()

        for xml_field, tenor_months in field_map.items():
            el = props.find(xml_field, NS)
            if el is not None and el.text is not None and el.text.strip():
                try:
                    yield_val = float(el.text)
                except ValueError:
                    continue
                rows.append({
                    "fecha": fecha,
                    "tenor_months": tenor_months,
                    "yield_value": yield_val,
                    "curve_type": curve_type,
                })

    return rows


def fetch_ust_nominal(year=None):
    if year is None:
        year = date.today().year
    xml_text = _fetch_xml("daily_treasury_yield_curve", year)
    rows = _parse_yield_entries(xml_text, NOMINAL_FIELDS, "NOMINAL")
    if not rows:
        return pd.DataFrame(columns=["fecha", "tenor_months", "yield_value", "curve_type"])
    return pd.DataFrame(rows)


def fetch_ust_tips(year=None):
    if year is None:
        year = date.today().year
    xml_text = _fetch_xml("daily_treasury_real_yield_curve", year)
    rows = _parse_yield_entries(xml_text, TIPS_FIELDS, "TIPS")
    if not rows:
        return pd.DataFrame(columns=["fecha", "tenor_months", "yield_value", "curve_type"])
    return pd.DataFrame(rows)


def fetch_all_curves(year=None):
    nominal = fetch_ust_nominal(year)
    tips = fetch_ust_tips(year)
    return pd.concat([nominal, tips], ignore_index=True)
