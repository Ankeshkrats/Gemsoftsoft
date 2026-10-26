"""
app.py — Indian Gemological Institute
Gemstone Testing & Certification System
Flask backend with SQLite, Ed25519 digital-signature QR codes, and image handling.
"""

import base64
import hashlib
import json
import os
import random
import sqlite3
import string
from datetime import datetime
from functools import wraps

from flask import (
    Flask, g, flash, jsonify, redirect,
    render_template, request, session, url_for, send_file
)
from io import BytesIO
import card_pdf
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from PIL import Image
import qrcode
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey, Ed25519PublicKey
)
from cryptography.hazmat.primitives.serialization import (
    Encoding, PublicFormat, PrivateFormat, NoEncryption,
    load_pem_private_key, load_pem_public_key
)
from cryptography.exceptions import InvalidSignature
from flask_wtf import CSRFProtect

# ── App Config ──────────────────────────────────────────────────────────────
BASE_DIR       = os.path.dirname(os.path.abspath(__file__))
DATABASE       = os.path.join(BASE_DIR, 'database.db')
UPLOAD_FOLDER  = os.path.join(BASE_DIR, 'static', 'uploads')
QR_FOLDER      = os.path.join(UPLOAD_FOLDER, 'qrcodes')
KEY_DIR        = os.path.join(BASE_DIR, 'keys')
PRIVATE_KEY_PATH = os.path.join(KEY_DIR, 'signing_key.pem')
PUBLIC_KEY_PATH  = os.path.join(KEY_DIR, 'verify_key.pem')
ALLOWED_EXTS   = {'jpg', 'jpeg', 'png', 'webp'}
MAX_IMG_SIZE   = 10 * 1024 * 1024   # 10 MB

# Institute identity — single place to change
INSTITUTE_NAME    = "Indian Gemological Institute"
INSTITUTE_ABBR    = "IGI"
INSTITUTE_WEBSITE = "indiangemological.com"
INSTITUTE_EMAIL   = "info@indiangemological.com"
INSTITUTE_ADDRESS = "Gemological Testing & Certification Laboratory"
QR_SCHEMA_VERSION = "IGI-v1"
SIGNING_KEY_ID    = "IGI-Ed25519-2026"

# Load environment variables
from dotenv import load_dotenv
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'dev-secret')
# Initialize CSRF protection
csrf = CSRFProtect(app)

app.config['MAX_CONTENT_LENGTH'] = MAX_IMG_SIZE

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(QR_FOLDER, exist_ok=True)
os.makedirs(KEY_DIR, exist_ok=True)


# ── Ed25519 Key Management ─────────────────────────────────────────────────
def _generate_and_save_keys():
    """Generate Ed25519 keypair and persist to keys/ directory."""
    private_key = Ed25519PrivateKey.generate()
    priv_pem = private_key.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
    pub_pem  = private_key.public_key().public_bytes(Encoding.PEM, PublicFormat.SubjectPublicKeyInfo)
    with open(PRIVATE_KEY_PATH, 'wb') as f:
        f.write(priv_pem)
    with open(PUBLIC_KEY_PATH, 'wb') as f:
        f.write(pub_pem)
    return private_key, private_key.public_key()

def load_signing_keys():
    """Load or generate Ed25519 keypair. Returns (private_key, public_key)."""
    if os.path.exists(PRIVATE_KEY_PATH) and os.path.exists(PUBLIC_KEY_PATH):
        try:
            with open(PRIVATE_KEY_PATH, 'rb') as f:
                priv = load_pem_private_key(f.read(), password=None)
            with open(PUBLIC_KEY_PATH, 'rb') as f:
                pub = load_pem_public_key(f.read())
            return priv, pub
        except Exception:
            pass
    return _generate_and_save_keys()

_private_key, _public_key = load_signing_keys()


