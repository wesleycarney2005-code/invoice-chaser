"""Send chase emails via Resend and run the daily check."""
import os
import logging
import resend
import db

log = logging.getLogger(__name__)
resend.api_key = os.environ.get("RESEND_API_KEY", "")

_CURRENCY_SYM = {"GBP": "£", "USD": "$", "EUR": "€"}

TEMPLATES = {
    1: {
        "subject": "Payment reminder — invoice {ref}",
        "tone": "friendly",
        "body": """Hi {client},

Just a friendly reminder that invoice {ref} for {sym}{amount} was due on {due_date}.

{description_line}

If you've already sent payment, please ignore this — and thank you!

If not, could you let me know when I can expect it? I'm happy to help if there's anything holding things up.

{user_name}
""",
    },
    3: {
        "subject": "Following up — invoice {ref} now {days} days overdue",
        "tone": "firm",
        "body": """Hi {client},

I'm following up on invoice {ref} for {sym}{amount}, which was due on {due_date} and is now {days} days overdue.

{description_line}

Could you please arrange payment at your earliest convenience? If there's an issue I'm not aware of, I'd appreciate a quick reply so we can sort it out.

{user_name}
""",
    },
    7: {
        "subject": "Final notice — invoice {ref} ({days} days overdue)",
        "tone": "formal",
        "body": """Hi {client},

This is a formal notice that invoice {ref} for {sym}{amount} remains unpaid, now {days} days past its due date of {due_date}.

{description_line}

If payment is not received within 7 days, I may need to pursue this through a debt recovery service or small claims court.

I'd much prefer to resolve this directly — please reply or make payment immediately.

{user_name}
""",
    },
}


def _html_wrap(plain: str, subject: str) -> str:
    lines = plain.strip().split("\n")
    paras = "".join(
        f'<p style="font-size:.93rem;line-height:1.75;margin:0 0 14px;color:#1a1612;">{l}</p>'
        if l.strip() else '<p style="margin:8px 0;"></p>'
        for l in lines
    )
    return f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8"></head>
<body style="background:#fdfbf7;margin:0;padding:0;font-family:Georgia,serif;">
<div style="max-width:560px;margin:0 auto;padding:40px 28px;">
  <p style="font-size:.72rem;color:#aaa;text-transform:uppercase;letter-spacing:.1em;margin-bottom:24px;">
    Payment Reminder
  </p>
  {paras}
</div>
</body></html>"""


def send_chase(chase: dict) -> bool:
    """Send a single chase email for an overdue invoice."""
    if not resend.api_key:
        log.error("RESEND_API_KEY not set")
        return False

    day   = chase["day"]
    tmpl  = TEMPLATES.get(day, TEMPLATES[7])
    sym   = _CURRENCY_SYM.get(chase["currency"], chase["currency"])
    ref   = chase["invoice_ref"] or f"INV-{chase['invoice_id']}"
    desc  = chase["description"]
    desc_line = f'Description: "{desc}"' if desc else ""

    from datetime import date, datetime
    due   = chase["due_date"]
    try:
        due_dt = datetime.strptime(due, "%Y-%m-%d").date()
        days_late = (date.today() - due_dt).days
    except Exception:
        days_late = day

    plain = tmpl["body"].format(
        client=chase["client_name"],
        ref=ref,
        sym=sym,
        amount=f"{chase['amount']:,.2f}",
        due_date=due,
        days=days_late,
        description_line=desc_line,
        user_name=chase["user_name"],
    )
    subject = tmpl["subject"].format(ref=ref, days=days_late)
    html    = _html_wrap(plain, subject)

    try:
        resend.Emails.send({
            "from":     f"{chase['user_name']} <{chase['user_email']}>",
            "to":       [chase["client_email"]],
            "reply_to": chase["user_email"],
            "subject":  subject,
            "html":     html,
            "text":     plain,
        })
        log.info("Chase sent: %s → %s (day %d)", ref, chase["client_email"], day)
        return True
    except Exception as exc:
        log.error("Chase send failed: %s", exc)
        return False


def run_daily_chases() -> int:
    """Called by scheduler — sends all due chases and returns count."""
    db.init()
    pending = db.get_pending_chases()
    sent = 0
    for chase in pending:
        ok = send_chase(chase)
        if ok:
            db.mark_chase_sent(chase["id"])
            sent += 1
    log.info("Daily chase run: %d sent", sent)
    return sent
