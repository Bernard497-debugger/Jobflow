from flask import Flask, request, redirect, session
import json
import os
import hashlib
import requests
from datetime import datetime

app = Flask(__name__)
app.secret_key = "json_saas_auth_key_secure_v2"

DB_FILE = "users.json"
GOOGLE_PUBLISHER_ID = "ca-pub-5573963043624926"
GOOGLE_SEARCH_CONSOLE_VERIFY = "your_verification_code_here"

def load_users():
    if not os.path.exists(DB_FILE):
        return {}
    with open(DB_FILE, "r") as f:
        return json.load(f)

def save_users(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2)

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

PLANS = {
    "free": {"name": "Free", "price": "$0", "jobs_per_month": 10, "features": ["10 job searches/month", "Basic search"]},
    "premium": {"name": "Premium", "price": "$9.99", "jobs_per_month": 500, "features": ["Unlimited searches", "Save jobs", "Job alerts", "Advanced filters"]}
}

APP_ID = "YOUR_APP_ID"
APP_KEY = "YOUR_APP_KEY"
BASE_URL = "https://api.adzuna.com/v1/api/jobs"

def search_jobs(keyword, location):
    try:
        url = BASE_URL + "/za/search/1"
        params = {"app_id": APP_ID, "app_key": APP_KEY, "what": keyword, "where": location, "results_per_page": 15}
        r = requests.get(url, params=params, timeout=10)
        return r.json().get("results", [])
    except:
        return []

def get_adsense_head():
    return f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={GOOGLE_PUBLISHER_ID}" crossorigin="anonymous"></script>'

def get_adsense_ad(slot="7654321098"):
    return f'<ins class="adsbygoogle" style="display:block" data-ad-client="{GOOGLE_PUBLISHER_ID}" data-ad-slot="{slot}" data-ad-format="auto" data-full-width-responsive="true"></ins><script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>'

def get_gsc_meta():
    return f'<meta name="google-site-verification" content="{GOOGLE_SEARCH_CONSOLE_VERIFY}" />'

@app.route("/")
def home():
    return redirect("/dashboard" if "user" in session else "/login")

@app.route("/signup", methods=["GET","POST"])
def signup():
    error = None
    users = load_users()

    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = request.form.get("password", "").strip()
        confirm = request.form.get("confirm_password", "").strip()

        if not u or not p:
            error = "Username and password required"
        elif len(u) < 3:
            error = "Username must be at least 3 characters"
        elif len(p) < 6:
            error = "Password must be at least 6 characters"
        elif p != confirm:
            error = "Passwords dont match"
        elif u in users:
            error = "Username already taken"
        else:
            users[u] = {"password": hash_pw(p), "plan": "free", "created": datetime.now().isoformat()}
            save_users(users)
            return redirect("/login?success=Account created! Login to continue")

    error_html = f'<div class="error">WARN {error}</div>' if error else ""
    adsense_head = get_adsense_head()
    gsc_meta = get_gsc_meta()
    
    html = f'''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="description" content="Sign up for JobFlow - Find jobs with AI-powered search"><meta name="keywords" content="job search, employment, career"><title>Sign Up - JobFlow</title>{gsc_meta}{adsense_head}<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{background:linear-gradient(135deg, #0f172a 0%, #1e293b 100%);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#f1f5f9;min-height:100vh;display:flex;align-items:center;justify-content:center}}.container{{width:100%;max-width:480px;padding:20px}}.card{{background:rgba(30,41,59,0.8);backdrop-filter:blur(10px);border:1px solid rgba(148,163,184,0.1);border-radius:20px;padding:50px 40px;box-shadow:0 8px 32px rgba(0,0,0,0.3)}}.logo{{font-size:40px;text-align:center;margin-bottom:20px}}h2{{font-size:28px;margin-bottom:10px;font-weight:600}}.subtitle{{color:#cbd5e1;margin-bottom:30px;font-size:14px}}.form-group{{margin-bottom:20px}}label{{display:block;font-size:13px;font-weight:500;margin-bottom:8px;color:#cbd5e1;text-transform:uppercase}}input{{width:100%;padding:14px 16px;background:rgba(15,23,42,0.5);border:1px solid rgba(148,163,184,0.2);border-radius:10px;color:#f1f5f9;font-size:15px}}.error{{background:rgba(239,68,68,0.1);border:1px solid #ef4444;color:#fca5a5;padding:12px;border-radius:10px;margin-bottom:20px;font-size:13px}}button{{width:100%;padding:14px 20px;background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);color:white;border:none;border-radius:10px;font-size:15px;font-weight:600;cursor:pointer;text-transform:uppercase;margin-top:10px}}.links{{text-align:center;margin-top:20px;font-size:14px}}.links a{{color:#0ea5e9;text-decoration:none}}@media(max-width:480px){{.card{{padding:40px 25px}}}}</style></head><body><div class="container"><div class="card"><div class="logo">POWER</div><h2>Create Account</h2><p class="subtitle">Join JobFlow and find your next opportunity</p>{error_html}<form method="POST"><div class="form-group"><label>Username</label><input type="text" name="username" placeholder="Enter username" required></div><div class="form-group"><label>Password</label><input type="password" name="password" placeholder="Min 6 characters" required></div><div class="form-group"><label>Confirm Password</label><input type="password" name="confirm_password" placeholder="Confirm password" required></div><button type="submit">Sign Up Free</button></form><div class="links">Already have account? <a href="/login">Login here</a> | <a href="/about">About</a></div></div></div></body></html>'''
    return html

