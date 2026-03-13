"""
Runner: Collect USD/COP forward rates from FXEmpire.
Stores in xerenity.cop_fwd_points table.
Appends one snapshot per day (idempotent — skips if today already collected).

Schedule: Daily at 21:00 UTC (after NY close)
Alerts:   Send Teams notification after each successful storage.
          Configure a Teams incoming webhook and set TEAMS_WEBHOOK_URL env var.
"""

import json
import os
import requests
from datetime import date
from src.collectors.fxempire_cop import fetch_cop_forwards

# ── Supabase REST connection ──
SUPABASE_URL = os.getenv("XTY_URL")
SUPABASE_KEY = os.getenv("XTY_TOKEN")
COLLECTOR_BEARER = os.getenv("COLLECTOR_BEARER")

TABLE = "cop_fwd_points"
TEAMS_WEBHOOK_URL = os.environ.get("TEAMS_WEBHOOK_URL", "")

db = requests.Session()
db.headers.update({
    'apikey': SUPABASE_KEY,
    'Authorization': f'Bearer {COLLECTOR_BEARER}',
    'Content-Type': 'application/json',
    'Accept-Profile': 'xerenity',
    'Content-Profile': 'xerenity',
    'Prefer': 'return=minimal',
})


def get_last_date() -> str | None:
    """Get the last date stored in the table."""
    resp = db.get(
        f'{SUPABASE_URL}/rest/v1/{TABLE}?select=fecha&order=fecha.desc&limit=1'
    )
    if resp.status_code == 200:
        data = resp.json()
        if data and len(data) > 0:
            return data[0]['fecha']
    return None


def insert_rows(rows: list[dict]) -> int:
    """Insert rows in batches of 200. Returns count inserted."""
    inserted = 0
    batch_size = 200
    for i in range(0, len(rows), batch_size):
        batch = rows[i:i + batch_size]
        resp = db.post(
            f'{SUPABASE_URL}/rest/v1/{TABLE}',
            data=json.dumps(batch),
        )
        if resp.status_code in (200, 201):
            inserted += len(batch)
        elif resp.status_code == 409 or 'duplicate' in resp.text.lower():
            print(f"  Batch {i // batch_size + 1}: duplicates skipped")
        else:
            print(f"  Batch {i // batch_size + 1} error: {resp.status_code} {resp.text[:200]}")
    return inserted


def notify_teams(message: str):
    """Send a notification to Microsoft Teams via incoming webhook."""
    if not TEAMS_WEBHOOK_URL:
        print("  Teams webhook not configured, skipping notification.")
        return
    payload = {"text": message}
    try:
        resp = requests.post(TEAMS_WEBHOOK_URL, json=payload, timeout=10)
        if resp.status_code in (200, 202):
            print("  Teams notification sent.")
        else:
            print(f"  Teams notification failed: {resp.status_code}")
    except requests.RequestException as e:
        print(f"  Teams notification error: {e}")


def main():
    today = date.today()
    print(f"COP Forward Points Collector (FXEmpire) — {today}")

    last_date = get_last_date()
    print(f"  Last stored date: {last_date or 'none (first load)'}")

    if last_date == today.isoformat():
        print("  Already collected today, skipping.")
        return

    df = fetch_cop_forwards()

    if df.empty:
        msg = f"⚠️ COP Fwd Points ({today}): No data fetched (weekend/holiday or source unavailable)"
        print(f"  {msg}")
        notify_teams(msg)
        return

    print(f"  Fetched {len(df)} data points")
    print(f"  Tenors: {', '.join(df['tenor'].tolist())}")

    rows = df.to_dict(orient='records')
    inserted = insert_rows(rows)
    print(f"  Inserted {inserted} rows")

    msg = (
        f"✅ COP Fwd Points ({today}): {inserted} rows stored.\n"
        f"Tenors: {', '.join(df['tenor'].tolist())}  |  "
        f"Mid 1M: {df.loc[df['tenor'] == '1M', 'mid'].values[0] if '1M' in df['tenor'].values else 'N/A'}  |  "
        f"Mid 1Y: {df.loc[df['tenor'] == '1Y', 'mid'].values[0] if '1Y' in df['tenor'].values else 'N/A'}"
    )
    notify_teams(msg)
    print(f"\nDone!")


if __name__ == "__main__":
    main()
