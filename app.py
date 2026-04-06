from flask import Flask, request, redirect, session, url_for
import json
import os
import hashlib
import requests
from datetime import datetime


app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "jobflow_secure_key_2024")

DB_FILE = "users.json"
GOOGLE_PUBLISHER_ID = os.getenv("GOOGLE_PUBLISHER_ID", "ca-pub-5573963043624926")
APP_ID = os.environ.get("APP_ID")
APP_KEY = os.environ.get("APP_KEY")
BASE_URL = "https://api.adzuna.com/v1/api/jobs"

PLANS = {
    "free": {"name": "Free", "price": "$0", "jobs_per_month": 10, "features": ["10 job searches/month", "Basic search"]},
    "premium": {"name": "Premium", "price": "$9.99", "jobs_per_month": 500, "features": ["Unlimited searches", "Save jobs", "Job alerts", "Advanced filters"]}
}

def load_users():
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_users(data):
    try:
        with open(DB_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving users: {e}")

def hash_pw(pw):
    return hashlib.sha256(pw.encode()).hexdigest()

def search_jobs(keyword, location):
    if not APP_ID or not APP_KEY:
        return []
    try:
        url = f"{BASE_URL}/za/search/1"
        params = {
            "app_id": APP_ID,
            "app_key": APP_KEY,
            "what": keyword,
            "where": location,
            "results_per_page": 15
        }
        r = requests.get(url, params=params, timeout=10)
        data = r.json()
        return data.get("results", [])
    except:
        return []

GOOGLE_SITE_VERIFICATION = "google5ce0866dc1e9ca22"

def get_adsense_script():
    return (
        f'<meta name="google-site-verification" content="{GOOGLE_SITE_VERIFICATION}">'
        f'<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js?client={GOOGLE_PUBLISHER_ID}" crossorigin="anonymous"></script>'
    )

def get_adsense_ad(slot="7654321098"):
    return f'<ins class="adsbygoogle" style="display:block" data-ad-client="{GOOGLE_PUBLISHER_ID}" data-ad-slot="{slot}" data-ad-format="auto" data-full-width-responsive="true"></ins><script>(adsbygoogle = window.adsbygoogle || []).push({{}});</script>'

def get_canonical_url():
    """Generate canonical URL for current page without query parameters"""
    return url_for(request.endpoint, _external=True, **{k: v for k, v in request.view_args.items() if k})

@app.route("/")
def home():
    return redirect("/dashboard" if "user" in session else "/login")

@app.route("/signup", methods=["GET","POST"])
def signup():
    error = None
    users = load_users()
    adsense = get_adsense_script()
    canonical = url_for('signup', _external=True)

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

    error_html = f'<div style="background:rgba(239,68,68,0.1);border:1px solid #ef4444;color:#fca5a5;padding:12px;border-radius:10px;margin-bottom:20px;font-size:13px;">WARN {error}</div>' if error else ""
    
    html = f'''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Sign Up - JobFlow</title><link rel="canonical" href="{canonical}">{adsense}<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{background:linear-gradient(135deg, #0f172a 0%, #1e293b 100%);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#f1f5f9;min-height:100vh;display:flex;align-items:center;justify-content:center}}.container{{width:100%;max-width:480px;padding:20px}}.card{{background:rgba(30,41,59,0.8);backdrop-filter:blur(10px);border:1px solid rgba(148,163,184,0.1);border-radius:20px;padding:50px 40px;box-shadow:0 8px 32px rgba(0,0,0,0.3)}}.logo{{font-size:40px;text-align:center;margin-bottom:20px}}h2{{font-size:28px;margin-bottom:10px;font-weight:600}}.subtitle{{color:#cbd5e1;margin-bottom:30px;font-size:14px}}.form-group{{margin-bottom:20px}}label{{display:block;font-size:13px;font-weight:500;margin-bottom:8px;color:#cbd5e1;text-transform:uppercase}}input{{width:100%;padding:14px 16px;background:rgba(15,23,42,0.5);border:1px solid rgba(148,163,184,0.2);border-radius:10px;color:#f1f5f9;font-size:15px}}button{{width:100%;padding:14px 20px;background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);color:white;border:none;border-radius:10px;font-size:15px;font-weight:600;cursor:pointer;text-transform:uppercase;margin-top:10px}}.links{{text-align:center;margin-top:20px;font-size:14px}}.links a{{color:#0ea5e9;text-decoration:none}}@media(max-width:480px){{.card{{padding:40px 25px}}}}</style></head><body><div class="container"><div class="card"><div class="logo">POWER</div><h2>Create Account</h2><p class="subtitle">Join JobFlow and find your next opportunity</p>{error_html}<form method="POST"><div class="form-group"><label>Username</label><input type="text" name="username" placeholder="Enter username" required></div><div class="form-group"><label>Password</label><input type="password" name="password" placeholder="Min 6 characters" required></div><div class="form-group"><label>Confirm Password</label><input type="password" name="confirm_password" placeholder="Confirm password" required></div><button type="submit">Sign Up Free</button></form><div class="links">Already have account? <a href="/login">Login here</a></div></div></div></body></html>'''
    return html

@app.route("/login", methods=["GET","POST"])
def login():
    error = None
    success = request.args.get("success")
    users = load_users()
    adsense = get_adsense_script()
    canonical = url_for('login', _external=True)

    if request.method == "POST":
        u = request.form.get("username", "").strip()
        p = hash_pw(request.form.get("password", "").strip())

        if u in users and users[u]["password"] == p:
            session["user"] = u
            session["plan"] = users[u].get("plan", "free")
            return redirect("/dashboard")
        else:
            error = "Invalid username or password"

    success_html = f'<div style="background:rgba(34,197,94,0.1);border:1px solid #22c55e;color:#86efac;padding:12px;border-radius:10px;margin-bottom:20px;font-size:13px;">OK {success}</div>' if success else ""
    error_html = f'<div style="background:rgba(239,68,68,0.1);border:1px solid #ef4444;color:#fca5a5;padding:12px;border-radius:10px;margin-bottom:20px;font-size:13px;">WARN {error}</div>' if error else ""
    
    html = f'''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Login - JobFlow</title><link rel="canonical" href="{canonical}">{adsense}<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{background:linear-gradient(135deg, #0f172a 0%, #1e293b 100%);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#f1f5f9;min-height:100vh;display:flex;align-items:center;justify-content:center}}.container{{width:100%;max-width:480px;padding:20px}}.card{{background:rgba(30,41,59,0.8);backdrop-filter:blur(10px);border:1px solid rgba(148,163,184,0.1);border-radius:20px;padding:50px 40px;box-shadow:0 8px 32px rgba(0,0,0,0.3)}}.logo{{font-size:40px;text-align:center;margin-bottom:20px}}h2{{font-size:28px;margin-bottom:10px;font-weight:600}}.subtitle{{color:#cbd5e1;margin-bottom:30px;font-size:14px}}.form-group{{margin-bottom:20px}}label{{display:block;font-size:13px;font-weight:500;margin-bottom:8px;color:#cbd5e1;text-transform:uppercase}}input{{width:100%;padding:14px 16px;background:rgba(15,23,42,0.5);border:1px solid rgba(148,163,184,0.2);border-radius:10px;color:#f1f5f9;font-size:15px}}button{{width:100%;padding:14px 20px;background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);color:white;border:none;border-radius:10px;font-size:15px;font-weight:600;cursor:pointer;text-transform:uppercase;margin-top:10px}}.links{{text-align:center;margin-top:20px;font-size:14px}}.links a{{color:#0ea5e9;text-decoration:none}}@media(max-width:480px){{.card{{padding:40px 25px}}}}</style></head><body><div class="container"><div class="card"><div class="logo">POWER</div><h2>Welcome Back</h2><p class="subtitle">Login to your JobFlow account</p>{success_html}{error_html}<form method="POST"><div class="form-group"><label>Username</label><input type="text" name="username" placeholder="Enter username" required></div><div class="form-group"><label>Password</label><input type="password" name="password" placeholder="Enter password" required></div><button type="submit">Login</button></form><div class="links">Don't have account? <a href="/signup">Sign up now</a></div></div></div></body></html>'''
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

    if not user_data:
        session.clear()
        return redirect("/login?success=Session expired. Please login again.")

    plan = user_data.get("plan", "free")
    session["plan"] = plan
    plan_info = PLANS.get(plan, PLANS["free"])
    canonical = url_for('dashboard', _external=True)
    
    features = "".join([f"<li>{f}</li>" for f in plan_info['features']])
    upgrade = '<a href="/pricing" style="display:inline-block;padding:12px 24px;background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);color:white;border-radius:8px;text-decoration:none;transition:all 0.3s ease;font-weight:600;font-size:14px;text-transform:uppercase;">Upgrade to Premium</a>' if plan == "free" else '<div style="display:flex;gap:10px;justify-content:space-between;align-items:center;"><div style="color:#22c55e;font-weight:600;font-size:13px;">OK Premium Active</div><a href="/downgrade" style="color:#f87171;font-size:13px;text-decoration:underline;">Downgrade</a></div>'
    created = user_data.get('created', 'N/A')[:10]
    plan_class = 'premium' if plan == 'premium' else ''
    adsense = get_adsense_script()
    adsense_ad = get_adsense_ad("7654321098")
    
    html = f'''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Dashboard - JobFlow</title><link rel="canonical" href="{canonical}">{adsense}<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{background:linear-gradient(135deg, #0f172a 0%, #1e293b 100%);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#f1f5f9;min-height:100vh}}.navbar{{background:rgba(30,41,59,0.8);backdrop-filter:blur(10px);border-bottom:1px solid rgba(148,163,184,0.1);padding:15px 30px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:100}}.navbar-brand{{font-size:24px;font-weight:600;display:flex;align-items:center;gap:10px}}.navbar-menu{{display:flex;gap:20px;align-items:center}}.user-info{{display:flex;align-items:center;gap:8px;padding:8px 12px;background:rgba(15,23,42,0.5);border-radius:8px}}.plan-badge{{padding:6px 12px;background:rgba(14,165,233,0.2);border:1px solid rgba(14,165,233,0.3);border-radius:6px;font-size:12px;font-weight:500;color:#0ea5e9;text-transform:uppercase}}.plan-badge.premium{{background:rgba(168,85,247,0.2);border-color:rgba(168,85,247,0.3);color:#a855f7}}a{{color:#0ea5e9;text-decoration:none}}.container{{max-width:1200px;margin:40px auto;padding:0 20px}}.grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:25px;margin-bottom:40px}}.card{{background:rgba(30,41,59,0.6);backdrop-filter:blur(10px);border:1px solid rgba(148,163,184,0.1);border-radius:15px;padding:30px;transition:all 0.3s ease}}.card:hover{{border-color:rgba(14,165,233,0.3);transform:translateY(-5px)}}.welcome-card{{grid-column:1/-1}}.welcome-card h1{{font-size:36px;margin-bottom:15px;background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}.card h3{{font-size:18px;margin-bottom:15px}}.card-content{{color:#cbd5e1;font-size:14px;line-height:1.6;margin-bottom:15px}}.features-list{{list-style:none}}.features-list li{{padding:8px 0;color:#cbd5e1}}.features-list li:before{{content:'CHECK ';color:#22c55e;font-weight:bold}}.search-card{{grid-column:1/-1}}form{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:15px}}.form-group{{display:flex;flex-direction:column}}.form-group label{{font-size:12px;font-weight:600;color:#cbd5e1;text-transform:uppercase;margin-bottom:6px}}input{{padding:12px 14px;background:rgba(15,23,42,0.5);border:1px solid rgba(148,163,184,0.2);border-radius:8px;color:#f1f5f9}}.button-group{{display:flex;gap:10px}}.button-group button{{flex:1;padding:12px;background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);color:white;border:none;border-radius:8px;font-weight:600;cursor:pointer;text-transform:uppercase}}.logout-btn{{background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);color:#fca5a5;padding:8px 16px}}.ad-container{{grid-column:1/-1;background:rgba(15,23,42,0.5);border:1px solid rgba(148,163,184,0.2);border-radius:15px;padding:20px;text-align:center;min-height:300px}}@media(max-width:768px){{.navbar{{flex-direction:column;gap:15px}}.grid{{grid-template-columns:1fr}}form{{grid-template-columns:1fr}}}}</style></head><body><div class="navbar"><div class="navbar-brand"><em style="font-size:28px;">POWER</em> JobFlow</div><div class="navbar-menu"><div class="user-info">FACE {session['user']}</div><span class="plan-badge {plan_class}">{plan_info['name']}</span><a href="/logout" class="logout-btn">Logout</a></div></div><div class="container"><div class="grid"><div class="card welcome-card"><h1>Welcome, {session['user']}! WAVE</h1><p>Find your next opportunity with JobFlow. Your plan: <strong>{plan_info['name']}</strong></p></div><div class="card"><h3>CHART Your Plan</h3><div class="card-content"><p><strong>{plan_info['name']}</strong> - {plan_info['price']}/month</p><p style="margin-top:10px;">Searches/month: <strong>{plan_info['jobs_per_month']}</strong></p></div>{upgrade}</div><div class="card"><h3>STAR Premium Features</h3><ul class="features-list">{features}</ul></div><div class="card"><h3>TARGET Quick Stats</h3><div class="card-content"><p>Member since: <strong>{created}</strong></p><p style="margin-top:10px;">Account Status: <strong style="color:#22c55e;">Active</strong></p></div></div><div class="card search-card"><h3>SEARCH Search for Jobs</h3><form action="/search" method="GET"><div class="form-group"><label>Job Category</label><input type="text" name="category" placeholder="e.g. Python Developer" required></div><div class="form-group"><label>Location</label><input type="text" name="location" placeholder="e.g. Johannesburg" required></div><div class="button-group"><button type="submit" style="margin:0;">Search Jobs</button></div></form></div><div class="ad-container">{adsense_ad}</div></div></div></body></html>'''
    return html

@app.route("/search", methods=["GET"])
def search():
    if "user" not in session:
        return redirect("/login")
    
    category = request.args.get("category", "").strip()
    location = request.args.get("location", "").strip()
    
    # Canonical URL - normalize to consistent params
    canonical = url_for('search', category=category, location=location, _external=True)
    
    adsense = get_adsense_script()
    adsense_ad = get_adsense_ad("7654321098")
    
    results = []
    if category and location:
        results = search_jobs(category, location)
    
    jobs_html = ""
    if results:
        for job in results:
            jobs_html += f'''
            <div class="job-card">
                <h3>{job.get('title', 'Job')}</h3>
                <p class="company">{job.get('company', {}).get('display_name', 'Unknown Company')}</p>
                <p class="location">{job.get('location', {}).get('display_name', 'Location TBD')}</p>
                <p class="salary">{job.get('salary_min', 'N/A')} - {job.get('salary_max', 'N/A')}</p>
                <a href="{job.get('redirect_url', '#')}" target="_blank" class="apply-btn">Apply Now</a>
            </div>
            '''
    else:
        jobs_html = '<p style="grid-column:1/-1;text-align:center;color:#cbd5e1;">No jobs found. Try different search terms.</p>'
    
    html = f'''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Search Results - JobFlow</title><link rel="canonical" href="{canonical}">{adsense}<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{background:linear-gradient(135deg, #0f172a 0%, #1e293b 100%);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#f1f5f9;min-height:100vh}}.navbar{{background:rgba(30,41,59,0.8);backdrop-filter:blur(10px);border-bottom:1px solid rgba(148,163,184,0.1);padding:15px 30px;display:flex;justify-content:space-between;align-items:center}}.navbar a{{color:#0ea5e9;text-decoration:none;font-weight:600}}.container{{max-width:1200px;margin:40px auto;padding:0 20px}}.header{{margin-bottom:30px}}.header h1{{font-size:32px;margin-bottom:10px;background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}.search-filters{{background:rgba(30,41,59,0.6);backdrop-filter:blur(10px);border:1px solid rgba(148,163,184,0.1);border-radius:15px;padding:20px;margin-bottom:30px}}.filter-row{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:15px}}.filter-row input{{padding:12px 14px;background:rgba(15,23,42,0.5);border:1px solid rgba(148,163,184,0.2);border-radius:8px;color:#f1f5f9}}.filter-row button{{padding:12px 24px;background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);color:white;border:none;border-radius:8px;font-weight:600;cursor:pointer}}.jobs-grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(350px,1fr));gap:20px;margin-bottom:40px}}.job-card{{background:rgba(30,41,59,0.6);backdrop-filter:blur(10px);border:1px solid rgba(148,163,184,0.1);border-radius:15px;padding:25px;transition:all 0.3s ease}}.job-card:hover{{border-color:rgba(14,165,233,0.3);transform:translateY(-5px)}}.job-card h3{{font-size:18px;margin-bottom:10px;color:#0ea5e9}}.company{{color:#cbd5e1;font-size:14px;margin-bottom:5px}}.location{{color:#cbd5e1;font-size:14px;margin-bottom:10px}}.salary{{color:#22c55e;font-weight:600;margin-bottom:15px}}.apply-btn{{display:inline-block;padding:12px 24px;background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);color:white;text-decoration:none;border-radius:8px;font-weight:600;transition:all 0.3s ease}}.apply-btn:hover{{transform:translateY(-2px)}}.ad-container{{background:rgba(30,41,59,0.6);backdrop-filter:blur(10px);border:1px solid rgba(148,163,184,0.1);border-radius:15px;padding:20px;text-align:center;min-height:300px}}@media(max-width:768px){{.jobs-grid{{grid-template-columns:1fr}}}}</style></head><body><div class="navbar"><a href="/dashboard">BACK Back to Dashboard</a></div><div class="container"><div class="header"><h1>Search Results</h1><p>Found jobs for "{category}" in "{location}"</p></div><div class="search-filters"><div class="filter-row"><input type="text" placeholder="Job Category" value="{category}" id="category"><input type="text" placeholder="Location" value="{location}" id="location"><button onclick="window.location=`/search?category=${{document.getElementById('category').value}}&location=${{document.getElementById('location').value}}`;">Search Again</button></div></div><div class="jobs-grid">{jobs_html}</div><div class="ad-container">{adsense_ad}</div></div></body></html>'''
    return html

@app.route("/pricing")
def pricing():
    if "user" not in session:
        return redirect("/login")
    
    current_plan = session.get("plan", "free")
    canonical = url_for('pricing', _external=True)
    adsense = get_adsense_script()
    adsense_ad = get_adsense_ad("1234567890")
    
    active_free = 'style="border:2px solid #0ea5e9;background:rgba(30,41,59,0.8);"' if current_plan == "free" else ""
    active_premium = 'style="border:2px solid #0ea5e9;background:rgba(30,41,59,0.8);"' if current_plan == "premium" else ""
    if current_plan == "premium":
        premium_btn = '<button style="background:rgba(34,197,94,0.2);color:#86efac;border:1px solid #22c55e;cursor:not-allowed;" disabled>Your Current Plan</button>'
    else:
        premium_btn = '<button onclick="if(confirm(\'Upgrade to Premium for $9.99/month?\')){window.location.href=\'/checkout\';}" style="width:100%;padding:14px;background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);color:white;border:none;border-radius:10px;font-weight:600;cursor:pointer;text-transform:uppercase;">Upgrade Now</button>'
    
    html = f'''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Pricing - JobFlow</title><link rel="canonical" href="{canonical}">{adsense}<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{background:linear-gradient(135deg, #0f172a 0%, #1e293b 100%);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#f1f5f9;min-height:100vh}}.navbar{{background:rgba(30,41,59,0.8);backdrop-filter:blur(10px);border-bottom:1px solid rgba(148,163,184,0.1);padding:15px 30px;position:sticky;top:0;z-index:100}}.navbar a{{color:#0ea5e9;text-decoration:none;font-weight:600}}.container{{max-width:1000px;margin:40px auto;padding:0 20px}}.header{{text-align:center;margin-bottom:50px}}.header h1{{font-size:40px;margin-bottom:10px;background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}.pricing-grid{{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:30px;margin-bottom:40px}}.pricing-card{{background:rgba(30,41,59,0.6);backdrop-filter:blur(10px);border:1px solid rgba(148,163,184,0.1);border-radius:20px;padding:40px;transition:all 0.3s ease}}.pricing-card:hover{{border-color:rgba(14,165,233,0.3);transform:translateY(-10px)}}.pricing-card h2{{font-size:24px;margin-bottom:10px}}.price{{font-size:36px;font-weight:700;color:#0ea5e9;margin-bottom:5px}}.price-period{{color:#cbd5e1;font-size:14px;margin-bottom:30px}}.features{{list-style:none;margin-bottom:30px}}.features li{{padding:10px 0;color:#cbd5e1;display:flex;align-items:center;gap:8px;border-bottom:1px solid rgba(148,163,184,0.1)}}.features li:before{{content:'CHECK';color:#22c55e;font-weight:bold;font-size:12px}}.ad-container{{background:rgba(30,41,59,0.6);backdrop-filter:blur(10px);border:1px solid rgba(148,163,184,0.1);border-radius:20px;padding:30px;margin-top:40px;text-align:center;min-height:300px}}@media(max-width:768px){{.pricing-grid{{grid-template-columns:1fr}}.header h1{{font-size:28px}}}}</style></head><body><div class="navbar"><a href="/dashboard">BACK Back to Dashboard</a></div><div class="container"><div class="header"><h1>Simple, Transparent Pricing</h1><p>Choose the perfect plan for your job search</p></div><div class="pricing-grid"><div class="pricing-card" {active_free}><h2>Free</h2><div class="price">$0</div><div class="price-period">/month</div><ul class="features"><li>10 job searches</li><li>Basic search</li><li>Email support</li></ul><button style="width:100%;padding:14px;background:rgba(34,197,94,0.2);color:#86efac;border:1px solid #22c55e;border-radius:10px;font-weight:600;cursor:not-allowed;" disabled>Your Current Plan</button></div><div class="pricing-card" {active_premium}><h2>Premium</h2><div class="price">$9.99</div><div class="price-period">/month</div><ul class="features"><li>Unlimited searches</li><li>Save jobs</li><li>Job alerts</li><li>Advanced filters</li></ul>{premium_btn}</div></div><div class="ad-container">{adsense_ad}</div></div></body></html>'''
    return html

@app.route("/checkout")
def checkout():
    if "user" not in session:
        return redirect("/login")
    
    canonical = url_for('checkout', _external=True)
    adsense = get_adsense_script()
    
    html = f'''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Checkout - JobFlow</title><link rel="canonical" href="{canonical}">{adsense}<style>*{{margin:0;padding:0;box-sizing:border-box}}body{{background:linear-gradient(135deg, #0f172a 0%, #1e293b 100%);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#f1f5f9;min-height:100vh;display:flex;align-items:center;justify-content:center}}.container{{width:100%;max-width:500px;padding:20px}}.card{{background:rgba(30,41,59,0.8);backdrop-filter:blur(10px);border:1px solid rgba(148,163,184,0.1);border-radius:20px;padding:40px;box-shadow:0 8px 32px rgba(0,0,0,0.3)}}.card h2{{font-size:28px;margin-bottom:10px}}.card p{{color:#cbd5e1;margin-bottom:30px}}.price-display{{font-size:48px;color:#0ea5e9;font-weight:700;margin-bottom:20px}}.features{{list-style:none;margin-bottom:30px}}.features li{{padding:8px 0;color:#cbd5e1;display:flex;align-items:center;gap:8px}}.features li:before{{content:'CHECK';color:#22c55e;font-weight:bold;font-size:12px}}.form-group{{margin-bottom:20px}}.form-group label{{display:block;font-size:12px;font-weight:600;color:#cbd5e1;text-transform:uppercase;margin-bottom:8px}}input{{width:100%;padding:12px 14px;background:rgba(15,23,42,0.5);border:1px solid rgba(148,163,184,0.2);border-radius:8px;color:#f1f5f9}}button{{width:100%;padding:14px 20px;background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);color:white;border:none;border-radius:10px;font-size:15px;font-weight:600;cursor:pointer;text-transform:uppercase;margin-top:10px}}.note{{background:rgba(59,130,246,0.1);border:1px solid rgba(59,130,246,0.3);color:#bfdbfe;padding:12px;border-radius:8px;font-size:12px;margin-top:20px}}</style></head><body><div class="container"><div class="card"><h2>Upgrade to Premium</h2><p>Get unlimited job searches and advanced features</p><div class="price-display">$9.99</div><p style="color:#cbd5e1;margin-bottom:20px;">/month</p><ul class="features"><li>Unlimited job searches</li><li>Save favorite jobs</li><li>Job alerts</li><li>Advanced filters</li></ul><form onsubmit="alert('Payment processing would happen here.\\n\\nIn production, integrate with Stripe/PayPal.\\n\\nFor now, click OK to continue.'); return false;"><div class="form-group"><label>Cardholder Name</label><input type="text" placeholder="John Doe" required></div><div class="form-group"><label>Card Number</label><input type="text" placeholder="4242 4242 4242 4242" maxlength="19" required></div><div style="display:grid;grid-template-columns:1fr 1fr;gap:15px;"><div class="form-group"><label>Expiry</label><input type="text" placeholder="MM/YY" maxlength="5" required></div><div class="form-group"><label>CVV</label><input type="text" placeholder="123" maxlength="3" required></div></div><button type="submit">Complete Payment</button></form><div class="note">NOTE: This is a demo. In production, integrate with Stripe or PayPal for actual payments.</div></div></div></body></html>'''
    return html

@app.route("/downgrade")
def downgrade():
    if "user" not in session:
        return redirect("/login")
    
    users = load_users()
    if session["user"] in users:
        users[session["user"]]["plan"] = "free"
        save_users(users)
        session["plan"] = "free"
    
    return redirect("/dashboard?success=Downgraded to Free plan")

# Robots.txt
@app.route('/robots.txt')
def robots():
    return '''User-agent: *
Allow: /
Disallow: /admin

Sitemap: https://yourdomain.com/sitemap.xml
'''

# Sitemap
@app.route('/sitemap.xml')
def sitemap():
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    # Main pages
    pages = [
        ('/', '2026-03-27', 'weekly'),
        ('/signup', '2026-03-27', 'monthly'),
        ('/login', '2026-03-27', 'monthly'),
        ('/pricing', '2026-03-27', 'weekly'),
    ]
    
    for page, date, freq in pages:
        xml += f'  <url>\n'
        xml += f'    <loc>{url_for("home", _external=True).rstrip("/")}{page}</loc>\n'
        xml += f'    <lastmod>{date}</lastmod>\n'
        xml += f'    <changefreq>{freq}</changefreq>\n'
        xml += f'  </url>\n'
    
    xml += '</urlset>'
    return xml, 200, {'Content-Type': 'application/xml'}

if __name__ == '__main__':
    app.run(debug=True)