@app.route("/login", methods=["GET","POST"])
def login():
    error = None
    success = request.args.get("success")
    users = load_users()

    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = hash_pw(request.form.get("password", "").strip())

        if u in users and users[u]["password"] == p:
            session["user"] = u
            session["plan"] = users[u].get("plan", "free")
            return redirect("/dashboard")
        else:
            error = "Invalid username or password"

    success_html = f'<div class="success">OK {success}</div>' if success else ""
    error_html = f'<div class="error">WARN {error}</div>' if error else ""
    adsense_head = get_adsense_head()
    gsc_meta = get_gsc_meta()
    
    html = f'''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="description" content="Login to JobFlow - Access your job search account"><title>Login - JobFlow</title>{gsc_meta}{adsense_head}<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{background:linear-gradient(135deg, #0f172a 0%, #1e293b 100%);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#f1f5f9;min-height:100vh;display:flex;align-items:center;justify-content:center}}.container{{width:100%;max-width:480px;padding:20px}}.card{{background:rgba(30,41,59,0.8);backdrop-filter:blur(10px);border:1px solid rgba(148,163,184,0.1);border-radius:20px;padding:50px 40px;box-shadow:0 8px 32px rgba(0,0,0,0.3)}}.logo{{font-size:40px;text-align:center;margin-bottom:20px}}h2{{font-size:28px;margin-bottom:10px;font-weight:600}}.subtitle{{color:#cbd5e1;margin-bottom:30px;font-size:14px}}.form-group{{margin-bottom:20px}}label{{display:block;font-size:13px;font-weight:500;margin-bottom:8px;color:#cbd5e1;text-transform:uppercase}}input{{width:100%;padding:14px 16px;background:rgba(15,23,42,0.5);border:1px solid rgba(148,163,184,0.2);border-radius:10px;color:#f1f5f9;font-size:15px}}.error{{background:rgba(239,68,68,0.1);border:1px solid #ef4444;color:#fca5a5;padding:12px;border-radius:10px;margin-bottom:20px;font-size:13px}}.success{{background:rgba(34,197,94,0.1);border:1px solid #22c55e;color:#86efac;padding:12px;border-radius:10px;margin-bottom:20px;font-size:13px}}button{{width:100%;padding:14px 20px;background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);color:white;border:none;border-radius:10px;font-size:15px;font-weight:600;cursor:pointer;text-transform:uppercase;margin-top:10px}}.links{{text-align:center;margin-top:20px;font-size:14px}}.links a{{color:#0ea5e9;text-decoration:none}}@media(max-width:480px){{.card{{padding:40px 25px}}}}</style></head><body><div class="container"><div class="card"><div class="logo">POWER</div><h2>Welcome Back</h2><p class="subtitle">Login to your JobFlow account</p>{success_html}{error_html}<form method="POST"><div class="form-group"><label>Username</label><input type="text" name="username" placeholder="Enter username" required></div><div class="form-group"><label>Password</label><input type="password" name="password" placeholder="Enter password" required></div><button type="submit">Login</button></form><div class="links">Don't have account? <a href="/signup">Sign up now</a> | <a href="/about">About</a></div></div></div></body></html>'''
    return html

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login?success=Logged out successfully")

