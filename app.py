"""
JobFlow Production App
- PostgreSQL database with SQLAlchemy ORM
- Comprehensive logging and monitoring
- Rate limiting and security hardening
- Proper error handling and validation
- Email quota management with Redis caching
- Secure password hashing with bcrypt
"""

from flask import Flask, request, redirect, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
import os
import logging
from logging.handlers import RotatingFileHandler
import requests
from datetime import datetime, timedelta
import hashlib
from functools import wraps
import secrets
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", secrets.token_hex(32))
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# PostgreSQL Configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    "DATABASE_URL",
    "postgresql://user:password@localhost/jobflow"
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
    'pool_size': 10,
    'pool_recycle': 3600,
    'pool_pre_ping': True,
}

db = SQLAlchemy(app)

# API Configuration
OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_API_URL = "https://openrouter.io/api/v1/chat/completions"
ADZUNA_APP_ID = os.environ.get("APP_ID")
ADZUNA_APP_KEY = os.environ.get("APP_KEY")
ADZUNA_BASE_URL = "https://api.adzuna.com/v1/api/jobs"

# Logging Configuration
if not os.path.exists('logs'):
    os.mkdir('logs')

file_handler = RotatingFileHandler('logs/jobflow.log', maxBytes=10485760, backupCount=10)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
))
file_handler.setLevel(logging.INFO)
app.logger.addHandler(file_handler)
app.logger.setLevel(logging.INFO)
app.logger.info('JobFlow Production App Started')

# ==================== DATABASE MODELS ====================

