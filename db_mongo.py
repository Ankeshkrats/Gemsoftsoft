"""
db_mongo.py — MongoDB Atlas Connection & Data Layer for Gemsoftsoft
Connects to MongoDB Atlas, manages auto-increment sequences, handles migrations,
and provides clean CRUD operations for users, certificates, and gemstone library.
"""

import os
import re
import sqlite3
import pymongo
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

MONGO_URI = os.getenv('MONGODB_URI') or os.getenv('MONGO_URI')
MONGO_DB_NAME = os.getenv('MONGODB_DB_NAME', 'gemsoftsoft')

_client = None

GEMSTONE_SEED = [
    ("Natural Ruby",        "1.762 – 1.770", "3.99 – 4.00", "9",   "Al₂O₃",        "Trigonal"),
    ("Blue Sapphire",       "1.762 – 1.770", "3.99 – 4.00", "9",   "Al₂O₃",        "Trigonal"),
    ("Diamond",             "2.417",         "3.51 – 3.53", "10",  "C",             "Cubic"),
    ("Emerald",             "1.565 – 1.602", "2.67 – 2.78", "7.5", "Be₃Al₂Si₆O₁₈", "Hexagonal"),
    ("Natural Alexandrite", "1.746 – 1.755", "3.70 – 3.73", "8.5", "BeAl₂O₄",      "Orthorhombic"),
    ("Aquamarine",          "1.567 – 1.590", "2.68 – 2.74", "7.5", "Be₃Al₂Si₆O₁₈", "Hexagonal"),
    ("Amethyst",            "1.544 – 1.553", "2.65 – 2.66", "7",   "SiO₂",         "Trigonal"),
    ("Topaz",               "1.619 – 1.627", "3.49 – 3.57", "8",   "Al₂SiO₄(F,OH)₂", "Orthorhombic"),
    ("Opal",                "1.450",         "1.98 – 2.20", "5.5", "SiO₂·nH₂O",   "Amorphous"),
    ("Tanzanite",           "1.691 – 1.704", "3.35",        "6.5", "Ca₂Al₃(SiO₄)₃(OH)", "Orthorhombic"),
    ("Spinel",              "1.712 – 1.762", "3.57 – 3.90", "8",   "MgAl₂O₄",     "Cubic"),
    ("Tourmaline",          "1.614 – 1.666", "2.98 – 3.26", "7.5", "Complex Borosilicate", "Trigonal"),
    ("Peridot",             "1.650 – 1.703", "3.27 – 3.48", "6.5", "(Mg,Fe)₂SiO₄", "Orthorhombic"),
    ("Garnet",              "1.714 – 1.888", "3.50 – 4.30", "6.5", "X₃Y₂(SiO₄)₃", "Cubic"),
    ("Zircon",              "1.810 – 2.024", "3.90 – 4.73", "7.5", "ZrSiO₄",      "Tetragonal"),
    ("Moonstone",           "1.518 – 1.526", "2.56 – 2.62", "6",   "KAlSi₃O₈",    "Monoclinic"),
]


def get_client():
    global _client
    if _client is None:
        uri = os.getenv('MONGODB_URI') or os.getenv('MONGO_URI')
        if not uri:
            raise RuntimeError(
                "MONGODB_URI is not set in environment or .env file. "
                "Please add MONGODB_URI=mongodb+srv://... to your .env"
            )
        _client = pymongo.MongoClient(
            uri,
            serverSelectionTimeoutMS=8000,
            connectTimeoutMS=8000
        )
    return _client


def get_db():
    client = get_client()
    return client[MONGO_DB_NAME]


def serialize_doc(doc):
    """Convert MongoDB document to a Jinja2/JSON-friendly dict."""
    if not doc:
        return doc
    d = dict(doc)
    if '_id' in d:
        d['_id'] = str(d['_id'])
    return d


def get_next_sequence(sequence_name: str) -> int:
    """Generate safe atomic sequential IDs for certificates, users, etc."""
    db = get_db()

    # Self-healing counter initialization to prevent DuplicateKeyError collisions
    start_seq = 0
    if sequence_name == 'gemstone_library':
        max_doc = db.gemstone_library.find_one(sort=[('id', -1)])
        if max_doc and 'id' in max_doc:
            start_seq = int(max_doc['id'])
    elif sequence_name == 'certificates':
        max_doc = db.certificates.find_one(sort=[('id', -1)])
        if max_doc and 'id' in max_doc:
            start_seq = int(max_doc['id'])
    elif sequence_name == 'users':
        max_doc = db.users.find_one(sort=[('id', -1)])
        if max_doc and 'id' in max_doc:
            start_seq = int(max_doc['id'])

    counter = db.counters.find_one({'_id': sequence_name})
    if counter is None or int(counter.get('seq', 0)) < start_seq:
        db.counters.update_one(
            {'_id': sequence_name},
            {'$set': {'seq': start_seq}},
            upsert=True
        )

    ret = db.counters.find_one_and_update(
        {'_id': sequence_name},
        {'$inc': {'seq': 1}},
        upsert=True,
        return_document=pymongo.ReturnDocument.AFTER
    )
    return int(ret['seq'])