@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")
    
    users = load_users()
    user_data = users.get(session["user"], {})
    plan = session.get("plan", "free")
    plan_info = PLANS.get(plan, PLANS["free"])
    
    features = "".join([f"<li>{f}</li>" for f in plan_info['features']])
    upgrade = '<a href="/pricing" class="btn">Upgrade to Premium</a>' if plan == "free" else '<div style="display:flex;gap:10px;justify-content:space-between;align-items:center;"><div style="color:#22c55e;font-weight:600;font-size:13px;">OK Premium Active</div><a href="/downgrade" style="color:#f87171;font-size:13px;text-decoration:underline;">Downgrade</a></div>'
    created = user_data.get('created', 'N/A')[:10]
    plan_class = 'premium' if plan == 'premium' else ''
    adsense_head = get_adsense_head()
    adsense_ad = get_adsense_ad("7654321098")
    gsc_meta = get_gsc_meta()
    
    html = f'''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="description" content="JobFlow Dashboard - Manage your job search"><title>Dashboard - JobFlow</title>{gsc_meta}{adsense_head}<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{background:linear-gradient(135deg, #0f172a 0%, #1e293b 100%);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#f1f5f9;min-height:100vh}}.navbar{{background:rgba(30,41,59,0.8);backdrop-filter:blur(10px);border-bottom:1px solid rgba(148,163,184,0.1);padding:15px 30px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:100}}.navbar-brand{{font-size:24px;font-weight:600;display:flex;align-items:center;gap:10px}}.navbar-menu{{display:flex;gap:20px;align-items:center}}.user-info{{display:flex;align-items:center;gap:8px;padding:8px 12px;background:rgba(15,23,42,0.5);border-radius:8px}}.plan-badge{{padding:6px 12px;background:rgba(14,165,233,0.2);border:1px solid rgba(14,165,233,0.3);border-radius:6px;font-size:12px;font-weight:500;color:#0ea5e9;text-transform:uppercase}}.plan-badge.premium{{background:rgba(168,85,247,0.2);border-color:rgba(168,85,247,0.3);color:#a855f7}}a{{color:#0ea5e9;text-decoration:none}}.container{{max-width:1200px;margin:40px auto;padding:0 20px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:25px;margin-bottom:40px}}.card{{background:rgba(30,41,59,0.6);backdrop-filter:blur(10px);border:1px solid rgba(148,163,184,0.1);border-radius:15px;padding:30px;transition:all 0.3s ease}}.card:hover{{border-color:rgba(14,165,233,0.3);transform:translateY(-5px)}}.welcome-card{{grid-column:1/-1}}.welcome-card h1{{font-size:36px;margin-bottom:15px;background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}.card h3{{font-size:18px;margin-bottom:15px}}.card-content{{color:#cbd5e1;font-size:14px;line-height:1.6;margin-bottom:15px}}.features-list{{list-style:none}}.features-list li{{padding:8px 0;color:#cbd5e1}}.features-list li:before{{content:'CHECK ';color:#22c55e;font-weight:bold}}.btn{{display:inline-block;padding:12px 24px;background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);color:white;border-radius:8px;text-decoration:none;transition:all 0.3s ease;font-weight:600;font-size:14px;text-transform:uppercase}}.btn:hover{{transform:translateY(-2px);box-shadow:0 8px 20px rgba(14,165,233,0.3)}}.search-card{{grid-column:1/-1}}form{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:15px}}.form-group{{display:flex;flex-direction:column}}.form-group label{{font-size:12px;font-weight:600;color:#cbd5e1;text-transform:uppercase;margin-bottom:6px}}input{{padding:12px 14px;background:rgba(15,23,42,0.5);border:1px solid rgba(148,163,184,0.2);border-radius:8px;color:#f1f5f9}}.button-group{{display:flex;gap:10px}}.button-group .btn{{flex:1;padding:12px}}.logout-btn{{background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);color:#fca5a5;padding:8px 16px}}.ad-container{{grid-column:1/-1;background:rgba(15,23,42,0.5);border:1px solid rgba(148,163,184,0.2);border-radius:15px;padding:20px;text-align:center;min-height:300px}}@media(max-width:768px){{.navbar{{flex-direction:column;gap:15px}}.grid{{grid-template-columns:1fr}}form{{grid-template-columns:1fr}}}}</style></head><body><div class="navbar"><div class="navbar-brand"><em style="font-size:28px;">POWER</em> JobFlow</div><div class="navbar-menu"><div class="user-info">FACE {session['user']}</div><span class="plan-badge {plan_class}">{plan_info['name']}</span><a href="/logout" class="logout-btn">Logout</a></div></div><div class="container"><div class="grid"><div class="card welcome-card"><h1>Welcome, {session['user']}! WAVE</h1><p>Find your next opportunity with JobFlow. Your plan: <strong>{plan_info['name']}</strong></p></div><div class="card"><h3>CHART Your Plan</h3><div class="card-content"><p><strong>{plan_info['name']}</strong> - {plan_info['price']}/month</p><p style="margin-top:10px;">Searches/month: <strong>{plan_info['jobs_per_month']}</strong></p></div>{upgrade}</div><div class="card"><h3>STAR Premium Features</h3><ul class="features-list">{features}</ul></div><div class="card"><h3>TARGET Quick Stats</h3><div class="card-content"><p>Member since: <strong>{created}</strong></p><p style="margin-top:10px;">Account Status: <strong style="color:#22c55e;">Active</strong></p></div></div><div class="card search-card"><h3>SEARCH Search for Jobs</h3><form action="/search" method="GET"><div class="form-group"><label>Job Category</label><input type="text" name="category" placeholder="e.g. Python Developer" required></div><div class="form-group"><label>Location</label><input type="text" name="location" placeholder="e.g. Johannesburg" required></div><div class="button-group"><button type="submit" class="btn" style="margin:0;">Search Jobs</button></div></form></div><div class="ad-container">{adsense_ad}</div></div><div style="text-align:center;margin-top:30px;color:#cbd5e1;font-size:12px;"><a href="/about" style="color:#0ea5e9;">About</a> | <a href="/privacy" style="color:#0ea5e9;">Privacy</a> | <a href="/terms" style="color:#0ea5e9;">Terms</a></div></div></body></html>'''
    return html

