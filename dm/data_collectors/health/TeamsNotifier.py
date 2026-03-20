import requests
from datetime import datetime


class TeamsNotifier:
    """
    Sends health check reports to Microsoft Teams via incoming webhook
    using Adaptive Cards for rich formatting.
    """

    def __init__(self, webhook_url):
        self.webhook_url = webhook_url

    def send_health_report(self, checks):
        """Format checks into an Adaptive Card and POST to Teams webhook."""
        ok_count = sum(1 for c in checks if c['status'] == 'ok')
        warning_count = sum(1 for c in checks if c['status'] == 'warning')
        stale_count = sum(1 for c in checks if c['status'] == 'stale')
        error_count = sum(1 for c in checks if c['status'] == 'error')
        total = len(checks)

        today = datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')

        status_emoji = {
            'ok': '✅',
            'warning': '⚠️',
            'stale': '❌',
            'error': '🔴'
        }

        # Build summary line
        summary_parts = [f'{ok_count}/{total} OK']
        if warning_count > 0:
            summary_parts.append(f'{warning_count} ⚠️')
        if stale_count > 0:
            summary_parts.append(f'{stale_count} ❌')
        if error_count > 0:
            summary_parts.append(f'{error_count} 🔴')
        summary = ' | '.join(summary_parts)

        # Overall color
        if stale_count > 0 or error_count > 0:
            accent = 'attention'
        elif warning_count > 0:
            accent = 'warning'
        else:
            accent = 'good'

        # Build card body
        body = [
            {
                "type": "TextBlock",
                "size": "large",
                "weight": "bolder",
                "text": f"Xerenity Health Check"
            },
            {
                "type": "TextBlock",
                "text": f"{today} — {summary}",
                "wrap": True,
                "spacing": "none"
            }
        ]

        # Problems section (stale + error + warning)
        problems = [c for c in checks if c['status'] in ('stale', 'error', 'warning')]
        if problems:
            body.append({
                "type": "TextBlock",
                "text": "Requiere atención:",
                "weight": "bolder",
                "spacing": "medium"
            })

            problem_facts = []
            for c in problems:
                emoji = status_emoji[c['status']]
                age_str = f"{c['age_hours']}h" if c['age_hours'] is not None else 'sin datos'
                problem_facts.append({
                    "title": f"{emoji} {c['label']}",
                    "value": f"Último: {c['latest_date']} (edad: {age_str}, max: {c['max_age_hours']}h)"
                })

            body.append({
                "type": "FactSet",
                "facts": problem_facts
            })

        # OK section (collapsed summary)
        ok_items = [c for c in checks if c['status'] == 'ok']
        if ok_items:
            ok_labels = ', '.join(c['label'] for c in ok_items)
            body.append({
                "type": "TextBlock",
                "text": f"✅ Al día ({ok_count}): {ok_labels}",
                "wrap": True,
                "spacing": "medium",
                "isSubtle": True,
                "size": "small"
            })

        # Build the Adaptive Card
        card = {
            "type": "message",
            "attachments": [
                {
                    "contentType": "application/vnd.microsoft.card.adaptive",
                    "contentUrl": None,
                    "content": {
                        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
                        "type": "AdaptiveCard",
                        "version": "1.4",
                        "body": body
                    }
                }
            ]
        }

        # POST to Teams webhook
        resp = requests.post(
            self.webhook_url,
            json=card,
            headers={'Content-Type': 'application/json'},
            timeout=15
        )

        if resp.status_code in (200, 202):
            print(f'Teams notification sent: {summary}')
        else:
            print(f'Teams webhook failed: {resp.status_code} {resp.text[:200]}')
            resp.raise_for_status()