def sign_payload(payload_dict: dict) -> str:
    """Canonicalize dict → JSON (sorted keys, no spaces) then Ed25519-sign → base64url."""
    canonical = json.dumps(payload_dict, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
    sig_bytes  = _private_key.sign(canonical.encode('utf-8'))
    return base64.urlsafe_b64encode(sig_bytes).decode('ascii')

def verify_payload_signature(payload_dict: dict, signature_b64: str) -> bool:
    """Return True iff signature validates the canonicalized payload dict."""
    try:
        sig_bytes = base64.urlsafe_b64decode(signature_b64 + '==')
        canonical = json.dumps(payload_dict, sort_keys=True, separators=(',', ':'), ensure_ascii=True)
        _public_key.verify(sig_bytes, canonical.encode('utf-8'))
        return True
    except (InvalidSignature, Exception):
        return False

def get_public_key_b64() -> str:
    """Return base64url-encoded raw public key bytes for embedding in verifier apps."""
    raw = _public_key.public_bytes(Encoding.Raw, PublicFormat.Raw)
    return base64.urlsafe_b64encode(raw).decode('ascii')


# ── MongoDB Atlas Database ──────────────────────────────────────────────────
import db_mongo

def init_db():
    db_mongo.init_db()


# ── Utilities ────────────────────────────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access the laboratory system.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def generate_report_number():
    """Generate unique report number: IGI-YYYY-NNNNN"""
    year = datetime.now().year
    while True:
        seq = random.randint(1, 99999)
        rn  = f"IGI-{year}-{seq:05d}"
        if not db_mongo.check_report_number_exists(rn):
            return rn

def generate_pin():
    return ''.join(random.choices(string.digits, k=6))

def build_qr_payload(cert_data: dict) -> dict:
    """Build the signable certificate payload (excludes signature itself)."""
    return {
        "schema":   QR_SCHEMA_VERSION,
        "inst":     INSTITUTE_NAME,
        "cert_no":  cert_data['report_number'],
        "gem":      cert_data['gemstone_name'],
        "weight":   str(cert_data['weight_carat']),
        "shape":    cert_data.get('shape_cut') or '',
        "color":    cert_data.get('color') or '',
        "ri":       cert_data.get('refractive_index') or '',
        "sg":       cert_data.get('specific_gravity') or '',
        "hard":     cert_data.get('hardness') or '',
        "formula":  cert_data.get('chemical_formula') or '',
        "crystal":  cert_data.get('crystal_system') or '',
        "comments": cert_data.get('comments') or '',
        "issued_to":cert_data.get('customer_name') or '',
        "date":     cert_data.get('created_at', '')[:10],
        "kid":      SIGNING_KEY_ID,
    }

def get_public_base_url() -> str:
    """Determine the public or LAN-reachable base URL for QR codes."""
    # 1. Configured explicitly in environment or .env
    configured = os.getenv('PUBLIC_BASE_URL') or os.getenv('BASE_URL')
    if configured:
        return configured.rstrip('/')

    # 2. Inside active Flask request context (matches whatever address the user is accessing)
    try:
        from flask import has_request_context
        if has_request_context():
            return request.host_url.rstrip('/')
    except Exception:
        pass

    # 3. Detect machine outbound Wi-Fi/LAN IP so phones on the same network can access
    try:
        import socket
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(0.5)
        s.connect(('8.8.8.8', 80))
        ip = s.getsockname()[0]
        s.close()
        return f"http://{ip}:5000"
    except Exception:
        return "http://127.0.0.1:5000"


def generate_qr(cert_data: dict, filename: str, base_url: str = None) -> tuple[str, str]:
    """
    Generate QR code PNG.
    Returns (filename, json_payload_string).
    Encodes the direct verification URL into the QR code so when scanned by ANY phone camera,
    the user immediately sees the certificate details upon tap.
    Also computes and stores the Ed25519 digital signature for cryptographic verification.
    """
    if not base_url:
        base_url = get_public_base_url()

    verify_url = f"{base_url}/verify?report={cert_data['report_number']}&pin={cert_data['secret_pin']}"

    payload = build_qr_payload(cert_data)
    signature = sign_payload(payload)
    qr_obj = dict(payload)
    qr_obj['sig'] = signature
    qr_obj['verify_url'] = verify_url
    qr_json = json.dumps(qr_obj, separators=(',', ':'))

    # Encode the direct URL into the QR code for instant, reliable scanning on any mobile camera / QR reader
    qr = qrcode.QRCode(
        version=None,          # auto-size
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=4,
    )
    qr.add_data(verify_url)
    qr.make(fit=True)

    img  = qr.make_image(fill_color="black", back_color="white")
    path = os.path.join(QR_FOLDER, filename)
    img.save(path)
    return filename, qr_json

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTS

def save_image(file_obj):
    """Save uploaded image + create thumbnail. Returns relative path."""
    ext      = file_obj.filename.rsplit('.', 1)[1].lower()
    unique   = ''.join(random.choices(string.ascii_lowercase + string.digits, k=12))
    filename = f"{unique}.{ext}"
    path     = os.path.join(UPLOAD_FOLDER, filename)

    img = Image.open(file_obj)
    img = img.convert('RGB')

    # Create square crop (center)
    min_dim = min(img.width, img.height)
    left    = (img.width  - min_dim) // 2
    top     = (img.height - min_dim) // 2
    img     = img.crop((left, top, left + min_dim, top + min_dim))
    img     = img.resize((800, 800), Image.LANCZOS)
    img.save(path, quality=90, optimize=True)

    return filename


# ── Auth Routes ───────────────────────────────────────────────────────────────
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))

    active_tab = request.args.get('tab', 'login')

    if request.method == 'POST':
        action = request.form.get('action', 'login')

        if action == 'register':
            active_tab = 'register'
            full_name        = request.form.get('full_name', '').strip()
            username         = request.form.get('username', '').strip()
            email            = request.form.get('email', '').strip()
            password         = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')

            # Validations
            if not full_name or not username or not password:
                flash('Please fill in all required fields.', 'error')
                return render_template('login.html', active_tab='register',
                                       reg_name=full_name, reg_username=username, reg_email=email,
                                       institute=INSTITUTE_NAME)

            if len(password) < 6:
                flash('Password must be at least 6 characters long.', 'error')
                return render_template('login.html', active_tab='register',
                                       reg_name=full_name, reg_username=username, reg_email=email,
                                       institute=INSTITUTE_NAME)

            if password != confirm_password:
                flash('Passwords do not match. Please re-enter them.', 'error')
                return render_template('login.html', active_tab='register',
                                       reg_name=full_name, reg_username=username, reg_email=email,
                                       institute=INSTITUTE_NAME)

            existing_user = db_mongo.find_user_by_username(username)
            if existing_user:
                flash('This username is already taken. Please choose another.', 'error')
                return render_template('login.html', active_tab='register',
                                       reg_name=full_name, reg_username=username, reg_email=email,
                                       institute=INSTITUTE_NAME)

            if email:
                existing_email = db_mongo.find_user_by_email(email)
                if existing_email:
                    flash('An account with this email already exists. Please sign in.', 'error')
                    return render_template('login.html', active_tab='login',
                                           login_identifier=email, institute=INSTITUTE_NAME)

            # Insert new user in MongoDB Atlas
            user_id = db_mongo.create_user(
                username=username,
                email=email if email else None,
                password_hash=generate_password_hash(password),
                full_name=full_name
            )

            # Automatic seamless login upon registration
            session.clear()
            session['user_id']   = user_id
            session['username']  = username
            session['full_name'] = full_name
            session.permanent    = True

            flash(f'Account created successfully! Welcome, {full_name}.', 'success')
            return redirect(url_for('dashboard'))

        else:
            # Login action
            active_tab = 'login'
            identifier = request.form.get('identifier', '') or request.form.get('username', '')
            identifier = identifier.strip()
            password   = request.form.get('password', '')

            if not identifier or not password:
                flash('Please enter your username or email and password.', 'error')
                return render_template('login.html', active_tab='login',
                                       login_identifier=identifier, institute=INSTITUTE_NAME)

            # Look up by either username or email in MongoDB Atlas
            user = db_mongo.find_user_by_identifier(identifier)

            if user and check_password_hash(user['password_hash'], password):
                session.clear()
                session['user_id']   = user['id']
                session['username']  = user['username']
                session['full_name'] = user.get('full_name') or user['username']
                session.permanent    = True
                flash(f'Welcome back, {session["full_name"]}!', 'success')
                return redirect(url_for('dashboard'))

            flash('Invalid username/email or password. Please try again.', 'error')
            return render_template('login.html', active_tab='login',
                                   login_identifier=identifier, institute=INSTITUTE_NAME)

    return render_template('login.html', active_tab=active_tab, institute=INSTITUTE_NAME)


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        return login()
    return redirect(url_for('login', tab='register'))