@app.route("/pricing")
def pricing():
    if "user" not in session:
        return redirect("/login")
    
    current_plan = session.get("plan", "free")
    adsense_head = get_adsense_head()
    adsense_ad = get_adsense_ad("1234567890")
    gsc_meta = get_gsc_meta()
    
    active_free = 'active' if current_plan == 'free' else ''
    active_premium = 'active' if current_plan == 'premium' else ''
    if current_plan == 'premium':
        premium_btn = '<button class="btn btn-current" disabled>Your Current Plan</button>'
    else:
        premium_btn = '<button class="btn" onclick="upgradePlan()">Upgrade Now</button>'
    
    html = f'''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="description" content="JobFlow Pricing - Choose your perfect plan"><title>Pricing - JobFlow</title>{gsc_meta}{adsense_head}<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{background:linear-gradient(135deg, #0f172a 0%, #1e293b 100%);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#f1f5f9;min-height:100vh}}.navbar{{background:rgba(30,41,59,0.8);backdrop-filter:blur(10px);border-bottom:1px solid rgba(148,163,184,0.1);padding:15px 30px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:100}}.navbar a{{color:#0ea5e9;text-decoration:none;font-weight:600}}.container{{max-width:1000px;margin:40px auto;padding:0 20px}}.header{{text-align:center;margin-bottom:50px}}.header h1{{font-size:40px;margin-bottom:10px;background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}.pricing-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:30px;margin-bottom:40px}}.pricing-card{{background:rgba(30,41,59,0.6);backdrop-filter:blur(10px);border:1px solid rgba(148,163,184,0.1);border-radius:20px;padding:40px;transition:all 0.3s ease;position:relative}}.pricing-card:hover{{border-color:rgba(14,165,233,0.3);transform:translateY(-10px)}}.pricing-card.active{{border:2px solid #0ea5e9;background:rgba(30,41,59,0.8)}}.pricing-card .badge{{position:absolute;top:-15px;right:20px;background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);color:white;padding:6px 12px;border-radius:20px;font-size:12px;font-weight:600;text-transform:uppercase}}.pricing-card h2{{font-size:24px;margin-bottom:10px}}.price{{font-size:36px;font-weight:700;color:#0ea5e9;margin-bottom:5px}}.features{{list-style:none;margin-bottom:30px}}.features li{{padding:10px 0;color:#cbd5e1;display:flex;align-items:center;gap:8px;border-bottom:1px solid rgba(148,163,184,0.1)}}.features li:before{{content:'CHECK';color:#22c55e;font-weight:bold;font-size:12px}}.btn{{display:block;width:100%;padding:14px 24px;background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);color:white;border:none;border-radius:10px;text-decoration:none;text-align:center;font-weight:600;font-size:14px;cursor:pointer;transition:all 0.3s ease;text-transform:uppercase}}.btn:hover{{transform:translateY(-2px);box-shadow:0 8px 20px rgba(14,165,233,0.3)}}.btn-current{{background:rgba(34,197,94,0.2);color:#86efac;border:1px solid #22c55e}}.ad-container{{background:rgba(30,41,59,0.6);backdrop-filter:blur(10px);border:1px solid rgba(148,163,184,0.1);border-radius:20px;padding:30px;margin-top:40px;text-align:center;min-height:300px}}@media(max-width:768px){{.pricing-grid{{grid-template-columns:1fr}}.header h1{{font-size:28px}}}}</style></head><body><div class="navbar"><a href="/dashboard">BACK Back to Dashboard</a></div><div class="container"><div class="header"><h1>Simple, Transparent Pricing</h1><p>Choose the perfect plan for your job search</p></div><div class="pricing-grid"><div class="pricing-card {active_free}"><h2>Free</h2><div class="price">$0</div><div style="color:#cbd5e1;margin-bottom:30px;font-size:14px;">/month</div><ul class="features"><li>10 job searches</li><li>Basic search</li><li>Email support</li></ul><button class="btn btn-current" disabled>Your Current Plan</button></div><div class="pricing-card {active_premium}"><div class="badge">POPULAR</div><h2>Premium</h2><div class="price">$9.99</div><div style="color:#cbd5e1;margin-bottom:30px;font-size:14px;">/month</div><ul class="features"><li>Unlimited searches</li><li>Save jobs</li><li>Job alerts</li><li>Advanced filters</li></ul>{premium_btn}</div></div><div class="ad-container">{adsense_ad}</div></div><script>function upgradePlan(){{if(confirm('Upgrade to Premium for $9.99/month?')){{window.location.href='/checkout';}}}}</script></body></html>'''
    return html