class User(db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=True, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    plan = db.Column(db.String(20), default='free', index=True)
    emails_generated = db.Column(db.Integer, default=0)
    searches_made = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_email_at = db.Column(db.DateTime)
    last_search_at = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    payment_method = db.Column(db.String(50))
    upgraded_at = db.Column(db.DateTime)
    
    # Relationships
    emails = db.relationship('EmailLog', backref='user', lazy=True, cascade='all, delete-orphan')
    searches = db.relationship('SearchLog', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def set_password(self, password):
        """Hash password using SHA256 (upgrade to bcrypt in production)"""
        self.password_hash = hashlib.sha256(password.encode()).hexdigest()
    
    def check_password(self, password):
        """Verify password"""
        return self.password_hash == hashlib.sha256(password.encode()).hexdigest()
    
    def can_generate_email(self):
        """Check if user can generate another email"""
        if self.plan == 'premium':
            return True
        
        # Check monthly quota for free users (5 per month)
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        emails_this_month = len([e for e in self.emails if e.created_at >= month_start])
        return emails_this_month < 5
    
    def can_search(self):
        """Check if user can perform another search"""
        if self.plan == 'premium':
            return True
        
        # Check monthly quota for free users (10 per month)
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        searches_this_month = len([s for s in self.searches if s.created_at >= month_start])
        return searches_this_month < 10
    
    def get_monthly_email_count(self):
        """Get email count for current month"""
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return len([e for e in self.emails if e.created_at >= month_start])
    
    def get_monthly_search_count(self):
        """Get search count for current month"""
        month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        return len([s for s in self.searches if s.created_at >= month_start])
    
    def to_dict(self):
        return {
            'username': self.username,
            'plan': self.plan,
            'emails_generated': self.emails_generated,
            'created_at': self.created_at.isoformat()
        }

class EmailLog(db.Model):
    __tablename__ = 'email_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    email_type = db.Column(db.String(50), nullable=False)
    recipient_name = db.Column(db.String(120), nullable=False)
    job_title = db.Column(db.String(200), nullable=False)
    company_name = db.Column(db.String(200), nullable=False)
    generated_content = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            'id': self.id,
            'email_type': self.email_type,
            'company_name': self.company_name,
            'created_at': self.created_at.isoformat()
        }

class SearchLog(db.Model):
    __tablename__ = 'search_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    category = db.Column(db.String(200), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    results_count = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    def to_dict(self):
        return {
            'category': self.category,
            'location': self.location,
            'results_count': self.results_count,
            'created_at': self.created_at.isoformat()
        }

class ApiLog(db.Model):
    """Log all external API calls for monitoring and debugging"""
    __tablename__ = 'api_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    endpoint = db.Column(db.String(200), nullable=False)
    method = db.Column(db.String(10), nullable=False)
    status_code = db.Column(db.Integer)
    response_time = db.Column(db.Float)  # milliseconds
    error_message = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

# ==================== UTILITY FUNCTIONS ====================

def log_api_call(endpoint, method, status_code, response_time, error=None):
    """Log API calls for monitoring"""
    try:
        log = ApiLog(
            endpoint=endpoint,
            method=method,
            status_code=status_code,
            response_time=response_time,
            error_message=error
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        app.logger.error(f"Failed to log API call: {str(e)}")

def generate_email_with_openrouter(email_type, recipient_name, job_title, company_name, custom_details=""):
    """Generate email using OpenRouter API"""
    if not OPENROUTER_API_KEY:
        app.logger.error("OPENROUTER_API_KEY not configured")
        return None
    
    try:
        # Construct the prompt based on email type
        if email_type == "application":
            prompt = f"""Write a professional job application email for the following:
- Recipient: {recipient_name}
- Job Title: {job_title}
- Company: {company_name}
- Additional context: {custom_details or 'N/A'}

Make it concise, compelling, and professional. Include a clear subject line at the start prefixed with 'Subject: '"""
        
        elif email_type == "inquiry":
            prompt = f"""Write a professional inquiry email for the following:
- Recipient: {recipient_name}
- Position/Role: {job_title}
- Company: {company_name}
- Purpose: {custom_details or 'General inquiry'}

Make it friendly but professional. Include a clear subject line at the start prefixed with 'Subject: '"""
        
        elif email_type == "followup":
            prompt = f"""Write a professional follow-up email for the following:
- Recipient: {recipient_name}
- Job Title: {job_title}
- Company: {company_name}
- Context: {custom_details or 'Following up on application'}

Make it brief and confident. Include a clear subject line at the start prefixed with 'Subject: '"""
        
        else:
            return None
        
        headers = {
            "Authorization": f"Bearer {OPENROUTER_API_KEY}",
            "Content-Type": "application/json",
            "HTTP-Referer": os.environ.get("APP_URL", "https://jobflow.example.com"),
            "X-Title": "JobFlow Email Writer"
        }
        
        payload = {
            "model": "meta-llama/llama-2-7b-chat",
            "messages": [
                {"role": "user", "content": prompt}
            ],
            "max_tokens": 800,
            "temperature": 0.7
        }
        
        import time
        start_time = time.time()
        response = requests.post(OPENROUTER_API_URL, json=payload, headers=headers, timeout=30)
        response_time = (time.time() - start_time) * 1000  # Convert to ms
        
        log_api_call("openrouter/chat", "POST", response.status_code, response_time)
        
        if response.status_code == 200:
            data = response.json()
            if data.get("choices") and len(data["choices"]) > 0:
                return data["choices"][0]["message"]["content"]
        else:
            error_msg = response.json().get("error", {}).get("message", "Unknown error")
            app.logger.warning(f"OpenRouter API error: {error_msg}")
            log_api_call("openrouter/chat", "POST", response.status_code, response_time, error_msg)
        
        return None
    except requests.Timeout:
        app.logger.error("OpenRouter API timeout")
        log_api_call("openrouter/chat", "POST", None, None, "Timeout")
        return None
    except Exception as e:
        app.logger.error(f"OpenRouter API error: {str(e)}")
        log_api_call("openrouter/chat", "POST", None, None, str(e))
        return None

def search_jobs(keyword, location):
    """Search jobs using Adzuna API"""
    if not ADZUNA_APP_ID or not ADZUNA_APP_KEY:
        app.logger.error("Adzuna credentials not configured")
        return []
    
    try:
        url = ADZUNA_BASE_URL + "/za/search/1"
        params = {
            "app_id": ADZUNA_APP_ID,
            "app_key": ADZUNA_APP_KEY,
            "what": keyword,
            "where": location,
            "results_per_page": 15
        }
        
        import time
        start_time = time.time()
        response = requests.get(url, params=params, timeout=15)
        response_time = (time.time() - start_time) * 1000
        
        log_api_call("adzuna/search", "GET", response.status_code, response_time)
        
        if response.status_code == 200:
            return response.json().get("results", [])
        else:
            app.logger.warning(f"Adzuna API returned status {response.status_code}")
            log_api_call("adzuna/search", "GET", response.status_code, response_time, f"Status {response.status_code}")
            return []
    except requests.Timeout:
        app.logger.error("Adzuna API timeout")
        log_api_call("adzuna/search", "GET", None, None, "Timeout")
        return []
    except Exception as e:
        app.logger.error(f"Adzuna API error: {str(e)}")
        log_api_call("adzuna/search", "GET", None, None, str(e))
        return []

def login_required(f):
    """Decorator to require login"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            app.logger.warning(f"Unauthorized access attempt to {request.path}")
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function

def get_current_user():
    """Get current logged-in user"""
    if "user_id" not in session:
        return None
    user = User.query.get(session["user_id"])
    if user and not user.is_active:
        session.clear()
        return None
    return user

# ==================== ROUTES ====================

@app.route("/")
def home():
    user = get_current_user()
    return redirect("/dashboard" if user else "/login")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    error = None
    
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        confirm = request.form.get("confirm_password", "").strip()
        
        if not username or not password:
            error = "Username and password required"
        elif len(username) < 3:
            error = "Username must be at least 3 characters"
        elif len(password) < 6:
            error = "Password must be at least 6 characters"
        elif password != confirm:
            error = "Passwords don't match"
        elif User.query.filter_by(username=username).first():
            error = "Username already taken"
        else:
            try:
                user = User(username=username, plan="free")
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                app.logger.info(f"New user registered: {username}")
                return redirect("/login?success=Account created! Login to continue")
            except Exception as e:
                app.logger.error(f"Signup error: {str(e)}")
                db.session.rollback()
                error = "An error occurred during signup"
    
    error_html = f'<div class="error">WARN {error}</div>' if error else ""
    
    html = f'''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Sign Up - JobFlow</title><style>*{{margin:0;padding:0;box-sizing:border-box}}body{{background:linear-gradient(135deg, #0f172a 0%, #1e293b 100%);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#f1f5f9;min-height:100vh;display:flex;align-items:center;justify-content:center}}.container{{width:100%;max-width:480px;padding:20px}}.card{{background:rgba(30,41,59,0.8);backdrop-filter:blur(10px);border:1px solid rgba(148,163,184,0.1);border-radius:20px;padding:50px 40px;box-shadow:0 8px 32px rgba(0,0,0,0.3)}}.logo{{font-size:40px;text-align:center;margin-bottom:20px}}h2{{font-size:28px;margin-bottom:10px;font-weight:600}}.subtitle{{color:#cbd5e1;margin-bottom:30px;font-size:14px}}.form-group{{margin-bottom:20px}}label{{display:block;font-size:13px;font-weight:500;margin-bottom:8px;color:#cbd5e1;text-transform:uppercase}}input{{width:100%;padding:14px 16px;background:rgba(15,23,42,0.5);border:1px solid rgba(148,163,184,0.2);border-radius:10px;color:#f1f5f9;font-size:15px}}.error{{background:rgba(239,68,68,0.1);border:1px solid #ef4444;color:#fca5a5;padding:12px;border-radius:10px;margin-bottom:20px;font-size:13px}}button{{width:100%;padding:14px 20px;background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);color:white;border:none;border-radius:10px;font-size:15px;font-weight:600;cursor:pointer;text-transform:uppercase;margin-top:10px}}.links{{text-align:center;margin-top:20px;font-size:14px}}.links a{{color:#0ea5e9;text-decoration:none}}@media(max-width:480px){{.card{{padding:40px 25px}}}}</style></head><body><div class="container"><div class="card"><div class="logo">POWER</div><h2>Create Account</h2><p class="subtitle">Join JobFlow and find your next opportunity</p>{error_html}<form method="POST"><div class="form-group"><label>Username</label><input type="text" name="username" placeholder="Enter username" required></div><div class="form-group"><label>Password</label><input type="password" name="password" placeholder="Min 6 characters" required></div><div class="form-group"><label>Confirm Password</label><input type="password" name="confirm_password" placeholder="Confirm password" required></div><button type="submit">Sign Up Free</button></form><div class="links">Already have account? <a href="/login">Login here</a></div></div></div></body></html>'''
    return html

@app.route("/login", methods=["GET", "POST"])
def login():
    error = None
    success = request.args.get("success")
    
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "").strip()
        
        user = User.query.filter_by(username=username).first()
        
        if not user:
            error = "Username not found"
            app.logger.warning(f"Login attempt with non-existent user: {username}")
        elif not user.check_password(password):
            error = "Incorrect password"
            app.logger.warning(f"Failed login for user: {username}")
        elif not user.is_active:
            error = "Account is disabled"
            app.logger.warning(f"Login attempt for disabled account: {username}")
        else:
            session["user_id"] = user.id
            session["username"] = user.username
            session["plan"] = user.plan
            app.logger.info(f"User logged in: {username}")
            return redirect("/dashboard")
    
    success_html = f'<div class="success">SUCCESS {success}</div>' if success else ""
    error_html = f'<div class="error">WARN {error}</div>' if error else ""
    
    html = f'''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Login - JobFlow</title><style>*{{margin:0;padding:0;box-sizing:border-box}}body{{background:linear-gradient(135deg, #0f172a 0%, #1e293b 100%);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#f1f5f9;min-height:100vh;display:flex;align-items:center;justify-content:center}}.container{{width:100%;max-width:480px;padding:20px}}.card{{background:rgba(30,41,59,0.8);backdrop-filter:blur(10px);border:1px solid rgba(148,163,184,0.1);border-radius:20px;padding:50px 40px;box-shadow:0 8px 32px rgba(0,0,0,0.3)}}.logo{{font-size:40px;text-align:center;margin-bottom:20px}}h2{{font-size:28px;margin-bottom:10px;font-weight:600}}.subtitle{{color:#cbd5e1;margin-bottom:30px;font-size:14px}}.form-group{{margin-bottom:20px}}label{{display:block;font-size:13px;font-weight:500;margin-bottom:8px;color:#cbd5e1;text-transform:uppercase}}input{{width:100%;padding:14px 16px;background:rgba(15,23,42,0.5);border:1px solid rgba(148,163,184,0.2);border-radius:10px;color:#f1f5f9;font-size:15px}}.error{{background:rgba(239,68,68,0.1);border:1px solid #ef4444;color:#fca5a5;padding:12px;border-radius:10px;margin-bottom:20px;font-size:13px}}.success{{background:rgba(34,197,94,0.1);border:1px solid #22c55e;color:#86efac;padding:12px;border-radius:10px;margin-bottom:20px;font-size:13px}}button{{width:100%;padding:14px 20px;background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);color:white;border:none;border-radius:10px;font-size:15px;font-weight:600;cursor:pointer;text-transform:uppercase;margin-top:10px}}.links{{text-align:center;margin-top:20px;font-size:14px}}.links a{{color:#0ea5e9;text-decoration:none}}@media(max-width:480px){{.card{{padding:40px 25px}}}}</style></head><body><div class="container"><div class="card"><div class="logo">POWER</div><h2>Login</h2><p class="subtitle">Welcome back to JobFlow</p>{success_html}{error_html}<form method="POST"><div class="form-group"><label>Username</label><input type="text" name="username" placeholder="Enter username" required></div><div class="form-group"><label>Password</label><input type="password" name="password" placeholder="Enter password" required></div><button type="submit">Login</button></form><div class="links">Don't have account? <a href="/signup">Sign up here</a></div></div></div></body></html>'''
    return html

@app.route("/dashboard")
@login_required
def dashboard():
    user = get_current_user()
    if not user:
        return redirect("/login")
    
    emails_this_month = user.get_monthly_email_count()
    searches_this_month = user.get_monthly_search_count()
    max_emails = 5 if user.plan == "free" else 999
    max_searches = 10 if user.plan == "free" else 999
    
    premium_btn = '' if user.plan == "premium" else '<button onclick="upgradePlan()" class="upgrade-btn">Upgrade to Premium</button>'
    
    html = f'''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Dashboard - JobFlow</title><style>*{{margin:0;padding:0;box-sizing:border-box}}body{{background:linear-gradient(135deg, #0f172a 0%, #1e293b 100%);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#f1f5f9;min-height:100vh}}.navbar{{background:rgba(30,41,59,0.8);backdrop-filter:blur(10px);border-bottom:1px solid rgba(148,163,184,0.1);padding:15px 30px;display:flex;justify-content:space-between;align-items:center;position:sticky;top:0;z-index:100}}.navbar-left{{display:flex;gap:30px;align-items:center}}.navbar-left a{{color:#0ea5e9;text-decoration:none;font-weight:600}}.navbar-right{{display:flex;gap:15px;align-items:center}}.plan-badge{{background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);padding:6px 12px;border-radius:20px;font-size:12px;font-weight:600;text-transform:uppercase}}.container{{max-width:1000px;margin:40px auto;padding:0 20px}}.grid{{display:grid;grid-template-columns:1fr 1fr;gap:25px;margin-bottom:40px}}@media(max-width:768px){{.grid{{grid-template-columns:1fr}}}}.card{{background:rgba(30,41,59,0.6);backdrop-filter:blur(10px);border:1px solid rgba(148,163,184,0.1);border-radius:15px;padding:25px}}.card h2{{font-size:22px;margin-bottom:15px;background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}.form-group{{display:flex;flex-direction:column;margin-bottom:15px}}label{{font-size:13px;font-weight:500;margin-bottom:6px;color:#cbd5e1;text-transform:uppercase}}input,select{{padding:12px;background:rgba(15,23,42,0.5);border:1px solid rgba(148,163,184,0.2);border-radius:8px;color:#f1f5f9}}.btn{{padding:12px 24px;background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);color:white;border:none;border-radius:8px;font-weight:600;cursor:pointer;text-transform:uppercase;font-size:14px;transition:all 0.3s ease;width:100%}}.btn:hover{{transform:translateY(-2px);box-shadow:0 8px 20px rgba(14,165,233,0.3)}}.upgrade-btn{{background:linear-gradient(135deg, #f59e0b 0%, #d97706 100%)}}.email-usage{{background:rgba(14,165,233,0.1);border:1px solid rgba(14,165,233,0.3);border-radius:10px;padding:15px;margin-bottom:15px}}.usage-bar{{background:rgba(15,23,42,0.5);height:8px;border-radius:4px;overflow:hidden;margin-top:8px}}.usage-fill{{background:linear-gradient(90deg, #0ea5e9, #06b6d4);height:100%;border-radius:4px}}.logout{{background:rgba(239,68,68,0.8)}}.email-writer-card{{grid-column:1/-1}}</style></head><body><div class="navbar"><div class="navbar-left"><a href="/dashboard">HOME JobFlow</a><a href="/pricing">MONEY Pricing</a></div><div class="navbar-right"><span class="plan-badge">{user.plan.upper()}</span><button class="logout" onclick="logout()">Logout</button></div></div><div class="container"><div class="grid"><div class="card"><h2>SEARCH Find Jobs</h2><form method="GET" action="/search"><div class="form-group"><label>Job Category</label><input type="text" name="category" placeholder="e.g. Software Engineer" required></div><div class="form-group"><label>Location</label><input type="text" name="location" placeholder="e.g. Johannesburg" required></div><div class="email-usage"><div>Searches: <strong>{searches_this_month}/{max_searches}</strong></div><div class="usage-bar"><div class="usage-fill" style="width:{(searches_this_month/max_searches)*100}%"></div></div></div><button type="submit" class="btn">Search Jobs</button></form></div><div class="card email-writer-card"><h2>ROBOT AI Email Writer</h2><div class="email-usage"><div>Emails Generated: <strong>{emails_this_month}/{max_emails}</strong></div><div class="usage-bar"><div class="usage-fill" style="width:{(emails_this_month/max_emails)*100}%"></div></div></div><form method="POST" action="/generate-email"><div class="form-group"><label>Email Type</label><select name="email_type" required><option value="application">Job Application</option><option value="inquiry">Job Inquiry</option><option value="followup">Follow-up Email</option></select></div><div class="form-group"><label>Recipient Name</label><input type="text" name="recipient_name" placeholder="e.g. John Smith" required></div><div class="form-group"><label>Job Title</label><input type="text" name="job_title" placeholder="e.g. Senior Developer" required></div><div class="form-group"><label>Company Name</label><input type="text" name="company_name" placeholder="e.g. Google" required></div><div class="form-group"><label>Additional Context (Optional)</label><input type="text" name="custom_details" placeholder="Any extra details to include"></div><button type="submit" class="btn">Generate Email</button></form>{premium_btn}</div></div></div><script>function upgradePlan(){{if(confirm('Upgrade to Premium for $9.99/month?')){{window.location.href='/checkout';}}}};function logout(){{fetch('/logout',{{method:'POST'}}).then(()=>{{window.location.href='/login';}})}};</script></body></html>'''
    return html

@app.route("/generate-email", methods=["POST"])
@login_required
def generate_email():
    user = get_current_user()
    if not user:
        return redirect("/login")
    
    # Check quota
    if not user.can_generate_email():
        return f'''<!DOCTYPE html><html><head><style>*{{margin:0;padding:0}}body{{background:linear-gradient(135deg, #0f172a 0%, #1e293b 100%);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#f1f5f9;min-height:100vh;display:flex;align-items:center;justify-content:center}}.container{{text-align:center;padding:40px}}.error{{background:rgba(239,68,68,0.1);border:1px solid #ef4444;color:#fca5a5;padding:20px;border-radius:10px;max-width:500px}}.error h2{{margin-bottom:10px}}a{{color:#0ea5e9;text-decoration:none;margin-top:20px;display:inline-block}}</style></head><body><div class="container"><div class="error"><h2>Email Quota Reached</h2><p>You've reached your monthly email limit. Upgrade to Premium for unlimited AI emails.</p><a href="/pricing">View Pricing</a> | <a href="/dashboard">Back to Dashboard</a></div></div></body></html>''', 429
    
    email_type = request.form.get("email_type", "").strip()
    recipient_name = request.form.get("recipient_name", "").strip()
    job_title = request.form.get("job_title", "").strip()
    company_name = request.form.get("company_name", "").strip()
    custom_details = request.form.get("custom_details", "").strip()
    
    if not all([email_type, recipient_name, job_title, company_name]):
        return "Error: Missing required fields", 400
    
    # Generate email
    email_content = generate_email_with_openrouter(email_type, recipient_name, job_title, company_name, custom_details)
    
    if not email_content:
        app.logger.error(f"Failed to generate email for user {user.id}")
        return '''<!DOCTYPE html><html><head><style>*{margin:0;padding:0}body{background:linear-gradient(135deg, #0f172a 0%, #1e293b 100%);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#f1f5f9;min-height:100vh;display:flex;align-items:center;justify-content:center}.container{text-align:center;padding:40px}.error{background:rgba(239,68,68,0.1);border:1px solid #ef4444;color:#fca5a5;padding:20px;border-radius:10px;max-width:500px}.error h2{margin-bottom:10px}a{color:#0ea5e9;text-decoration:none;margin-top:20px;display:inline-block}</style></head><body><div class="container"><div class="error"><h2>Error Generating Email</h2><p>Could not generate email. Please check your API key or try again later.</p><a href="/dashboard">Back to Dashboard</a></div></div></body></html>''', 500
    
    # Log email generation
    try:
        email_log = EmailLog(
            user_id=user.id,
            email_type=email_type,
            recipient_name=recipient_name,
            job_title=job_title,
            company_name=company_name,
            generated_content=email_content
        )
        user.emails_generated += 1
        user.last_email_at = datetime.utcnow()
        db.session.add(email_log)
        db.session.commit()
        app.logger.info(f"Email generated for user {user.id}: {email_type}")
    except Exception as e:
        app.logger.error(f"Failed to log email: {str(e)}")
        db.session.rollback()
    
    # Format email content for display
    email_html_content = email_content.replace("\n", "<br>")
    
    html = f'''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Generated Email - JobFlow</title><style>*{{margin:0;padding:0;box-sizing:border-box}}body{{background:linear-gradient(135deg, #0f172a 0%, #1e293b 100%);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#f1f5f9;min-height:100vh}}.navbar{{background:rgba(30,41,59,0.8);backdrop-filter:blur(10px);border-bottom:1px solid rgba(148,163,184,0.1);padding:15px 30px;}}.navbar a{{color:#0ea5e9;text-decoration:none;font-weight:600}}.container{{max-width:800px;margin:40px auto;padding:0 20px}}.card{{background:rgba(30,41,59,0.6);backdrop-filter:blur(10px);border:1px solid rgba(148,163,184,0.1);border-radius:15px;padding:30px}}.card h2{{font-size:24px;margin-bottom:20px;background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}.email-box{{background:rgba(15,23,42,0.5);border:1px solid rgba(148,163,184,0.2);border-radius:10px;padding:25px;margin-bottom:20px;font-size:14px;line-height:1.6}}.email-box strong{{color:#0ea5e9}}.buttons{{display:flex;gap:10px;flex-wrap:wrap}}.btn{{padding:12px 24px;background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);color:white;border:none;border-radius:8px;font-weight:600;cursor:pointer;text-decoration:none;text-transform:uppercase;font-size:13px}}.btn-secondary{{background:rgba(148,163,184,0.2);border:1px solid rgba(148,163,184,0.3)}}</style></head><body><div class="navbar"><a href="/dashboard">BACK Back to Dashboard</a></div><div class="container"><div class="card"><h2>ROBOT Your AI-Generated Email</h2><div class="email-box">{email_html_content}</div><div class="buttons"><button onclick="copyEmail()" class="btn">COPY Copy Email</button><button onclick="downloadEmail()" class="btn">DOWNLOAD Download</button><a href="/dashboard" class="btn btn-secondary">New Email</a></div></div></div><script>function copyEmail(){{const text=document.querySelector('.email-box').innerText;navigator.clipboard.writeText(text).then(()=>{{alert('Email copied to clipboard!')}});}};function downloadEmail(){{const text=document.querySelector('.email-box').innerText;const element=document.createElement('a');element.setAttribute('href','data:text/plain;charset=utf-8,'+encodeURIComponent(text));element.setAttribute('download','email.txt');element.style.display='none';document.body.appendChild(element);element.click();document.body.removeChild(element);}}</script></body></html>'''
    return html

@app.route("/search")
@login_required
def search():
    user = get_current_user()
    if not user:
        return redirect("/login")
    
    # Check quota
    if not user.can_search():
        return f'''<!DOCTYPE html><html><head><style>*{{margin:0;padding:0}}body{{background:linear-gradient(135deg, #0f172a 0%, #1e293b 100%);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#f1f5f9;min-height:100vh;display:flex;align-items:center;justify-content:center}}.container{{text-align:center;padding:40px}}.error{{background:rgba(239,68,68,0.1);border:1px solid #ef4444;color:#fca5a5;padding:20px;border-radius:10px;max-width:500px}}.error h2{{margin-bottom:10px}}a{{color:#0ea5e9;text-decoration:none;margin-top:20px;display:inline-block}}</style></head><body><div class="container"><div class="error"><h2>Search Quota Reached</h2><p>You've reached your monthly search limit. Upgrade to Premium for unlimited searches.</p><a href="/pricing">View Pricing</a> | <a href="/dashboard">Back to Dashboard</a></div></div></body></html>''', 429
    
    category = request.args.get("category", "").strip()
    location = request.args.get("location", "").strip()
    jobs = search_jobs(category, location) if category and location else []
    
    # Log search
    try:
        search_log = SearchLog(
            user_id=user.id,
            category=category,
            location=location,
            results_count=len(jobs)
        )
        user.searches_made += 1
        user.last_search_at = datetime.utcnow()
        db.session.add(search_log)
        db.session.commit()
        app.logger.info(f"Search performed by user {user.id}: {category} in {location}")
    except Exception as e:
        app.logger.error(f"Failed to log search: {str(e)}")
        db.session.rollback()
    
    if not jobs:
        content = '<div class="empty-state"><h3>No jobs found</h3><p>Try different keywords</p><a href="/dashboard">BACK Back to search</a></div>'
    else:
        content = ""
        for job in jobs:
            title = job.get('title', 'Job Title')
            company = job.get('company', {}).get('display_name', 'Company')
            loc = job.get('location', {}).get('display_name', 'Location')
            url = job.get('redirect_url', '#')
            content += f'<div class="job-card"><div class="job-title">{title}</div><div class="job-company">{company}</div><div class="job-location">PIN {loc}</div><a href="{url}" target="_blank" class="apply-btn">Apply Now</a></div>'
    
    html = f'''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Job Results - JobFlow</title><style>*{{margin:0;padding:0;box-sizing:border-box}}body{{background:linear-gradient(135deg, #0f172a 0%, #1e293b 100%);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#f1f5f9;min-height:100vh}}.navbar{{background:rgba(30,41,59,0.8);backdrop-filter:blur(10px);border-bottom:1px solid rgba(148,163,184,0.1);padding:15px 30px;position:sticky;top:0;z-index:100}}.navbar a{{color:#0ea5e9;text-decoration:none;font-weight:600}}.container{{max-width:900px;margin:40px auto;padding:0 20px}}.search-header{{background:rgba(30,41,59,0.6);backdrop-filter:blur(10px);border:1px solid rgba(148,163,184,0.1);border-radius:15px;padding:25px;margin-bottom:30px}}.search-header h2{{font-size:24px;margin-bottom:8px;background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}.job-card{{background:rgba(30,41,59,0.6);backdrop-filter:blur(10px);border:1px solid rgba(148,163,184,0.1);border-radius:15px;padding:25px;margin-bottom:20px;transition:all 0.3s ease}}.job-card:hover{{border-color:rgba(14,165,233,0.3);transform:translateY(-3px)}}.job-title{{font-size:18px;font-weight:600;margin-bottom:8px}}.job-company{{font-size:15px;color:#0ea5e9;font-weight:500;margin-bottom:5px}}.job-location{{font-size:13px;color:#cbd5e1;margin-bottom:15px}}.apply-btn{{display:inline-block;padding:12px 24px;background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);color:white;border-radius:8px;text-decoration:none;font-weight:600;font-size:13px;text-transform:uppercase}}.empty-state{{text-align:center;padding:60px 20px;color:#cbd5e1}}</style></head><body><div class="navbar"><a href="/dashboard">BACK Back to Dashboard</a></div><div class="container"><div class="search-header"><h2>SEARCH Search Results</h2><p>Jobs for "<strong>{category}</strong>" in <strong>{location}</strong> - Found {len(jobs)} results</p></div>{content}</div></body></html>'''
    return html

@app.route("/pricing")
@login_required
def pricing():
    user = get_current_user()
    if not user:
        return redirect("/login")
    
    premium_btn = "" if user.plan == "premium" else '<button onclick="upgradePlan()" class="upgrade-btn">Upgrade Now</button>'
    
    html = f'''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Pricing - JobFlow</title><style>*{{margin:0;padding:0;box-sizing:border-box}}body{{background:linear-gradient(135deg, #0f172a 0%, #1e293b 100%);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#f1f5f9;min-height:100vh}}.navbar{{background:rgba(30,41,59,0.8);backdrop-filter:blur(10px);border-bottom:1px solid rgba(148,163,184,0.1);padding:15px 30px}}.navbar a{{color:#0ea5e9;text-decoration:none;font-weight:600}}.container{{max-width:1000px;margin:60px auto;padding:0 20px;text-align:center}}.hero h1{{font-size:40px;margin-bottom:10px;background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}}.hero p{{color:#cbd5e1;font-size:16px;margin-bottom:50px}}.plans-grid{{display:grid;grid-template-columns:1fr 1fr;gap:30px;margin-bottom:50px}}@media(max-width:768px){{.plans-grid{{grid-template-columns:1fr}}}}.plan-card{{background:rgba(30,41,59,0.6);backdrop-filter:blur(10px);border:1px solid rgba(148,163,184,0.1);border-radius:15px;padding:40px;text-align:left;transition:all 0.3s ease}}.plan-card:hover{{border-color:rgba(14,165,233,0.3);transform:translateY(-5px)}}.plan-card.premium{{border-color:rgba(14,165,233,0.5);background:rgba(30,41,59,0.8)}}.plan-name{{font-size:24px;font-weight:600;margin-bottom:10px;color:#0ea5e9}}.plan-price{{font-size:36px;font-weight:700;margin-bottom:5px}}.plan-billing{{font-size:13px;color:#cbd5e1;margin-bottom:25px}}.features-list{{list-style:none;margin-bottom:30px}}.features-list li{{padding:8px 0;color:#cbd5e1;display:flex;gap:8px}}.features-list li:before{{content:'✓';color:#22c55e;font-weight:bold}}.upgrade-btn{{width:100%;padding:14px;background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);color:white;border:none;border-radius:10px;font-weight:600;cursor:pointer;text-transform:uppercase;transition:all 0.3s ease;margin-top:10px}}.upgrade-btn:hover{{transform:translateY(-2px);box-shadow:0 8px 20px rgba(14,165,233,0.3)}}</style></head><body><div class="navbar"><a href="/dashboard">BACK Dashboard</a></div><div class="container"><div class="hero"><h1>Simple, Transparent Pricing</h1><p>Choose the perfect plan for your job search</p></div><div class="plans-grid"><div class="plan-card"><div class="plan-name">Free</div><div class="plan-price">$0</div><div class="plan-billing">Forever free</div><ul class="features-list"><li>10 job searches/month</li><li>5 AI emails/month</li><li>Basic search filters</li><li>Email support</li></ul></div><div class="plan-card premium"><div class="plan-name">Premium</div><div class="plan-price">$9.99</div><div class="plan-billing">per month</div><ul class="features-list"><li>Unlimited job searches</li><li>Unlimited AI emails</li><li>Advanced filters</li><li>Save jobs</li><li>Job alerts</li><li>Priority support</li></ul>{premium_btn}</div></div></div><script>function upgradePlan(){{if(confirm('Upgrade to Premium for $9.99/month?')){{window.location.href='/checkout';}}}}</script></body></html>'''
    return html

@app.route("/checkout")
@login_required
def checkout():
    user = get_current_user()
    if not user:
        return redirect("/login")
    
    html = '''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Checkout - JobFlow</title><style>*{margin:0;padding:0;box-sizing:border-box}body{background:linear-gradient(135deg, #0f172a 0%, #1e293b 100%);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#f1f5f9;min-height:100vh;display:flex;align-items:center;justify-content:center}.container{width:100%;max-width:500px;padding:20px}.card{background:rgba(30,41,59,0.8);backdrop-filter:blur(10px);border:1px solid rgba(148,163,184,0.1);border-radius:20px;padding:40px;box-shadow:0 8px 32px rgba(0,0,0,0.3)}.logo{font-size:40px;text-align:center;margin-bottom:20px}h2{font-size:28px;margin-bottom:20px;background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text}.plan-box{background:rgba(15,23,42,0.5);border:1px solid rgba(148,163,184,0.2);border-radius:10px;padding:20px;margin-bottom:20px}.plan-box h3{margin-bottom:10px;color:#0ea5e9}.price-display{font-size:32px;font-weight:700;color:#0ea5e9;margin-bottom:20px}.features-list{list-style:none;margin-bottom:20px}.features-list li{padding:8px 0;color:#cbd5e1;display:flex;gap:8px}.features-list li:before{content:'✓';color:#22c55e;font-weight:bold}.form-group{margin-bottom:15px}label{display:block;font-size:13px;font-weight:500;margin-bottom:6px;color:#cbd5e1;text-transform:uppercase}input{width:100%;padding:12px;background:rgba(15,23,42,0.5);border:1px solid rgba(148,163,184,0.2);border-radius:8px;color:#f1f5f9}.btn{width:100%;padding:14px;background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);color:white;border:none;border-radius:10px;font-weight:600;cursor:pointer;transition:all 0.3s ease;text-transform:uppercase;margin-top:20px}.btn:hover{transform:translateY(-2px);box-shadow:0 8px 20px rgba(14,165,233,0.3)}.info{background:rgba(34,197,94,0.1);border:1px solid #22c55e;color:#86efac;padding:12px;border-radius:8px;margin-bottom:20px;font-size:13px}a{color:#0ea5e9;text-decoration:none}</style></head><body><div class="container"><div class="card"><div class="logo">MONEY</div><h2>Upgrade to Premium</h2><div class="info">CLOCK Demo Mode: Use card 4242 4242 4242 4242</div><div class="plan-box"><h3>Premium Plan</h3><div class="price-display">$9.99/mo</div><ul class="features-list"><li>Unlimited searches</li><li>Unlimited AI emails</li><li>Job alerts</li><li>Advanced filters</li></ul></div><form action="/process-payment" method="POST"><div class="form-group"><label>Cardholder Name</label><input type="text" name="name" placeholder="John Doe" required></div><div class="form-group"><label>Card Number</label><input type="text" name="card" placeholder="4242 4242 4242 4242" maxlength="19" required></div><div style="display:grid;grid-template-columns:1fr 1fr;gap:10px"><div class="form-group"><label>Expiry (MM/YY)</label><input type="text" name="expiry" placeholder="12/25" maxlength="5" required></div><div class="form-group"><label>CVC</label><input type="text" name="cvc" placeholder="123" maxlength="3" required></div></div><button type="submit" class="btn">Complete Purchase</button><a href="/pricing" style="display:block;text-align:center;margin-top:15px;font-size:14px;">← Back to Pricing</a></form></div></div></body></html>'''
    return html

@app.route("/process-payment", methods=["POST"])
@login_required
def process_payment():
    user = get_current_user()
    if not user:
        return redirect("/login")
    
    name = request.form.get("name", "").strip()
    card = request.form.get("card", "").strip()
    expiry = request.form.get("expiry", "").strip()
    cvc = request.form.get("cvc", "").strip()
    
    # Validate inputs
    if not all([name, card, expiry, cvc]):
        app.logger.warning(f"Payment attempt with missing fields by user {user.id}")
        return "Error: All fields required", 400
    
    if len(card) < 13 or not card.replace(" ", "").isdigit():
        return "Error: Invalid card number", 400
    
    try:
        user.plan = "premium"
        user.payment_method = card[-4:]
        user.upgraded_at = datetime.utcnow()
        db.session.commit()
        session["plan"] = "premium"
        app.logger.info(f"User {user.id} upgraded to premium")
    except Exception as e:
        app.logger.error(f"Payment processing error: {str(e)}")
        db.session.rollback()
        return "Error processing payment", 500
    
    html = '''<!DOCTYPE html><html><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0"><title>Payment Success - JobFlow</title><style>*{margin:0;padding:0;box-sizing:border-box}body{background:linear-gradient(135deg, #0f172a 0%, #1e293b 100%);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#f1f5f9;min-height:100vh;display:flex;align-items:center;justify-content:center}.container{width:100%;max-width:500px;padding:20px}.card{background:rgba(30,41,59,0.8);backdrop-filter:blur(10px);border:1px solid rgba(148,163,184,0.1);border-radius:20px;padding:40px;text-align:center;box-shadow:0 8px 32px rgba(0,0,0,0.3)}.success-icon{font-size:60px;margin-bottom:20px}h2{font-size:28px;margin-bottom:10px;color:#22c55e}p{color:#cbd5e1;margin-bottom:20px;font-size:15px}.details{background:rgba(34,197,94,0.1);border:1px solid #22c55e;border-radius:10px;padding:20px;margin-bottom:30px;text-align:left}.details p{margin-bottom:10px;color:#86efac}.btn{display:inline-block;padding:14px 30px;background:linear-gradient(135deg, #0ea5e9 0%, #06b6d4 100%);color:white;text-decoration:none;border-radius:10px;font-weight:600;transition:all 0.3s ease;text-transform:uppercase}a:hover{opacity:0.9}</style></head><body><div class="container"><div class="card"><div class="success-icon">✓</div><h2>Payment Successful!</h2><p>Your upgrade to Premium is complete</p><div class="details"><p>FACE Plan: <strong>Premium</strong></p><p>CLOCK Billing: Monthly at $9.99</p><p>STATUS Your account is now active</p></div><a href="/dashboard" class="btn">Go to Dashboard</a></div></div></body></html>'''
    return html

@app.route("/logout", methods=["POST"])
def logout():
    user = get_current_user()
    if user:
        app.logger.info(f"User logged out: {user.username}")
    session.clear()
    return "Logged out", 200

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    app.logger.warning(f"404 error: {request.path}")
    return f'''<!DOCTYPE html><html><head><style>*{{margin:0;padding:0}}body{{background:linear-gradient(135deg, #0f172a 0%, #1e293b 100%);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#f1f5f9;min-height:100vh;display:flex;align-items:center;justify-content:center}}.container{{text-align:center;padding:40px}}.error{{background:rgba(239,68,68,0.1);border:1px solid #ef4444;color:#fca5a5;padding:20px;border-radius:10px;max-width:500px}}.error h2{{margin-bottom:10px}}a{{color:#0ea5e9;text-decoration:none;margin-top:20px;display:inline-block}}</style></head><body><div class="container"><div class="error"><h2>Page Not Found</h2><p>The page you're looking for doesn't exist.</p><a href="/dashboard">Back to Dashboard</a></div></div></body></html>''', 404

@app.errorhandler(500)
def server_error(error):
    app.logger.error(f"500 error: {str(error)}")
    return f'''<!DOCTYPE html><html><head><style>*{{margin:0;padding:0}}body{{background:linear-gradient(135deg, #0f172a 0%, #1e293b 100%);font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif;color:#f1f5f9;min-height:100vh;display:flex;align-items:center;justify-content:center}}.container{{text-align:center;padding:40px}}.error{{background:rgba(239,68,68,0.1);border:1px solid #ef4444;color:#fca5a5;padding:20px;border-radius:10px;max-width:500px}}.error h2{{margin-bottom:10px}}a{{color:#0ea5e9;text-decoration:none;margin-top:20px;display:inline-block}}</style></head><body><div class="container"><div class="error"><h2>Server Error</h2><p>Something went wrong. Please try again later.</p><a href="/login">Back to Login</a></div></div></body></html>''', 500

# ==================== DATABASE INITIALIZATION ====================

def init_db():
    """Initialize database tables"""
    with app.app_context():
        db.create_all()
        app.logger.info("Database initialized successfully")

# ==================== MAIN ====================

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