def reset_all_data(keep_gemstones: bool = True):
    """
    Completely delete all user accounts, certificates, and reset ID sequences to 1.
    """
    db = get_db()
    db.users.delete_many({})
    db.certificates.delete_many({})
    db.counters.delete_many({})
    if not keep_gemstones:
        db.gemstone_library.delete_many({})
    print("  [MongoDB Atlas] All previous users, certificates, and sequences deleted successfully!")


def init_db():
    """
    Initialise MongoDB Atlas collections, ensure indexes, and seed gemstone library if empty.
    All data is stored directly in MongoDB Atlas.
    """
    db = get_db()

    # 1. Unique indexes
    try:
        db.users.create_index([('username', 1)], unique=True)
        db.users.create_index([('id', 1)], unique=True)
        db.certificates.create_index([('report_number', 1)], unique=True)
        db.certificates.create_index([('id', 1)], unique=True)
        db.gemstone_library.create_index([('name', 1)], unique=True)
        db.gemstone_library.create_index([('id', 1)], unique=True)
    except Exception as e:
        print(f"Index creation note: {e}")

    # 2. Seed Gemstone Reference Library if empty
    if db.gemstone_library.count_documents({}) == 0:
        for gem in GEMSTONE_SEED:
            db.gemstone_library.insert_one({
                'id': get_next_sequence('gemstone_library'),
                'name': gem[0],
                'refractive_index': gem[1],
                'specific_gravity': gem[2],
                'hardness': gem[3],
                'chemical_formula': gem[4],
                'crystal_system': gem[5],
                'is_custom': 0,
                'is_active': 1
            })
        print("  [MongoDB Atlas] Gemstone reference library seeded.")


# ── User Operations ──────────────────────────────────────────────────────────
def find_user_by_identifier(identifier: str):
    """Find a user by username or email (case-insensitive)."""
    if not identifier:
        return None
    db = get_db()
    ident = identifier.strip()
    return db.users.find_one({
        '$or': [
            {'username': {'$regex': f"^{re.escape(ident)}$", '$options': 'i'}},
            {'email': {'$regex': f"^{re.escape(ident)}$", '$options': 'i'}}
        ]
    })


def find_user_by_username(username: str):
    """Find user strictly by username."""
    if not username:
        return None
    db = get_db()
    return db.users.find_one({
        'username': {'$regex': f"^{re.escape(username.strip())}$", '$options': 'i'}
    })


def find_user_by_email(email: str):
    """Find user strictly by email."""
    if not email:
        return None
    db = get_db()
    return db.users.find_one({
        'email': {'$regex': f"^{re.escape(email.strip())}$", '$options': 'i'}
    })