@app.route("/checkout")
def checkout():
    if "user" not in session:
        return redirect("/login")
    
    adsense_head = get_adsense_head()
    gsc_meta = get_gsc_meta()
    
    html = f'''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="description" content="JobFlow Checkout - Complete your upgrade"><title>Checkout - JobFlow</title>{gsc_meta}{adsense_head}<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{background:linear-gradient(135deg, #0f172a 0%, #1e293b 100%);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#f1f5f9;min-height:100vh;display:flex;align-items:center;justify-content:center}}.container{{width:100%;max-width:500px;padding:20px}}.card{{background:rgba(30,41,59,0.8);backdrop-filter:blur(10px);border:1px solid rgba(148,163,184,0.1);border-radius:20px;padding:40px;box-shadow:0 8px 32px rgba(0,0,0,0.3)}}.logo{{font-size:40px;text-align:center;margin-bottom:20px}}h2{{font-size:28px;margin-bottom:20px;background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}.plan-box{{background:rgba(15,23,42,0.5);border:1px solid rgba(148,163,184,0.2);border-radius:10px;padding:20px;margin-bottom:20px}}.plan-box h3{{margin-bottom:10px;color:#0ea5e9}}.price-display{{font-size:32px;font-weight:700;color:#0ea5e9;margin-bottom:20px}}.features-list{{list-style:none;margin-bottom:20px}}.features-list li{{padding:8px 0;color:#cbd5e1;display:flex;gap:8px}}.features-list li:before{{content:'CHECK';color:#22c55e;font-weight:bold;font-size:12px}}.form-group{{margin-bottom:15px}}label{{display:block;font-size:13px;font-weight:500;margin-bottom:6px;color:#cbd5e1;text-transform:uppercase}}input{{width:100%;padding:12px;background:rgba(15,23,42,0.5);border:1px solid rgba(148,163,184,0.2);border-radius:8px;color:#f1f5f9}}.btn{{width:100%;padding:14px;background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);color:white;border:none;border-radius:10px;font-weight:600;cursor:pointer;transition:all 0.3s ease;text-transform:uppercase;margin-top:20px}}.btn:hover{{transform:translateY(-2px);box-shadow:0 8px 20px rgba(14,165,233,0.3)}}.info{{background:rgba(34,197,94,0.1);border:1px solid #22c55e;color:#86efac;padding:12px;border-radius:8px;margin-bottom:20px;font-size:13px}}a{{color:#0ea5e9;text-decoration:none}}</style></head><body><div class="container"><div class="card"><div class="logo">MONEY</div><h2>Upgrade to Premium</h2><div class="info">CLOCK Demo Mode: Use card 4242 4242 4242 4242</div><div class="plan-box"><h3>Premium Plan</h3><div class="price-display">$9.99/mo</div><ul class="features-list"><li>Unlimited searches</li><li>Save jobs</li><li>Job alerts</li><li>Advanced filters</li></ul></div><form action="/process-payment" method="POST"><div class="form-group"><label>Cardholder Name</label><input type="text" name="name" placeholder="John Doe" required></div><div class="form-group"><label>Card Number</label><input type="text" name="card" placeholder="4242 4242 4242 4242" maxlength="19" required></div><div style="display:grid;grid-template-columns:1fr 1fr;gap:10px"><div class="form-group"><label>Expiry (MM/YY)</label><input type="text" name="expiry" placeholder="12/25" maxlength="5" required></div><div class="form-group"><label>CVC</label><input type="text" name="cvc" placeholder="123" maxlength="3" required></div></div><button type="submit" class="btn">Complete Purchase</button><a href="/pricing" style="display:block;text-align:center;margin-top:15px;font-size:14px;">← Back to Pricing</a></form></div></div></body></html>'''
    return html

