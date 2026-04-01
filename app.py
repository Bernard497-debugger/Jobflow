from flask import Flask, request, redirect, session
import json, os, hashlib, requests
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secure_key_v3"

DB_FILE = "users.json"

# ---------- DATABASE ----------
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

# ---------- PLANS ----------
PLANS = {
    "free": {"name": "Free", "price": "$0"},
    "premium": {"name": "Premium", "price": "$9.99"}
}

# ---------- ENV VARS (FIXED) ----------
APP_ID = os.environ.get("APP_ID")
APP_KEY = os.environ.get("APP_KEY")
BASE_URL = "https://api.adzuna.com/v1/api/jobs"

# ---------- JOB SEARCH ----------
def search_jobs(keyword, location):
    try:
        url = f"{BASE_URL}/za/search/1"

        params = {
            "app_id": APP_ID,
            "app_key": APP_KEY,
            "what": keyword,
            "where": location,
            "results_per_page": 10
        }

        r = requests.get(url, params=params, timeout=10)
        data = r.json()

        print("DEBUG:", data)  # remove later

        return data.get("results", [])

    except Exception as e:
        print("ERROR:", e)
        return []

# ---------- ROUTES ----------
@app.route("/")
def home():
    return redirect("/dashboard" if "user" in session else "/login")

# ---------- SIGNUP ----------
@app.route("/signup", methods=["GET", "POST"])
def signup():
    users = load_users()
    error = None

    if request.method == "POST":
        u = request.form.get("username")
        p = request.form.get("password")
        c = request.form.get("confirm")

        if u in users:
            error = "User exists"
        elif p != c:
            error = "Passwords mismatch"
        else:
            users[u] = {
                "password": hash_pw(p),
                "plan": "free",
                "created": datetime.now().isoformat()
            }
            save_users(users)
            return redirect("/login")

    return f"""
    <h2>Signup</h2>
    {error if error else ""}
    <form method='POST'>
    <input name='username' placeholder='Username'><br>
    <input name='password' type='password'><br>
    <input name='confirm' type='password'><br>
    <button>Signup</button>
    </form>
    <a href='/login'>Login</a>
    """

# ---------- LOGIN ----------
@app.route("/login", methods=["GET", "POST"])
def login():
    users = load_users()
    error = None

    if request.method == "POST":
        u = request.form.get("username")
        p = hash_pw(request.form.get("password"))

        if u in users and users[u]["password"] == p:
            session["user"] = u
            session["plan"] = users[u]["plan"]
            return redirect("/dashboard")
        else:
            error = "Invalid login"

    return f"""
    <h2>Login</h2>
    {error if error else ""}
    <form method='POST'>
    <input name='username'><br>
    <input name='password' type='password'><br>
    <button>Login</button>
    </form>
    <a href='/signup'>Signup</a>
    """

# ---------- LOGOUT ----------
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------- DASHBOARD ----------
@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect("/login")

    return f"""
    <h2>Welcome {session['user']}</h2>
    <a href='/logout'>Logout</a>

    <h3>Search Jobs</h3>
    <form action="/search" method="GET">
        <input name="category" placeholder="Job (e.g Python)">
        <input name="location" placeholder="Location">
        <button>Search</button>
    </form>
    """

# ---------- SEARCH (FIXED) ----------
@app.route("/search", methods=["GET"])
def search():
    if "user" not in session:
        return redirect("/login")

    category = request.args.get("category")
    location = request.args.get("location")

    jobs = search_jobs(category, location)

    if not jobs:
        return f"""
        <h2>No jobs found</h2>
        <a href='/dashboard'>Back</a>
        """

    results = ""
    for job in jobs:
        title = job.get("title", "Job")
        company = job.get("company", {}).get("display_name", "")
        url = job.get("redirect_url", "#")

        results += f"""
        <div>
            <h3>{title}</h3>
            <p>{company}</p>
            <a href="{url}" target="_blank">Apply</a>
        </div>
        <hr>
        """

    return f"""
    <h2>Results</h2>
    {results}
    <a href='/dashboard'>Back</a>
    """

# ---------- RUN ----------
if __name__ == "__main__":
    app.run(debug=True)