@app.route('/logout')
def logout():
    session.clear()
    flash('You have been signed out safely.', 'success')
    return redirect(url_for('login'))


# ── Dashboard ─────────────────────────────────────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    certs     = db_mongo.get_all_certificates()
    total     = len(certs)
    originals = sum(1 for c in certs if not c.get('is_clone'))
    clones    = total - originals
    return render_template('dashboard.html',
        certificates=certs, total=total, originals=originals, clones=clones,
        institute=INSTITUTE_NAME)


# ── Certificate: New ──────────────────────────────────────────────────────────
@app.route('/certificate/new', methods=['GET', 'POST'])
@login_required
def new_certificate():
    gemstones = db_mongo.get_active_gemstones()
    if request.method == 'POST':
        customer_name    = request.form.get('customer_name', '').strip()
        file_name        = request.form.get('file_name', '').strip()
        gemstone_name    = request.form.get('gemstone_name', '').strip()
        new_gemstone_input = request.form.get('new_gemstone_name', '').strip()
        weight_carat     = request.form.get('weight_carat', '0')
        shape_cut        = request.form.get('shape_cut', '').strip()
        color            = request.form.get('color', '').strip()
        comments         = request.form.get('comments', '').strip()
        refractive_index = request.form.get('refractive_index', '').strip()
        specific_gravity = request.form.get('specific_gravity', '').strip()
        hardness         = request.form.get('hardness', '').strip()
        chemical_formula = request.form.get('chemical_formula', '').strip()
        crystal_system   = request.form.get('crystal_system', '').strip()
        image_path       = request.form.get('image_path', '').strip()

        # Handle "other" gemstone
        if gemstone_name == '__other__':
            clean_new = new_gemstone_input.strip()
            if not clean_new:
                flash('Please enter a name for the new gemstone type.', 'error')
                return render_template('new_certificate.html', gemstones=gemstones, cert=None, institute=INSTITUTE_NAME)

            # Check if gemstone already exists in library (case-insensitive)
            existing_gem = db_mongo.get_gemstone_by_name(clean_new)
            if existing_gem:
                gemstone_name = existing_gem['name']
            else:
                try:
                    db_mongo.insert_custom_gemstone({
                        'name': clean_new,
                        'refractive_index': refractive_index,
                        'specific_gravity': specific_gravity,
                        'hardness': hardness,
                        'chemical_formula': chemical_formula,
                        'crystal_system': crystal_system
                    })
                    gemstone_name = clean_new
                except Exception as e:
                    app.logger.error(f"Error inserting gemstone '{clean_new}': {e}")
                    gemstone_name = clean_new

        if not customer_name or not gemstone_name:
            flash('Customer Name and Gemstone Name are required.', 'error')
            return render_template('new_certificate.html', gemstones=gemstones, cert=None, institute=INSTITUTE_NAME)

        weight_input = str(weight_carat).strip()
        try:
            weight_carat = float(weight_input)
        except (ValueError, TypeError):
            weight_carat = weight_input or '0'

        report_number = generate_report_number()
        secret_pin    = generate_pin()
        qr_filename   = f"{report_number.replace('-','_')}_qr.png"

        cert_data = {
            'report_number': report_number,
            'secret_pin': secret_pin,
            'customer_name': customer_name,
            'gemstone_name': gemstone_name,
            'weight_carat': weight_carat,
            'shape_cut': shape_cut,
            'color': color,
            'refractive_index': refractive_index,
            'specific_gravity': specific_gravity,
            'hardness': hardness,
            'chemical_formula': chemical_formula,
            'crystal_system': crystal_system,
            'comments': comments,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        _, qr_json = generate_qr(cert_data, qr_filename)

        cert_doc = {
            'report_number': report_number,
            'secret_pin': secret_pin,
            'customer_name': customer_name,
            'file_name': file_name,
            'gemstone_name': gemstone_name,
            'weight_carat': weight_carat,
            'shape_cut': shape_cut,
            'color': color,
            'comments': comments,
            'refractive_index': refractive_index,
            'specific_gravity': specific_gravity,
            'hardness': hardness,
            'chemical_formula': chemical_formula,
            'crystal_system': crystal_system,
            'image_path': image_path,
            'qr_code_path': qr_filename,
            'qr_payload': qr_json,
            'created_by': session['user_id'],
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'is_clone': 0,
            'parent_id': None
        }

        cert_id = db_mongo.insert_certificate(cert_doc)

        flash(f'Certificate {report_number} created successfully!', 'success')
        return redirect(url_for('view_certificate', cert_id=cert_id))

    return render_template('new_certificate.html', gemstones=gemstones, cert=None, institute=INSTITUTE_NAME)


# ── Certificate: View / Print ─────────────────────────────────────────────────
@app.route('/certificate/<int:cert_id>')
@login_required
def view_certificate(cert_id):
    cert = db_mongo.get_certificate_by_id(cert_id)
    if not cert:
        flash('Certificate not found.', 'error')
        return redirect(url_for('dashboard'))
    return render_template('certificate.html', cert=cert, institute=INSTITUTE_NAME,
                           institute_website=INSTITUTE_WEBSITE, institute_email=INSTITUTE_EMAIL)


# ── Certificate: Delete ───────────────────────────────────────────────────────
@app.route('/certificate/<int:cert_id>', methods=['DELETE'])
@login_required
@csrf.exempt
def delete_certificate(cert_id):
    cert = db_mongo.get_certificate_by_id(cert_id)
    if not cert:
        return jsonify({'error': 'Not found'}), 404
    for path_key, folder in [('image_path', UPLOAD_FOLDER), ('qr_code_path', QR_FOLDER)]:
        p = cert.get(path_key)
        if p:
            try:
                os.remove(os.path.join(folder, p))
            except OSError:
                pass
    db_mongo.delete_certificate_by_id(cert_id)
    return jsonify({'success': True})


# ── Certificate: Bulk Clone ───────────────────────────────────────────────────
@app.route('/certificate/<int:cert_id>/clone', methods=['POST'])
@login_required
@csrf.exempt
def clone_certificate(cert_id):
    data  = request.get_json() or {}
    count = int(data.get('count', 0))
    if count < 1 or count > 500:
        return jsonify({'error': 'Count must be between 1 and 500'}), 400

    src = db_mongo.get_certificate_by_id(cert_id)
    if not src:
        return jsonify({'error': 'Source certificate not found'}), 404

    created = 0
    for _ in range(count):
        rn       = generate_report_number()
        pin      = generate_pin()
        qr_fname = f"{rn.replace('-','_')}_qr.png"
        now_str  = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        cert_data = {
            'report_number': rn,
            'secret_pin': pin,
            'customer_name': src['customer_name'],
            'gemstone_name': src['gemstone_name'],
            'weight_carat': src['weight_carat'],
            'shape_cut': src.get('shape_cut'),
            'color': src.get('color'),
            'refractive_index': src.get('refractive_index'),
            'specific_gravity': src.get('specific_gravity'),
            'hardness': src.get('hardness'),
            'chemical_formula': src.get('chemical_formula'),
            'crystal_system': src.get('crystal_system'),
            'comments': src.get('comments'),
            'created_at': now_str,
        }
        _, qr_json = generate_qr(cert_data, qr_fname)
        clone_doc = {
            'report_number': rn,
            'secret_pin': pin,
            'customer_name': src['customer_name'],
            'file_name': src.get('file_name'),
            'gemstone_name': src['gemstone_name'],
            'weight_carat': src['weight_carat'],
            'shape_cut': src.get('shape_cut'),
            'color': src.get('color'),
            'comments': src.get('comments'),
            'refractive_index': src.get('refractive_index'),
            'specific_gravity': src.get('specific_gravity'),
            'hardness': src.get('hardness'),
            'chemical_formula': src.get('chemical_formula'),
            'crystal_system': src.get('crystal_system'),
            'image_path': src.get('image_path'),
            'qr_code_path': qr_fname,
            'qr_payload': qr_json,
            'created_by': session['user_id'],
            'created_at': now_str,
            'is_clone': 1,
            'parent_id': cert_id
        }
        db_mongo.insert_certificate(clone_doc)
        created += 1

    return jsonify({'success': True, 'created': created})


# ── Labels ────────────────────────────────────────────────────────────────────
@app.route('/labels/<int:cert_id>')
@login_required
def print_labels(cert_id):
    cert = db_mongo.get_certificate_by_id(cert_id)
    if not cert:
        flash('Certificate not found.', 'error')
        return redirect(url_for('dashboard'))

    # If all=1 is requested and cert has clones, show all. Otherwise default to single card
    show_all = request.args.get('all') == '1'
    if show_all and not cert.get('is_clone'):
        clones = db_mongo.get_certificate_clones(cert_id)
        certs  = [cert] + list(clones)
    else:
        certs = [cert]

    return render_template('print_labels.html', cert=cert, certs=certs,
                           cert_ids_str=str(cert_id), is_merged=False,
                           institute=INSTITUTE_NAME,
                           lab_address='Gemological Testing Lab')


# ── Direct Single Card PDF Download ──────────────────────────────────────────
@app.route('/labels/<int:cert_id>/pdf')
@login_required
def download_card_pdf(cert_id):
    cert = db_mongo.get_certificate_by_id(cert_id)
    if not cert:
        flash('Certificate not found.', 'error')
        return redirect(url_for('dashboard'))

    buf = BytesIO()
    gemologist = session.get('full_name') or 'Gemologist'
    card_pdf.generate_single_card_pdf(cert, buf, base_dir=BASE_DIR, gemologist_name=gemologist)
    buf.seek(0)

    filename = f"{cert.get('report_number', 'IGI_Card')}_Card.pdf"
    return send_file(
        buf,
        as_attachment=True,
        download_name=filename,
        mimetype='application/pdf'
    )


# ── Merged Cards (Max 10) View ────────────────────────────────────────────────
@app.route('/labels/merge')
@login_required
def merge_labels():
    raw_ids = request.args.get('ids', '')
    if not raw_ids:
        flash('No certificates selected for merge.', 'error')
        return redirect(url_for('dashboard'))

    try:
        id_list = [int(i.strip()) for i in raw_ids.split(',') if i.strip().isdigit()]
    except Exception:
        id_list = []

    if not id_list:
        flash('Invalid certificate IDs.', 'error')
        return redirect(url_for('dashboard'))

    if len(id_list) > 10:
        id_list = id_list[:10]

    certs = []
    for cid in id_list:
        c = db_mongo.get_certificate_by_id(cid)
        if c:
            certs.append(c)

    if not certs:
        flash('Selected certificates not found.', 'error')
        return redirect(url_for('dashboard'))

    first_cert = certs[0]
    return render_template('print_labels.html', cert=first_cert, certs=certs,
                           cert_ids_str=','.join(str(c['id']) for c in certs),
                           is_merged=True,
                           institute=INSTITUTE_NAME,
                           lab_address='Gemological Testing Lab')


# ── Merged Cards (Max 10) PDF Download ────────────────────────────────────────
@app.route('/labels/merge/pdf')
@login_required
def download_merged_cards_pdf():
    raw_ids = request.args.get('ids', '')
    if not raw_ids:
        flash('No certificates selected for merge.', 'error')
        return redirect(url_for('dashboard'))

    try:
        id_list = [int(i.strip()) for i in raw_ids.split(',') if i.strip().isdigit()]
    except Exception:
        id_list = []

    if not id_list:
        flash('Invalid certificate IDs.', 'error')
        return redirect(url_for('dashboard'))

    if len(id_list) > 10:
        id_list = id_list[:10]

    certs = []
    for cid in id_list:
        c = db_mongo.get_certificate_by_id(cid)
        if c:
            certs.append(c)

    if not certs:
        flash('Selected certificates not found.', 'error')
        return redirect(url_for('dashboard'))

    buf = BytesIO()
    gemologist = session.get('full_name') or 'Gemologist'
    card_pdf.generate_merged_cards_pdf(certs, buf, base_dir=BASE_DIR, gemologist_name=gemologist)
    buf.seek(0)

    filename = f"IGI_Merged_{len(certs)}_Cards_A4.pdf"
    return send_file(
        buf,
        as_attachment=True,
        download_name=filename,
        mimetype='application/pdf'
    )


# ── API: Gemstone Library ─────────────────────────────────────────────────────
@app.route('/api/gemstone/<name>')
@login_required
def api_gemstone(name):
    gem = db_mongo.get_gemstone_by_name(name)
    if not gem:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({
        'name':             gem['name'],
        'refractive_index': gem.get('refractive_index', ''),
        'specific_gravity': gem.get('specific_gravity', ''),
        'hardness':         gem.get('hardness', ''),
        'chemical_formula': gem.get('chemical_formula', ''),
        'crystal_system':   gem.get('crystal_system', ''),
        'is_custom':        bool(gem.get('is_custom')),
    })


# ── API: Add Custom Gemstone ──────────────────────────────────────────────────
@app.route('/api/gemstone/add', methods=['POST'])
@csrf.exempt
@login_required
def api_add_gemstone():
    data = request.get_json(silent=True) or {}
    name = (data.get('name') or request.form.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Gemstone name is required'}), 400
    if len(name) > 100:
        return jsonify({'error': 'Name too long (max 100 characters)'}), 400

    existing = db_mongo.get_gemstone_by_name(name)
    if existing:
        return jsonify({
            'success': True,
            'id': existing.get('id'),
            'name': existing.get('name', name),
            'already_exists': True
        })

    try:
        gid = db_mongo.insert_custom_gemstone({
            'name': name,
            'refractive_index': data.get('refractive_index', ''),
            'specific_gravity': data.get('specific_gravity', ''),
            'hardness':         data.get('hardness', ''),
            'chemical_formula': data.get('chemical_formula', ''),
            'crystal_system':   data.get('crystal_system', '')
        })
        return jsonify({'success': True, 'id': gid, 'name': name})
    except Exception as e:
        app.logger.error(f"Failed to add gemstone: {e}")
        return jsonify({'error': f'Failed to add gemstone: {str(e)}'}), 500


# ── API: Deactivate Custom Gemstone ──────────────────────────────────────────
@app.route('/api/gemstone/<int:gem_id>/deactivate', methods=['POST'])
@login_required
@csrf.exempt
def api_deactivate_gemstone(gem_id):
    success = db_mongo.deactivate_gemstone(gem_id)
    if not success:
        return jsonify({'error': 'Custom gemstone not found'}), 404
    return jsonify({'success': True})


# ── API: Image Upload ─────────────────────────────────────────────────────────
@app.route('/api/upload-image', methods=['POST'])
@login_required
@csrf.exempt
def upload_image():
    if 'image' not in request.files:
        return jsonify({'error': 'No image file provided'}), 400
    file = request.files['image']
    if not file or file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    if not allowed_file(file.filename):
        return jsonify({'error': 'Only JPEG, PNG, or WEBP files are accepted'}), 400

    try:
        filename = save_image(file)
        return jsonify({
            'success':       True,
            'image_path':    filename,
            'thumbnail_url': f'/static/uploads/{filename}',
        })
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500


# ── Public Verify: Page ───────────────────────────────────────────────────────
@app.route('/verify')
def verify_page():
    report_number = request.args.get('report', '').strip()
    secret_pin    = request.args.get('pin', '').strip()
    cert = None
    if report_number:
        cert = db_mongo.verify_certificate_record(report_number, secret_pin if secret_pin else None)

    return render_template('verify.html',
                           institute=INSTITUTE_NAME,
                           institute_website=INSTITUTE_WEBSITE,
                           institute_email=INSTITUTE_EMAIL,
                           report_number=report_number,
                           secret_pin=secret_pin,
                           cert=cert)


# ── Public Verify: JSON API (online) ─────────────────────────────────────────
@app.route('/api/verify')
def api_verify():
    report_number = request.args.get('report', '').strip()
    secret_pin    = request.args.get('pin', '').strip()

    if not report_number:
        return jsonify({'error': 'Report number is required'}), 400

    cert = db_mongo.verify_certificate_record(report_number, secret_pin if secret_pin else None)
    if not cert:
        return jsonify({'error': 'Certificate not found or PIN incorrect'}), 404

    image_url = f'/static/uploads/{cert["image_path"]}' if cert.get('image_path') else None
    qr_url    = f'/static/uploads/qrcodes/{cert["qr_code_path"]}' if cert.get('qr_code_path') else None

    return jsonify({
        'report_number':    cert['report_number'],
        'customer_name':    cert['customer_name'],
        'gemstone_name':    cert['gemstone_name'],
        'weight_carat':     cert['weight_carat'],
        'shape_cut':        cert.get('shape_cut'),
        'color':            cert.get('color'),
        'comments':         cert.get('comments'),
        'refractive_index': cert.get('refractive_index'),
        'specific_gravity': cert.get('specific_gravity'),
        'hardness':         cert.get('hardness'),
        'chemical_formula': cert.get('chemical_formula'),
        'crystal_system':   cert.get('crystal_system'),
        'created_at':       cert.get('created_at'),
        'image_url':        image_url,
        'qr_url':           qr_url,
        'institute':        INSTITUTE_NAME,
    })


# ── Offline QR Verify: JSON API ──────────────────────────────────────────────
@app.route('/api/verify-qr', methods=['POST'])
@csrf.exempt
def api_verify_qr():
    """
    POST body: { "qr_data": "<raw QR JSON string>" }
    Returns signature verification result.
    Works without internet once the verifier is installed and public key is embedded.
    """
    body    = request.get_json() or {}
    qr_data = body.get('qr_data', '').strip()
    if not qr_data:
        return jsonify({
            'status': 'INVALID',
            'status_label': 'UNSUPPORTED OR INVALID QR DATA',
            'reason': 'Empty QR data'
        }), 400

    try:
        qr_obj = json.loads(qr_data)
    except json.JSONDecodeError:
        return jsonify({
            'status': 'INVALID',
            'status_label': 'UNSUPPORTED OR INVALID QR DATA',
            'reason': 'QR payload is not valid JSON'
        }), 400

    # Check schema version
    schema = qr_obj.get('schema', '')
    if schema != QR_SCHEMA_VERSION:
        return jsonify({
            'status': 'LEGACY',
            'status_label': 'UNSUPPORTED OR INVALID QR DATA',
            'reason': f'Unsupported schema version "{schema}". This may be a legacy certificate without offline verification.'
        }), 200

    sig = qr_obj.get('sig', '')
    if not sig:
        return jsonify({
            'status': 'INVALID',
            'status_label': 'INVALID SIGNATURE — DATA MAY HAVE BEEN MODIFIED',
            'reason': 'No signature present in QR data'
        }), 200

    # Extract the payload (same keys as build_qr_payload, minus sig and verify_url)
    PAYLOAD_KEYS = ['schema','inst','cert_no','gem','weight','shape','color','ri',
                    'sg','hard','formula','crystal','comments','issued_to','date','kid']
    payload = {k: qr_obj[k] for k in PAYLOAD_KEYS if k in qr_obj}

    valid = verify_payload_signature(payload, sig)
    if valid:
        return jsonify({
            'status': 'VALID',
            'status_label': 'SIGNATURE VALID — DATA UNALTERED',
            'cert_no':  qr_obj.get('cert_no'),
            'inst':     qr_obj.get('inst'),
            'gem':      qr_obj.get('gem'),
            'weight':   qr_obj.get('weight'),
            'shape':    qr_obj.get('shape'),
            'color':    qr_obj.get('color'),
            'ri':       qr_obj.get('ri'),
            'hardness': qr_obj.get('hard'),
            'crystal':  qr_obj.get('crystal'),
            'issued_to':qr_obj.get('issued_to'),
            'date':     qr_obj.get('date'),
            'kid':      qr_obj.get('kid'),
            'disclaimer': (
                'Offline verification confirms signed data integrity only. '
                'It does not authenticate the physical gemstone, '
                'nor can it detect subsequent revocation without an internet connection.'
            )
        }), 200
    else:
        return jsonify({
            'status': 'TAMPERED',
            'status_label': 'INVALID SIGNATURE — DATA MAY HAVE BEEN MODIFIED',
            'reason': 'The QR payload signature does not match. The certificate data may have been tampered with.'
        }), 200


# ── Public Key Endpoint ───────────────────────────────────────────────────────
@app.route('/api/public-key')
def api_public_key():
    """Return the base64url-encoded Ed25519 public key for verifier app distribution."""
    return jsonify({
        'algorithm':  'Ed25519',
        'key_id':     SIGNING_KEY_ID,
        'public_key': get_public_key_b64(),
        'institute':  INSTITUTE_NAME,
        'note': (
            'Embed this key in your offline verifier app. '
            'Never expose the private signing key.'
        )
    })


# ── Entry Point ───────────────────────────────────────────────────────────────
if __name__ == '__main__':
    init_db()
    print("\n" + "="*60)
    print(f"  {INSTITUTE_NAME}")
    print("="*60)
    print("  Database:   MongoDB Atlas (gemsoftsoft)")
    print("  URL:        http://127.0.0.1:5000")
    print("  Access:     Sign In or Create an Account")
    print("  Verify:     http://127.0.0.1:5000/verify")
    print("  Public Key: http://127.0.0.1:5000/api/public-key")
    print(f"  Sign Key:   {PRIVATE_KEY_PATH}")
    local_ip = get_public_base_url()
    print(f"  Network IP: {local_ip}")
    print("="*60 + "\n")
    app.run(debug=True, host='0.0.0.0', port=5000)