@app.route("/process-payment", methods=["POST"])
def process_payment():
    if "user" not in session:
        return redirect("/login")
    
    name = request.form.get("name", "").strip()
    card = request.form.get("card", "").strip()
    expiry = request.form.get("expiry", "").strip()
    cvc = request.form.get("cvc", "").strip()
    
    if not all([name, card, expiry, cvc]) or len(card) < 16:
        return "Error: Invalid payment details", 400
    
    users = load_users()
    users[session["user"]]["plan"] = "premium"
    users[session["user"]]["payment_method"] = card[-4:]
    users[session["user"]]["upgraded_at"] = datetime.now().isoformat()
    save_users(users)
    
    session["plan"] = "premium"
    
    adsense_head = get_adsense_head()
    gsc_meta = get_gsc_meta()
    
    html = f'''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="description" content="Payment successful"><title>Payment Success - JobFlow</title>{gsc_meta}{adsense_head}<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{background:linear-gradient(135deg, #0f172a 0%, #1e293b 100%);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#f1f5f9;min-height:100vh;display:flex;align-items:center;justify-content:center}}.container{{width:100%;max-width:500px;padding:20px}}.card{{background:rgba(30,41,59,0.8);backdrop-filter:blur(10px);border:1px solid rgba(148,163,184,0.1);border-radius:20px;padding:40px;text-align:center;box-shadow:0 8px 32px rgba(0,0,0,0.3)}}.success-icon{{font-size:60px;margin-bottom:20px}}h2{{font-size:28px;margin-bottom:10px;color:#22c55e}}.details{{background:rgba(34,197,94,0.1);border:1px solid #22c55e;border-radius:10px;padding:20px;margin-bottom:30px;text-align:left}}.details p{{margin-bottom:10px;color:#86efac}}.btn{{display:inline-block;padding:14px 30px;background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);color:white;text-decoration:none;border-radius:10px;font-weight:600;transition:all 0.3s ease;text-transform:uppercase}}</style></head><body><div class="container"><div class="card"><div class="success-icon">CHECK</div><h2>Payment Successful!</h2><p style="color:#cbd5e1;margin-bottom:20px;">Your upgrade to Premium is complete</p><div class="details"><p>FACE Plan: <strong>Premium</strong></p><p>CLOCK Billing: Monthly at $9.99</p><p>STATUS Your account is now active</p></div><a href="/dashboard" class="btn">Go to Dashboard</a></div></div></body></html>'''
    return html

@app.route("/downgrade")
def downgrade():
    if "user" not in session:
        return redirect("/login")
    
    users = load_users()
    users[session["user"]]["plan"] = "free"
    users[session["user"]]["downgraded_at"] = datetime.now().isoformat()
    save_users(users)
    session["plan"] = "free"
    
    return redirect("/dashboard?downgraded=true")

@app.route("/search")
def search():
    if "user" not in session:
        return redirect("/login")

    category = request.args.get("category", "")
    location = request.args.get("location", "")
    jobs = search_jobs(category, location) if category and location else []

    if not jobs:
        content = '<div style="text-align:center;padding:40px;"><p>No jobs found. Try different keywords.</p></div>'
    else:
        content = ""
        for job in jobs:
            title = job.get('title', 'Job Title')
            company = job.get('company', {}).get('display_name', 'Company')
            loc = job.get('location', {}).get('display_name', 'Location')
            url = job.get('redirect_url', '#')
            content += f'<div style="background:rgba(30,41,59,0.6);backdrop-filter:blur(10px);border:1px solid rgba(148,163,184,0.1);border-radius:15px;padding:25px;margin-bottom:20px;transition:all 0.3s ease;"><div style="font-size:18px;font-weight:600;margin-bottom:8px;">{title}</div><div style="font-size:15px;color:#0ea5e9;font-weight:500;margin-bottom:5px;">{company}</div><div style="font-size:13px;color:#cbd5e1;margin-bottom:15px;">PIN {loc}</div><a href="{url}" target="_blank" style="display:inline-block;padding:12px 24px;background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);color:white;border-radius:8px;text-decoration:none;font-weight:600;font-size:13px;text-transform:uppercase;">Apply Now</a></div>'
    
    adsense_head = get_adsense_head()
    adsense_ad = get_adsense_ad("9876543210")
    gsc_meta = get_gsc_meta()
    
    html = f'''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="description" content="Job search results"><title>Job Results - JobFlow</title>{gsc_meta}{adsense_head}<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{background:linear-gradient(135deg, #0f172a 0%, #1e293b 100%);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#f1f5f9;min-height:100vh}}.navbar{{background:rgba(30,41,59,0.8);backdrop-filter:blur(10px);border-bottom:1px solid rgba(148,163,184,0.1);padding:15px 30px;position:sticky;top:0;z-index:100}}.navbar a{{color:#0ea5e9;text-decoration:none;font-weight:600}}.container{{max-width:900px;margin:40px auto;padding:0 20px}}.search-header{{background:rgba(30,41,59,0.6);backdrop-filter:blur(10px);border:1px solid rgba(148,163,184,0.1);border-radius:15px;padding:25px;margin-bottom:30px}}.search-header h2{{font-size:24px;margin-bottom:8px;background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}.ad-container{{background:rgba(30,41,59,0.6);backdrop-filter:blur(10px);border:1px solid rgba(148,163,184,0.1);border-radius:15px;padding:20px;margin:30px 0;text-align:center;min-height:300px}}</style></head><body><div class="navbar"><a href="/dashboard">BACK Back to Dashboard</a></div><div class="container"><div class="search-header"><h2>SEARCH Search Results</h2><p>Jobs for "<strong>{category}</strong>" in <strong>{location}</strong></p></div>{content}<div class="ad-container">{adsense_ad}</div></div></body></html>'''
    return html

