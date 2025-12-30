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
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

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

    # Load and Clean Config
    smtp_server = (os.getenv("MAIL_SERVER") or "").strip()
    try:
        smtp_port = int(os.getenv("MAIL_PORT", 587))
    except ValueError:
        smtp_port = 587
    smtp_user = (os.getenv("MAIL_USERNAME") or "").strip()
    smtp_pass = (os.getenv("MAIL_PASSWORD") or "").strip()

    if not smtp_server or not smtp_user or not smtp_pass:
            error_msg = f"SMTP Config Missing. Server: '{smtp_server}', User: '{smtp_user}'"
            print(f"ERROR: {error_msg}")
            return jsonify({"error": "Server configuration error", "debug": error_msg}), 500

    log = EmailLog(recipient=recipient, subject=subject, api_key_id=api_key.id, status="pending")

    try:
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = smtp_user
        msg['To'] = recipient
        msg['Subject'] = subject
        
        if body_text:
            msg.attach(MIMEText(body_text, 'plain'))
        if body_html:
            msg.attach(MIMEText(body_html, 'html'))

        # Send email
        print(f"DEBUG: Connecting to SMTP {smtp_server}:{smtp_port} as {smtp_user}") 
        
        server = None
        try:
            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_server, smtp_port)
                server.ehlo()
            else:
                server = smtplib.SMTP(smtp_server, smtp_port)
                server.ehlo()
                server.starttls()
                server.ehlo()
            
            server.login(smtp_user, smtp_pass)
            text = msg.as_string()
            server.sendmail(smtp_user, recipient, text)
            
        except Exception as smtp_err:
             print(f"SMTP Error: {smtp_err}")
             # Specific helpful message for PA users
             if "Network is unreachable" in str(smtp_err) or "Errno 101" in str(smtp_err):
                 raise Exception("Network Unreachable. On PythonAnywhere Free Tier? You can ONLY use 'smtp.gmail.com' on port 587 or 465. Other servers are blocked.")
             raise smtp_err
        finally:
             try:
                 if server:
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
        # Return helpful debug info (remove in production later)
        return jsonify({
            "error": str(e), 
            "debug": f"Failed to connect to {smtp_server}:{smtp_port}"
        }), 500

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
