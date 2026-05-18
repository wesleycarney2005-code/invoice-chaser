"""Invoice Chaser — automated payment chasing SaaS."""
from dotenv import load_dotenv
load_dotenv()

import os, logging
from flask import Flask, request, jsonify, redirect, url_for, session
from apscheduler.schedulers.background import BackgroundScheduler
import db, chaser

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "invoice-chaser-secret-2026")

STRIPE_MONTHLY = os.environ.get("STRIPE_LINK_CHASER", "")

_scheduler = BackgroundScheduler()
_scheduler.add_job(chaser.run_daily_chases, "cron", hour=9, minute=0, id="daily_chases")
_scheduler.start()
db.init()

HTML = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Invoice Chaser — Stop chasing payments manually</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#FDFBF7;color:#1A1612;font-family:Georgia,serif;min-height:100vh}
.nav{display:flex;align-items:center;justify-content:space-between;padding:18px 40px;border-bottom:1px solid #E8E3DA}
.logo{font-size:1.1rem;font-weight:700;letter-spacing:-.02em}
.nav-right{display:flex;gap:12px;align-items:center}
.btn{display:inline-block;padding:10px 22px;border-radius:6px;font-size:.85rem;font-weight:600;cursor:pointer;border:none;text-decoration:none;font-family:Georgia,serif}
.btn-p{background:#1A1612;color:#fff}
.btn-s{background:transparent;color:#1A1612;border:1px solid #C4B89A}
.hero{text-align:center;padding:80px 24px 60px}
.hero h1{font-size:clamp(2rem,5vw,3.4rem);line-height:1.15;margin-bottom:20px;max-width:700px;margin-left:auto;margin-right:auto}
.hero p{font-size:1.05rem;color:#6B5E4E;max-width:520px;margin:0 auto 36px;line-height:1.7}
.badge{display:inline-block;background:#F0EAE0;color:#8B6F47;font-size:.72rem;padding:4px 12px;border-radius:20px;margin-bottom:20px;letter-spacing:.06em;text-transform:uppercase}
.features{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:24px;max-width:900px;margin:0 auto;padding:0 24px 80px}
.feat{background:#fff;border:1px solid #E8E3DA;border-radius:12px;padding:28px}
.feat .icon{font-size:1.6rem;margin-bottom:12px}
.feat h3{font-size:1rem;margin-bottom:8px}
.feat p{font-size:.85rem;color:#6B5E4E;line-height:1.65}
.pricing{background:#1A1612;color:#FDFBF7;text-align:center;padding:60px 24px}
.pricing h2{font-size:2rem;margin-bottom:12px}
.pricing .sub{color:#9A8A7A;margin-bottom:40px}
.price-cards{display:grid;grid-template-columns:repeat(auto-fit,minmax(240px,1fr));gap:20px;max-width:700px;margin:0 auto}
.pcard{border:1px solid #333;border-radius:12px;padding:32px;text-align:center}
.pcard.highlight{border-color:#C4B89A}
.pcard .amount{font-size:2.5rem;font-weight:700;margin:12px 0}
.pcard .period{font-size:.8rem;color:#9A8A7A}
.pcard ul{list-style:none;margin:20px 0 28px;text-align:left}
.pcard ul li{font-size:.85rem;padding:6px 0;color:#C4B89A}
.pcard ul li::before{content:"✓  "}
/* dashboard */
.dash{max-width:960px;margin:0 auto;padding:40px 24px}
.dash h2{font-size:1.4rem;margin-bottom:4px}
.dash .sub{color:#6B5E4E;font-size:.85rem;margin-bottom:32px}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:32px}
.stat{background:#fff;border:1px solid #E8E3DA;border-radius:10px;padding:20px}
.stat .lbl{font-size:.68rem;text-transform:uppercase;letter-spacing:.1em;color:#9A8A7A;margin-bottom:6px}
.stat .val{font-size:1.8rem;font-weight:700}
.form-card{background:#fff;border:1px solid #E8E3DA;border-radius:12px;padding:28px;margin-bottom:24px}
.form-card h3{font-size:1rem;margin-bottom:20px}
.fg{margin-bottom:16px}
.fg label{display:block;font-size:.8rem;color:#6B5E4E;margin-bottom:5px}
.fg input,.fg textarea,.fg select{width:100%;padding:10px 14px;border:1px solid #D4C9B5;border-radius:6px;font-size:.9rem;font-family:Georgia,serif;background:#FDFBF7;color:#1A1612}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.inv-table{width:100%;border-collapse:collapse;font-size:.85rem}
.inv-table th{text-align:left;padding:10px 12px;color:#9A8A7A;font-size:.72rem;text-transform:uppercase;letter-spacing:.08em;border-bottom:1px solid #E8E3DA}
.inv-table td{padding:10px 12px;border-bottom:1px solid #F0EAE0}
.badge-unpaid{background:#FFF0E0;color:#C4622D;padding:2px 8px;border-radius:4px;font-size:.72rem;font-weight:600}
.badge-paid{background:#E0F4E8;color:#2D7A46;padding:2px 8px;border-radius:4px;font-size:.72rem;font-weight:600}
.save-msg{color:#2D7A46;font-size:.8rem;margin-top:8px;min-height:18px}
.login-box{max-width:420px;margin:80px auto;padding:40px;background:#fff;border:1px solid #E8E3DA;border-radius:16px;text-align:center}
.login-box h2{margin-bottom:8px}
.login-box p{color:#6B5E4E;font-size:.88rem;margin-bottom:28px}
</style>
</head>
<body>

<nav class="nav">
  <div class="logo">Invoice Chaser</div>
  <div class="nav-right" id="nav-btns">
    <a href="#pricing" class="btn btn-s">Pricing</a>
    <a href="/login" class="btn btn-p">Get Started</a>
  </div>
</nav>

<div id="page-home">
  <div class="hero">
    <div class="badge">Stop chasing. Start earning.</div>
    <h1>Automated payment reminders.<br>Without the awkwardness.</h1>
    <p>Add your overdue invoices and Invoice Chaser automatically sends polite, professional payment reminders on day 1, 3, and 7 — in your name, from your email.</p>
    <a href="/login" class="btn btn-p" style="padding:14px 32px;font-size:.95rem;">Start free — no card needed</a>
  </div>

  <div class="features">
    <div class="feat">
      <div class="icon">📬</div>
      <h3>Automated chasing</h3>
      <p>Sends reminder emails at day 1, 3, and 7 after the due date. Friendly tone on day 1, firm on day 3, formal on day 7.</p>
    </div>
    <div class="feat">
      <div class="icon">✍️</div>
      <h3>Sent as you</h3>
      <p>Emails come from your own email address with your name. No "sent by Invoice Chaser" branding on the free plan.</p>
    </div>
    <div class="feat">
      <div class="icon">✅</div>
      <h3>Mark as paid</h3>
      <p>One click stops all future chases the moment a client pays. No awkward reminders after you've been paid.</p>
    </div>
    <div class="feat">
      <div class="icon">📊</div>
      <h3>Outstanding at a glance</h3>
      <p>See all unpaid invoices, total value outstanding, and which chases have gone out — in one clean dashboard.</p>
    </div>
  </div>

  <div class="pricing" id="pricing">
    <h2>Simple pricing</h2>
    <p class="sub">No hidden fees. Cancel anytime.</p>
    <div class="price-cards">
      <div class="pcard">
        <div>Free</div>
        <div class="amount">£0</div>
        <div class="period">forever</div>
        <ul>
          <li>Up to 3 active invoices</li>
          <li>Day 1 + 3 chases</li>
          <li>Sent from your email</li>
          <li>Basic dashboard</li>
        </ul>
        <a href="/login" class="btn btn-p" style="width:100%;display:block;text-align:center;">Get started</a>
      </div>
      <div class="pcard highlight">
        <div>Pro</div>
        <div class="amount">£9.99</div>
        <div class="period">per month</div>
        <ul>
          <li>Unlimited invoices</li>
          <li>Day 1, 3 + 7 chases</li>
          <li>Priority support</li>
          <li>CSV export</li>
          <li>Custom email templates</li>
        </ul>
        <a href="STRIPE_MONTHLY_PLACEHOLDER" class="btn btn-p" style="width:100%;display:block;text-align:center;">Upgrade to Pro</a>
      </div>
    </div>
  </div>
</div>

</body>
</html>"""

DASH_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Invoice Chaser — Dashboard</title>
<style>
*{box-sizing:border-box;margin:0;padding:0}
body{background:#FDFBF7;color:#1A1612;font-family:Georgia,serif;min-height:100vh}
.nav{display:flex;align-items:center;justify-content:space-between;padding:18px 40px;border-bottom:1px solid #E8E3DA}
.logo{font-size:1.1rem;font-weight:700}
.btn{display:inline-block;padding:10px 22px;border-radius:6px;font-size:.85rem;font-weight:600;cursor:pointer;border:none;text-decoration:none;font-family:Georgia,serif}
.btn-p{background:#1A1612;color:#fff}
.btn-s{background:transparent;color:#1A1612;border:1px solid #C4B89A;font-size:.8rem;padding:7px 14px}
.btn-sm{padding:6px 14px;font-size:.78rem}
.dash{max-width:960px;margin:0 auto;padding:40px 24px}
.dash h2{font-size:1.4rem;margin-bottom:4px}
.dash-sub{color:#6B5E4E;font-size:.85rem;margin-bottom:32px}
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;margin-bottom:32px}
.stat{background:#fff;border:1px solid #E8E3DA;border-radius:10px;padding:20px}
.stat .lbl{font-size:.68rem;text-transform:uppercase;letter-spacing:.1em;color:#9A8A7A;margin-bottom:6px}
.stat .val{font-size:1.8rem;font-weight:700}
.form-card{background:#fff;border:1px solid #E8E3DA;border-radius:12px;padding:28px;margin-bottom:24px}
.form-card h3{font-size:1rem;margin-bottom:20px;padding-bottom:12px;border-bottom:1px solid #F0EAE0}
.fg{margin-bottom:14px}
.fg label{display:block;font-size:.78rem;color:#6B5E4E;margin-bottom:5px;text-transform:uppercase;letter-spacing:.05em}
.fg input,.fg select{width:100%;padding:10px 14px;border:1px solid #D4C9B5;border-radius:6px;font-size:.88rem;font-family:Georgia,serif;background:#FDFBF7;color:#1A1612}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.row3{display:grid;grid-template-columns:1fr 1fr 1fr;gap:12px}
.inv-table{width:100%;border-collapse:collapse;font-size:.82rem}
.inv-table th{text-align:left;padding:10px 12px;color:#9A8A7A;font-size:.68rem;text-transform:uppercase;letter-spacing:.08em;border-bottom:1px solid #E8E3DA;white-space:nowrap}
.inv-table td{padding:10px 12px;border-bottom:1px solid #F0EAE0;vertical-align:middle}
.badge-unpaid{background:#FFF0E0;color:#C4622D;padding:2px 8px;border-radius:4px;font-size:.7rem;font-weight:600}
.badge-paid{background:#E0F4E8;color:#2D7A46;padding:2px 8px;border-radius:4px;font-size:.7rem;font-weight:600}
.save-msg{color:#2D7A46;font-size:.8rem;margin-top:10px;min-height:18px}
</style>
</head>
<body>
<nav class="nav">
  <div class="logo">Invoice Chaser</div>
  <div style="display:flex;gap:12px;align-items:center">
    <span style="font-size:.82rem;color:#6B5E4E">{{user_email}}</span>
    <a href="/logout" class="btn btn-s">Logout</a>
  </div>
</nav>
<div class="dash">
  <h2>Dashboard</h2>
  <p class="dash-sub">Invoices are chased automatically at day 1, 3, and 7 after the due date.</p>

  <div class="stats">
    <div class="stat"><div class="lbl">Total invoices</div><div class="val" id="s-total">—</div></div>
    <div class="stat"><div class="lbl">Unpaid</div><div class="val" id="s-unpaid">—</div></div>
    <div class="stat"><div class="lbl">Outstanding</div><div class="val" id="s-value">—</div></div>
  </div>

  <div class="form-card">
    <h3>Add Invoice</h3>
    <div class="row2">
      <div class="fg"><label>Client Name</label><input id="f-cname" placeholder="Acme Ltd"></div>
      <div class="fg"><label>Client Email</label><input id="f-cemail" type="email" placeholder="billing@acme.com"></div>
    </div>
    <div class="row3">
      <div class="fg"><label>Amount</label><input id="f-amount" type="number" step="0.01" placeholder="500.00"></div>
      <div class="fg"><label>Currency</label>
        <select id="f-currency">
          <option value="GBP">GBP (£)</option>
          <option value="USD">USD ($)</option>
          <option value="EUR">EUR (€)</option>
        </select>
      </div>
      <div class="fg"><label>Due Date</label><input id="f-due" type="date"></div>
    </div>
    <div class="row2">
      <div class="fg"><label>Invoice Ref (optional)</label><input id="f-ref" placeholder="INV-001"></div>
      <div class="fg"><label>Description (optional)</label><input id="f-desc" placeholder="Web design project"></div>
    </div>
    <button class="btn btn-p" onclick="addInvoice()">Add Invoice + Start Chasing</button>
    <div class="save-msg" id="add-msg"></div>
  </div>

  <div class="form-card">
    <h3>Your Invoices</h3>
    <table class="inv-table">
      <thead><tr>
        <th>Client</th><th>Ref</th><th>Amount</th><th>Due</th><th>Status</th><th>Action</th>
      </tr></thead>
      <tbody id="inv-body"><tr><td colspan="6" style="color:#9A8A7A;padding:20px 12px">Loading…</td></tr></tbody>
    </table>
  </div>
</div>

<script>
async function loadStats(){
  const r = await fetch('/api/stats'); const d = await r.json();
  document.getElementById('s-total').textContent = d.total;
  document.getElementById('s-unpaid').textContent = d.unpaid;
  document.getElementById('s-value').textContent = '£' + d.unpaid_value.toFixed(2);
}
async function loadInvoices(){
  const r = await fetch('/api/invoices'); const d = await r.json();
  const b = document.getElementById('inv-body');
  if(!d.length){b.innerHTML='<tr><td colspan="6" style="color:#9A8A7A;padding:20px 12px">No invoices yet.</td></tr>';return;}
  const sym = {GBP:'£',USD:'$',EUR:'€'};
  b.innerHTML = d.map(i=>`<tr>
    <td>${i.client_name}<br><span style="font-size:.75rem;color:#9A8A7A">${i.client_email}</span></td>
    <td>${i.invoice_ref||'—'}</td>
    <td>${sym[i.currency]||''}${parseFloat(i.amount).toFixed(2)}</td>
    <td>${i.due_date}</td>
    <td><span class="badge-${i.status}">${i.status}</span></td>
    <td>${i.status==='unpaid'?`<button class="btn btn-s btn-sm" onclick="markPaid(${i.id})">Mark paid</button>`:''}</td>
  </tr>`).join('');
}
async function addInvoice(){
  const payload = {
    client_name:  document.getElementById('f-cname').value,
    client_email: document.getElementById('f-cemail').value,
    amount:       parseFloat(document.getElementById('f-amount').value),
    currency:     document.getElementById('f-currency').value,
    due_date:     document.getElementById('f-due').value,
    invoice_ref:  document.getElementById('f-ref').value,
    description:  document.getElementById('f-desc').value,
  };
  const r = await fetch('/api/invoices',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
  const d = await r.json();
  const m = document.getElementById('add-msg');
  if(d.ok){m.textContent='✓ Invoice added — chases scheduled';loadInvoices();loadStats();}
  else{m.style.color='#C4622D';m.textContent=d.error||'Error';}
  setTimeout(()=>m.textContent='',4000);
}
async function markPaid(id){
  await fetch('/api/invoices/'+id+'/paid',{method:'POST'});
  loadInvoices(); loadStats();
}
loadStats(); loadInvoices();
</script>
</body>
</html>"""


@app.route("/")
def index():
    if "user_id" in session:
        return redirect("/dashboard")
    return HTML.replace("STRIPE_MONTHLY_PLACEHOLDER", STRIPE_MONTHLY or "#pricing")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        data  = request.json or {}
        email = data.get("email", "").strip().lower()
        name  = data.get("name", email.split("@")[0].title())
        if not email or "@" not in email:
            return jsonify({"ok": False, "error": "Valid email required"})
        user = db.get_or_create_user(email, name)
        session["user_id"]    = user["id"]
        session["user_email"] = user["email"]
        session["user_name"]  = user["name"]
        return jsonify({"ok": True})
    return """<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Login</title>
<style>*{box-sizing:border-box;margin:0;padding:0}body{background:#FDFBF7;font-family:Georgia,serif;display:flex;align-items:center;justify-content:center;min-height:100vh}
.box{background:#fff;border:1px solid #E8E3DA;border-radius:16px;padding:48px;max-width:400px;width:90%;text-align:center}
h2{margin-bottom:8px}p{color:#6B5E4E;font-size:.88rem;margin-bottom:28px}
input{width:100%;padding:11px 14px;border:1px solid #D4C9B5;border-radius:6px;font-size:.9rem;font-family:Georgia,serif;background:#FDFBF7;margin-bottom:12px}
.btn{width:100%;padding:13px;background:#1A1612;color:#fff;border:none;border-radius:6px;font-size:.9rem;font-family:Georgia,serif;font-weight:600;cursor:pointer}
.msg{color:#C4622D;font-size:.82rem;margin-top:10px;min-height:18px}</style></head>
<body><div class="box"><h2>Invoice Chaser</h2>
<p>Enter your email to get started — no password needed.</p>
<input id="name" placeholder="Your name" type="text">
<input id="email" placeholder="your@email.com" type="email">
<button class="btn" onclick="go()">Continue →</button>
<div class="msg" id="msg"></div></div>
<script>
async function go(){
  const r=await fetch('/login',{method:'POST',headers:{'Content-Type':'application/json'},
    body:JSON.stringify({email:document.getElementById('email').value,name:document.getElementById('name').value})});
  const d=await r.json();
  if(d.ok)window.location='/dashboard';
  else document.getElementById('msg').textContent=d.error||'Error';
}
document.addEventListener('keydown',e=>e.key==='Enter'&&go());
</script></body></html>"""


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")
    return DASH_HTML.replace("{{user_email}}", session.get("user_email", ""))


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/api/stats")
def api_stats():
    if "user_id" not in session:
        return jsonify({"error": "not logged in"}), 401
    return jsonify(db.stats(session["user_id"]))


@app.route("/api/invoices", methods=["GET"])
def api_invoices():
    if "user_id" not in session:
        return jsonify({"error": "not logged in"}), 401
    return jsonify(db.get_invoices(session["user_id"]))


@app.route("/api/invoices", methods=["POST"])
def api_add_invoice():
    if "user_id" not in session:
        return jsonify({"error": "not logged in"}), 401
    d = request.json or {}
    required = ["client_name", "client_email", "amount", "due_date"]
    for f in required:
        if not d.get(f):
            return jsonify({"ok": False, "error": f"{f} is required"})
    try:
        inv_id = db.add_invoice(
            user_id=session["user_id"],
            client_name=d["client_name"],
            client_email=d["client_email"],
            amount=float(d["amount"]),
            due_date=d["due_date"],
            description=d.get("description", ""),
            invoice_ref=d.get("invoice_ref", ""),
            currency=d.get("currency", "GBP"),
        )
        return jsonify({"ok": True, "id": inv_id})
    except Exception as exc:
        return jsonify({"ok": False, "error": str(exc)})


@app.route("/api/invoices/<int:inv_id>/paid", methods=["POST"])
def api_mark_paid(inv_id: int):
    if "user_id" not in session:
        return jsonify({"error": "not logged in"}), 401
    db.mark_paid(inv_id)
    return jsonify({"ok": True})


if __name__ == "__main__":
    import webbrowser
    webbrowser.open("http://127.0.0.1:5051")
    app.run(port=5051, debug=False)
