import os
import smtplib
from functools import wraps
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, request, jsonify, render_template, redirect, url_for, flash
from flask_cors import CORS
from dotenv import load_dotenv
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from models import db, ApiKey, EmailLog, User

# Load environment variables
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "supersecretkey") # Change this in production
CORS(app)

# Database Config
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///relaymail.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)

# Login Manager
login_manager = LoginManager()
login_manager.login_view = 'login'
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Configuration
SMTP_SERVER = os.getenv("MAIL_SERVER")
SMTP_PORT = int(os.getenv("MAIL_PORT", 587))
SMTP_USERNAME = os.getenv("MAIL_USERNAME")
SMTP_PASSWORD = os.getenv("MAIL_PASSWORD")

# Create DB tables
with app.app_context():
    db.create_all()

# Authentication Decorator (for API)
def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({"error": "Missing or invalid API Key"}), 401
        
        token = auth_header.split(" ")[1]
        api_key = ApiKey.query.filter_by(key=token, is_active=True).first()
        
        if not api_key:
            return jsonify({"error": "Invalid API Key"}), 401
            
        return f(api_key, *args, **kwargs)
    return decorated_function

# --- Auth Routes ---
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered')
            return redirect(url_for('signup'))
        
        new_user = User(email=email)
        new_user.set_password(password)
        db.session.add(new_user)
        db.session.commit()
        
        login_user(new_user)
        return redirect(url_for('dashboard')) # Redirect to Dashboard
    return render_template('signup.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('dashboard')) # Redirect to Dashboard
        flash('Invalid email or password')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('landing'))

# --- Sending API ---
@app.route('/api/v1/send', methods=['POST'])
@require_api_key
def send_email(api_key):
    data = request.get_json()
    
    # Validation
    if not data or not all(k in data for k in ("to", "subject")):
        return jsonify({"error": "Missing required fields: 'to', 'subject'"}), 400

    recipient = data["to"]
    subject = data["subject"]
    
    # Check for body or html
    body_text = data.get("body")
    body_html = data.get("html")
    
    if not body_text and not body_html:
        return jsonify({"error": "Missing email content. Provide 'body' (text) or 'html'."}), 400

    log = EmailLog(recipient=recipient, subject=subject, api_key_id=api_key.id, status="pending")

    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = SMTP_USERNAME
        msg['To'] = recipient
        msg['Subject'] = subject
        
        if body_text:
            msg.attach(MIMEText(body_text, 'plain'))
        if body_html:
            msg.attach(MIMEText(body_html, 'html'))

        # Send email
        # Send email
        print(f"DEBUG: Connecting to SMTP {SMTP_SERVER}:{SMTP_PORT} as {SMTP_USERNAME}") # User log for PA
        
        server = smtplib.SMTP()
        # server.set_debuglevel(1) # Optional: enable for deep debugging
        
        try:
            server.connect(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            text = msg.as_string()
            server.sendmail(SMTP_USERNAME, recipient, text)
        except Exception as smtp_err:
             print(f"SMTP Error: {smtp_err}")
             raise smtp_err
        finally:
             try:
                 server.quit()
             except:
                 pass
        
        log.status = "sent"
        db.session.add(log)
        db.session.commit()

        return jsonify({"id": log.id, "message": "Email sent successfully"}), 200

    except Exception as e:
        log.status = "failed"
        log.error_message = str(e)
        db.session.add(log)
        db.session.commit()
        return jsonify({"error": str(e)}), 500

# --- Dashboard API ---
@app.route('/api/v1/keys', methods=['GET', 'POST'])
@login_required
def manage_keys():
    if request.method == 'POST':
        data = request.get_json() or {}
        name = data.get('name', f"Key {datetime.utcnow().strftime('%Y-%m-%d %H:%M')}")
        new_key = ApiKey(name=name, user_id=current_user.id)
        db.session.add(new_key)
        db.session.commit()
        return jsonify({"id": new_key.id, "name": new_key.name, "key": new_key.key, "created": new_key.created_at}), 201
    else:
        keys = ApiKey.query.filter_by(user_id=current_user.id, is_active=True).all()
    # logic: key_token is not stored plainly, only prefix if we had it. 
    # We will just show a masked version based on what we have.
    
    # Helper to get last used
    def get_last_used(k_id):
        last_log = EmailLog.query.filter_by(api_key_id=k_id).order_by(EmailLog.timestamp.desc()).first()
        return last_log.timestamp.isoformat() if last_log else None

    return jsonify([{
        "id": k.id,
        "name": k.name,
        "key_token": f"rk_live_{k.key[:4]}..." if k.key else "rk_live_...",
        "created_at": k.created_at.isoformat() if k.created_at else datetime.utcnow().isoformat(),
        "last_used": get_last_used(k.id)
    } for k in keys])

@app.route('/api/v1/keys/<int:key_id>', methods=['DELETE'])
@login_required
def revoke_key(key_id):
    key = ApiKey.query.filter_by(id=key_id, user_id=current_user.id).first()
    if not key:
        return jsonify({"error": "Key not found"}), 404
    key.is_active = False
    db.session.commit()
    return jsonify({"message": "Key revoked"}), 200

@app.route('/api/v1/emails', methods=['GET'])
@login_required
def get_emails():
    # Join ApiKey to filter by current user
    logs = EmailLog.query.join(ApiKey).filter(ApiKey.user_id == current_user.id).order_by(EmailLog.timestamp.desc()).limit(100).all()
    return jsonify([{
        "id": l.id,
        "recipient": l.recipient,
        "subject": l.subject,
        "status": l.status,
        "timestamp": l.timestamp,
        "key_name": l.api_key.name
    } for l in logs])

@app.route('/api/v1/metrics', methods=['GET'])
@login_required
def get_metrics():
    # Filter by user
    base_query = EmailLog.query.join(ApiKey).filter(ApiKey.user_id == current_user.id)
    total = base_query.count()
    sent = base_query.filter(EmailLog.status == 'sent').count()
    failed = base_query.filter(EmailLog.status == 'failed').count()
    success_rate = round((sent / total * 100), 1) if total > 0 else 0
    
    active_keys = ApiKey.query.filter_by(user_id=current_user.id, is_active=True).count()

    return jsonify({
        "total": total,
        "sent": sent,
        "failed": failed,
        "rate": success_rate,
        "active_keys": active_keys
    })

# --- Routes ---
@app.route('/')
def landing():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return render_template('landing.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/keys')
@login_required
def keys_page():
    return render_template('api_keys.html')

if __name__ == '__main__':
    app.run(debug=True, port=int(os.getenv("PORT", 5001)))