def create_user(username: str, email: str, password_hash: str, full_name: str) -> int:
    """Insert a new user document in MongoDB Atlas and return generated integer ID."""
    db = get_db()
    new_id = get_next_sequence('users')
    doc = {
        'id': new_id,
        'username': username.strip(),
        'email': email.strip() if email else None,
        'password_hash': password_hash,
        'full_name': full_name.strip() if full_name else username,
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    db.users.insert_one(doc)
    return new_id


# ── Certificate Operations ───────────────────────────────────────────────────
def check_report_number_exists(report_number: str) -> bool:
    db = get_db()
    return db.certificates.find_one({'report_number': report_number}) is not None


def get_all_certificates():
    db = get_db()
    return [serialize_doc(c) for c in db.certificates.find().sort('created_at', -1)]


def get_certificate_by_id(cert_id: int):
    db = get_db()
    doc = db.certificates.find_one({'id': int(cert_id)})
    return serialize_doc(doc) if doc else None


def get_certificate_clones(parent_id: int):
    db = get_db()
    return [serialize_doc(c) for c in db.certificates.find({'parent_id': int(parent_id)})]


def insert_certificate(cert_data: dict) -> int:
    """
    Insert certificate document into MongoDB Atlas.
    Note: To save database space, product images are NEVER stored in MongoDB Atlas.
    Only the short filename string (or empty string) is stored.
    """
    db = get_db()
    doc = dict(cert_data)

    # Strictly protect MongoDB Atlas space: ensure no binary or base64 image data is stored
    for prohibited in ['image_data', 'image_base64', 'image_binary', 'file_bytes']:
        if prohibited in doc:
            del doc[prohibited]
    
    # If image_path is suspiciously large (e.g. accidentally passed base64), clean it
    img_path = doc.get('image_path')
    if isinstance(img_path, str) and (img_path.startswith('data:image') or len(img_path) > 255):
        doc['image_path'] = ''

    while True:
        try:
            new_id = get_next_sequence('certificates')
            doc['id'] = new_id
            db.certificates.insert_one(doc)
            return new_id
        except pymongo.errors.DuplicateKeyError:
            # Sync counter to actual max ID and retry
            max_doc = db.certificates.find_one(sort=[('id', -1)])
            highest_id = int(max_doc.get('id', 0)) if max_doc else 0
            db.counters.update_one({'_id': 'certificates'}, {'$set': {'seq': highest_id}}, upsert=True)


def update_certificate_qr(cert_id: int, qr_code_path: str, qr_payload: str) -> bool:
    """Update QR code path and payload for an existing certificate."""
    db = get_db()
    res = db.certificates.update_one(
        {'id': int(cert_id)},
        {'$set': {'qr_code_path': qr_code_path, 'qr_payload': qr_payload}}
    )
    return res.matched_count > 0


def delete_certificate_by_id(cert_id: int) -> bool:
    db = get_db()
    res = db.certificates.delete_one({'id': int(cert_id)})
    return res.deleted_count > 0


def verify_certificate_record(report_number: str, secret_pin: str = None):
    """
    Verify/find certificate record.
    Matches report_number (case-insensitive), and matches secret_pin if provided.
    """
    if not report_number:
        return None
    db = get_db()
    query = {
        'report_number': {'$regex': f"^{re.escape(report_number.strip())}$", '$options': 'i'}
    }
    if secret_pin and secret_pin.strip():
        query['secret_pin'] = secret_pin.strip()
    doc = db.certificates.find_one(query)
    return serialize_doc(doc) if doc else None


# ── Gemstone Library Operations ──────────────────────────────────────────────
def get_active_gemstones():
    db = get_db()
    return [serialize_doc(g) for g in db.gemstone_library.find({'is_active': 1}).sort([('is_custom', 1), ('name', 1)])]


def get_gemstone_by_name(name: str):
    if not name:
        return None
    db = get_db()
    clean = name.strip()
    doc = db.gemstone_library.find_one({
        'name': {'$regex': f"^{re.escape(clean)}$", '$options': 'i'},
        'is_active': 1
    })
    if doc:
        return serialize_doc(doc)

    # Check if exists in library but deactivated; reactivate it seamlessly
    doc_inactive = db.gemstone_library.find_one({
        'name': {'$regex': f"^{re.escape(clean)}$", '$options': 'i'}
    })
    if doc_inactive:
        db.gemstone_library.update_one({'_id': doc_inactive['_id']}, {'$set': {'is_active': 1}})
        doc_inactive['is_active'] = 1
        return serialize_doc(doc_inactive)

    return None


def insert_custom_gemstone(gem_data: dict) -> int:
    db = get_db()
    doc = dict(gem_data)
    clean_name = str(doc.get('name', '')).strip()
    doc['name'] = clean_name
    doc['is_custom'] = 1
    doc['is_active'] = 1

    # Check if duplicate exists before insert (case-insensitive)
    existing = db.gemstone_library.find_one({
        'name': {'$regex': f"^{re.escape(clean_name)}$", '$options': 'i'}
    })
    if existing:
        if not existing.get('is_active'):
            db.gemstone_library.update_one({'_id': existing['_id']}, {'$set': {'is_active': 1}})
        return int(existing.get('id', 0))

    while True:
        try:
            new_id = get_next_sequence('gemstone_library')
            doc['id'] = new_id
            db.gemstone_library.insert_one(doc)
            return new_id
        except pymongo.errors.DuplicateKeyError:
            # Check if name caused duplicate
            existing_name = db.gemstone_library.find_one({
                'name': {'$regex': f"^{re.escape(clean_name)}$", '$options': 'i'}
            })
            if existing_name:
                if not existing_name.get('is_active'):
                    db.gemstone_library.update_one({'_id': existing_name['_id']}, {'$set': {'is_active': 1}})
                return int(existing_name.get('id', 0))

            # ID collision: sync counter to actual max ID and retry
            max_doc = db.gemstone_library.find_one(sort=[('id', -1)])
            highest_id = int(max_doc.get('id', 0)) if max_doc else 0
            db.counters.update_one({'_id': 'gemstone_library'}, {'$set': {'seq': highest_id}}, upsert=True)


def deactivate_gemstone(gem_id: int) -> bool:
    db = get_db()
    res = db.gemstone_library.update_one({'id': int(gem_id)}, {'$set': {'is_active': 0}})
    return res.matched_count > 0


def deactivate_gemstone_by_name(name: str) -> bool:
    if not name:
        return False
    db = get_db()
    clean = name.strip()
    res = db.gemstone_library.update_one(
        {'name': {'$regex': f"^{re.escape(clean)}$", '$options': 'i'}},
        {'$set': {'is_active': 0}}
    )
    return res.matched_count > 0
