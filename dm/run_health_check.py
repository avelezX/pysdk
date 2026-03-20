import os
import sys
from data_collectors.health.HealthChecker import HealthChecker
from data_collectors.health.TeamsNotifier import TeamsNotifier

# Fix Windows console encoding for emoji output
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Same credentials used by all collectors (see db_connection/supabase/Client.py)
SUPABASE_URL = 'https://tvpehjbqxpiswkqszwwv.supabase.co'
SUPABASE_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InR2cGVoamJxeHBpc3drcXN6d3d2Iiwicm9sZSI6ImFub24iLCJpYXQiOjE2OTY0NTEzODksImV4cCI6MjAxMjAyNzM4OX0.LZW0i9HU81lCdyjAdqjwwF4hkuSVtsJsSDQh7blzozw'
COLLECTOR_BEARER = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhdWQiOiAiY29sbGVjdG9yIiwiZXhwIjogMTg0NzI4ODUyMCwiaWF0IjogMTczNjk1NTc1MiwiaXNzIjogImh0dHBzOi8vdHZwZWhqYnF4cGlzd2txc3p3d3Yuc3VwYWJhc2UuY28iLCJlbWFpbCI6ICJzdmVsZXpzYWZmb25AZ21haWwuY29tIiwicm9sZSI6ICJjb2xsZWN0b3IifQ.5HX_n8SsXN4xPslndvyyYubdlDLFg2_uAUIwinEi-eU'
TEAMS_WEBHOOK_URL = os.environ.get('TEAMS_WEBHOOK_URL', '')

checker = HealthChecker(
    supabase_url=SUPABASE_URL,
    supabase_key=SUPABASE_KEY,
    collector_bearer=COLLECTOR_BEARER
)

print('Running health checks...')
results = checker.check_all()

# Print results to console
for r in results:
    status_icon = {'ok': '✅', 'warning': '⚠️', 'stale': '❌', 'error': '🔴'}.get(r['status'], '?')
    age = f"{r['age_hours']}h" if r['age_hours'] is not None else 'N/A'
    print(f"  {status_icon} {r['label']:30s} last={r['latest_date']:12s} age={age:>8s} max={r['max_age_hours']}h")

ok = sum(1 for r in results if r['status'] == 'ok')
print(f'\nSummary: {ok}/{len(results)} OK')

# Send to Teams
if TEAMS_WEBHOOK_URL:
    notifier = TeamsNotifier(webhook_url=TEAMS_WEBHOOK_URL)
    notifier.send_health_report(checks=results)
else:
    print('TEAMS_WEBHOOK_URL not set, skipping notification')