@app.route("/about")
def about():
    adsense_head = get_adsense_head()
    adsense_ad = get_adsense_ad("1111111111")
    gsc_meta = get_gsc_meta()
    
    html = f'''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="description" content="About JobFlow - AI-powered job search platform"><meta name="keywords" content="job search, employment, career"><title>About JobFlow</title>{gsc_meta}{adsense_head}<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{background:linear-gradient(135deg, #0f172a 0%, #1e293b 100%);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#f1f5f9;min-height:100vh}}.navbar{{background:rgba(30,41,59,0.8);backdrop-filter:blur(10px);border-bottom:1px solid rgba(148,163,184,0.1);padding:15px 30px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:100}}.navbar-brand{{font-size:24px;font-weight:600}}.navbar a{{color:#0ea5e9;text-decoration:none}}.container{{max-width:900px;margin:40px auto;padding:0 20px}}.card{{background:rgba(30,41,59,0.6);backdrop-filter:blur(10px);border:1px solid rgba(148,163,184,0.1);border-radius:15px;padding:40px;margin-bottom:30px}}.card h2{{font-size:28px;margin-bottom:20px;color:#0ea5e9}}.card h3{{font-size:20px;margin-top:20px;margin-bottom:10px;color:#0ea5e9}}.card p{{color:#cbd5e1;line-height:1.8;margin-bottom:15px}}.card ul{{color:#cbd5e1;margin-left:20px;margin-bottom:15px}}.card li{{margin-bottom:8px}}.ad-container{{background:rgba(30,41,59,0.6);backdrop-filter:blur(10px);border:1px solid rgba(148,163,184,0.1);border-radius:15px;padding:20px;margin:30px 0;text-align:center;min-height:300px}}.links{{text-align:center;margin-top:30px}}.links a{{margin:0 15px;font-weight:600}}</style></head><body>{adsense_head}<div class="navbar"><div class="navbar-brand">POWER JobFlow</div><div><a href="/">Home</a> | <a href="/privacy">Privacy</a> | <a href="/terms">Terms</a></div></div><div class="container"><div class="card"><h2>About JobFlow</h2><p>JobFlow is an AI-powered job search platform designed to help you find your dream career faster than ever.</p><h3>Our Mission</h3><p>We believe job searching should be easy, fast, and effective. JobFlow connects you with opportunities that match your skills.</p><h3>Why Choose JobFlow?</h3><ul><li>SEARCH Lightning-fast job search</li><li>CHECK Real-time job alerts</li><li>STAR Advanced filtering</li><li>CLOCK Trusted by job seekers</li></ul></div><div class="ad-container">{adsense_ad}</div><div class="card"><h3>Get Started</h3><p><a href="/signup" style="color:#0ea5e9;">Sign up for free</a> today!</p></div><div class="links"><a href="/">Home</a> | <a href="/privacy">Privacy</a> | <a href="/terms">Terms</a></div></div></body></html>'''
    return html

@app.route("/privacy")
def privacy():
    adsense_head = get_adsense_head()
    gsc_meta = get_gsc_meta()
    
    html = f'''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="description" content="JobFlow Privacy Policy"><title>Privacy Policy - JobFlow</title>{gsc_meta}{adsense_head}<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{background:linear-gradient(135deg, #0f172a 0%, #1e293b 100%);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#f1f5f9;min-height:100vh}}.navbar{{background:rgba(30,41,59,0.8);backdrop-filter:blur(10px);border-bottom:1px solid rgba(148,163,184,0.1);padding:15px 30px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:100}}.navbar-brand{{font-size:24px;font-weight:600}}.navbar a{{color:#0ea5e9;text-decoration:none}}.container{{max-width:900px;margin:40px auto;padding:0 20px}}.card{{background:rgba(30,41,59,0.6);backdrop-filter:blur(10px);border:1px solid rgba(148,163,184,0.1);border-radius:15px;padding:40px;margin-bottom:30px}}.card h2{{font-size:28px;margin-bottom:20px;color:#0ea5e9}}.card h3{{font-size:18px;margin-top:20px;margin-bottom:10px;color:#0ea5e9}}.card p{{color:#cbd5e1;line-height:1.8;margin-bottom:15px;font-size:14px}}.card ul{{color:#cbd5e1;margin-left:20px;margin-bottom:15px}}.card li{{margin-bottom:8px;font-size:14px}}.links{{text-align:center;margin-top:30px}}.links a{{margin:0 15px;font-weight:600;color:#0ea5e9}}</style></head><body>{adsense_head}<div class="navbar"><div class="navbar-brand">POWER JobFlow</div><div><a href="/">Home</a> | <a href="/about">About</a></div></div><div class="container"><div class="card"><h2>Privacy Policy</h2><h3>1. Information We Collect</h3><p>We collect information you provide directly, such as username and password. We may collect information automatically, such as IP address and browsing activity.</p><h3>2. How We Use Your Information</h3><ul><li>To provide and improve our services</li><li>To process payments</li><li>To send updates</li><li>To comply with legal obligations</li></ul><h3>3. Data Security</h3><p>We implement appropriate measures to protect your personal data against unauthorized access, alteration, disclosure, or destruction.</p><h3>4. Third-Party Services</h3><p>We use Google AdSense for advertising. Please review their privacy policy for more information.</p><h3>5. Cookies</h3><p>Our website uses cookies and similar tracking technologies. You can control cookie settings in your browser.</p><h3>6. Contact Us</h3><p>If you have questions, contact us at support@jobflow.com</p></div><div class="links"><a href="/">Home</a> | <a href="/about">About</a> | <a href="/terms">Terms</a></div></div></body></html>'''
    return html

@app.route("/terms")
def terms():
    adsense_head = get_adsense_head()
    gsc_meta = get_gsc_meta()
    
    html = f'''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><meta name="description" content="JobFlow Terms of Service"><title>Terms of Service - JobFlow</title>{gsc_meta}{adsense_head}<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{background:linear-gradient(135deg, #0f172a 0%, #1e293b 100%);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#f1f5f9;min-height:100vh}}.navbar{{background:rgba(30,41,59,0.8);backdrop-filter:blur(10px);border-bottom:1px solid rgba(148,163,184,0.1);padding:15px 30px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:100}}.navbar-brand{{font-size:24px;font-weight:600}}.navbar a{{color:#0ea5e9;text-decoration:none}}.container{{max-width:900px;margin:40px auto;padding:0 20px}}.card{{background:rgba(30,41,59,0.6);backdrop-filter:blur(10px);border:1px solid rgba(148,163,184,0.1);border-radius:15px;padding:40px;margin-bottom:30px}}.card h2{{font-size:28px;margin-bottom:20px;color:#0ea5e9}}.card h3{{font-size:18px;margin-top:20px;margin-bottom:10px;color:#0ea5e9}}.card p{{color:#cbd5e1;line-height:1.8;margin-bottom:15px;font-size:14px}}.links{{text-align:center;margin-top:30px}}.links a{{margin:0 15px;font-weight:600;color:#0ea5e9}}</style></head><body>{adsense_head}<div class="navbar"><div class="navbar-brand">POWER JobFlow</div><div><a href="/">Home</a> | <a href="/privacy">Privacy</a></div></div><div class="container"><div class="card"><h2>Terms of Service</h2><h3>1. Acceptance of Terms</h3><p>By accessing JobFlow, you accept and agree to be bound by the terms of this agreement.</p><h3>2. Use License</h3><p>Permission is granted to temporarily download one copy of materials for personal, non-commercial viewing only.</p><h3>3. Disclaimer</h3><p>The materials on JobFlow are provided on an AS IS basis. We make no warranties, expressed or implied.</p><h3>4. Limitations</h3><p>In no event shall JobFlow be liable for any damages arising out of the use or inability to use the materials.</p><h3>5. Governing Law</h3><p>These terms are governed by and construed in accordance with the laws of Botswana.</p></div><div class="links"><a href="/">Home</a> | <a href="/about">About</a> | <a href="/privacy">Privacy</a></div></div></body></html>'''
    return html

@app.route("/sitemap.xml")
def sitemap():
    xml = '''<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>http://localhost:5000/</loc>
    <lastmod>2025-03-31</lastmod>
    <changefreq>daily</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>http://localhost:5000/about</loc>
    <lastmod>2025-03-31</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.8</priority>
  </url>
  <url>
    <loc>http://localhost:5000/privacy</loc>
    <lastmod>2025-03-31</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>
  <url>
    <loc>http://localhost:5000/terms</loc>
    <lastmod>2025-03-31</lastmod>
    <changefreq>monthly</changefreq>
    <priority>0.7</priority>
  </url>
  <url>
    <loc>http://localhost:5000/pricing</loc>
    <lastmod>2025-03-31</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>
</urlset>'''
    return app.response_class(xml, mimetype='application/xml')

@app.route("/robots.txt")
def robots():
    txt = '''User-agent: *
Allow: /
Allow: /about
Allow: /privacy
Allow: /terms
Allow: /pricing
Allow: /sitemap.xml
Disallow: /admin
Disallow: /api

Sitemap: http://localhost:5000/sitemap.xml'''
    return app.response_class(txt, mimetype='text/plain')

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
