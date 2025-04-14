import os
import json
import sqlite3
import time
import secrets
import jwt as pyjwt
from flask import Flask, request, jsonify
# import requests
# from phe import paillier
import bcrypt
import rsa
import hashlib
import hmac
import ssl
from cryptography.fernet import Fernet
from flask_cors import CORS

# Initialize Flask app
app = Flask(__name__)

CORS(app, supports_credentials=True, expose_headers=["Authorization"], allow_headers=["Authorization", "Content-Type"])

# Secret keys
# JWT_SECRET = os.urandom(32)
JWT_SECRET = b'supersecuresecretkey123'
hmac_key = os.urandom(32)

# BASE_URL = 'http://localhost:5000'

# RSA keys for digital signatures
rsa_public_key, rsa_private_key = rsa.newkeys(512)

# AES-256 key generation
aes_key = Fernet.generate_key()
cipher = Fernet(aes_key)

# SQLite database setup
db_path = 'database/voting_system.db'

conn = sqlite3.connect(db_path, check_same_thread=False)
c = conn.cursor()

# Create tables
c.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                role TEXT CHECK(role IN ('voter', 'candidate', 'admin')),
                has_voted INTEGER DEFAULT 0 CHECK(has_voted IN (0, 1))
             )''')

c.execute('''CREATE TABLE IF NOT EXISTS votes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            encrypted_data TEXT,
            timestamp INTEGER
            )''')

# c.execute("INSERT OR IGNORE INTO users (username, password, role, has_voted) VALUES (?, ?, ?, ?)",
#           ('admin', 'admin', 'admin', 0))

conn.commit()

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12))

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

def sign_vote(vote, voter):
    vote_hash = hashlib.sha256((str(vote) + voter + secrets.token_hex(4)).encode()).digest()
    return rsa.sign(vote_hash, rsa_private_key, 'SHA-256')

def encrypt_data(data):
    return cipher.encrypt(json.dumps(data).encode('utf-8'))

def decrypt_data(encrypted_data):
    return json.loads(cipher.decrypt(encrypted_data).decode('utf-8'))

def generate_hmac(voter, candidate, nonce):
    message = f"{voter}:{candidate}:{nonce}"
    return hmac.new(hmac_key, message.encode('utf-8'), hashlib.sha256).hexdigest()

def verify_hmac(voter, candidate, nonce, mac):
    expected_mac = generate_hmac(voter, candidate, nonce)
    return hmac.compare_digest(expected_mac, mac)

def generate_jwt(username, role):
    payload = {'username': username, 'role': role, 'exp': time.time() + 300}
    return pyjwt.encode(payload, JWT_SECRET, algorithm='HS256')

def verify_jwt(token):
    if not token:
        return None
    try:
        decoded = pyjwt.decode(token, JWT_SECRET, algorithms=['HS256'])
        return decoded
    except pyjwt.ExpiredSignatureError:
        print("JWT Expired")  # Debugging
        return None
    except pyjwt.InvalidTokenError:
        print("JWT Invalid")  # Debugging
        return None
    except Exception as e:
        print("JWT verification failed:", e)
        return None

@app.route('/register', methods=['POST'])
def register():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    role = data.get('role')
    if role not in ['voter', 'candidate', 'admin']:
        return jsonify({'error': 'Invalid role'}), 400
    hashed_password = hash_password(password)
    try:
        c.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', (username, hashed_password, role))
        conn.commit()
        return jsonify({'message': f'{role.capitalize()} {username} registered successfully'})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'User already exists'}), 400

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    c.execute('SELECT password, role FROM users WHERE username = ?', (username,))
    result = c.fetchone()
    if not result or not verify_password(password, result[0]):
        return jsonify({'error': 'Invalid credentials'}), 401
    token = generate_jwt(username, result[1])
    print("login token: ", token)
    return jsonify({'message': 'Login successful', 'token': token})
    
@app.route('/candidates', methods=['GET'])
def list_candidates():
    c.execute("SELECT username FROM users WHERE role = 'candidate'")
    # print(c.fetchall())
    # candidates = [row[0] for row in c.fetchall()]
    candidates = c.fetchall()
    candidates = [row for row in candidates]

    # c.close()
    return jsonify({"candidates": candidates})

@app.route('/check_admin', methods=['GET'])
def check_admin():
    # Query the database to check if an admin exists
    # conn = sqlite3.connect('voting_system.db')
    # c = conn.cursor()
    c.execute("SELECT * FROM users WHERE role == 'admin'")
    print(c)
    admin = c.fetchone()  # Returns the first admin it finds, or None if not found
    # conn.close()
    
    print("admin ", admin[1])

    if admin:
        return "true"
    else:
        return "false"

@app.route('/all_voters_voted', methods=['GET'])
def all_voters_voted():
    with sqlite3.connect(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'voter'")
        total_voters = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM users WHERE role = 'voter' AND has_voted = 1")
        voted_voters = cursor.fetchone()[0]

    all_voted = (total_voters > 0) and (total_voters == voted_voters)

    return jsonify({
        'all_voted': all_voted,
        'total_voters': total_voters,
        'voted_voters': voted_voters
    })

@app.route('/vote', methods=['POST'])
def vote():
    data = request.json
    token = data.get('token')
    username = data.get('username')
    candidate = data.get('candidate')
    nonce = secrets.token_hex(16)
    timestamp = int(time.time())

    decoded = verify_jwt(token)
    if not decoded or decoded['role'] != 'voter' or decoded['username'] != username:
        return jsonify({'error': 'Invalid token or role'}), 403

    c.execute('SELECT role FROM users WHERE username = ?', (username,))
    if c.fetchone() is None:
        return jsonify({'error': 'Invalid voter'}), 400

    c.execute('SELECT role FROM users WHERE username = ?', (candidate,))
    if c.fetchone() is None:
        return jsonify({'error': 'Invalid candidate'}), 400

    # Prevent double voting by checking decrypted records
    c.execute('SELECT encrypted_data FROM votes')
    for row in c.fetchall():
        try:
            decrypted_vote = decrypt_data(row[0])
            if decrypted_vote['voter'] == username:
                return jsonify({'error': 'Voter has already cast their vote'}), 403
        except:
            continue

    encrypted_vote = encrypt_data(1)
    signature = sign_vote(1, username)
    mac = generate_hmac(username, candidate, nonce)

    full_vote_data = {
        'voter': username,
        'candidate': candidate,
        'vote': str(encrypted_vote),
        'nonce': nonce,
        'timestamp': timestamp,
        'signature': signature.hex(),
        'mac': mac
    }

    encrypted_payload = encrypt_data(full_vote_data)

    c.execute('''
        INSERT INTO votes (encrypted_data, timestamp)
        VALUES (?, ?)
    ''', (encrypted_payload, timestamp))

    c.execute("UPDATE users SET has_voted = 1 WHERE username = ?", (username,))
    conn.commit()

    return jsonify({'message': f'Vote cast successfully by {username} for {candidate}'})


@app.route('/votes', methods=['GET'])
def get_votes():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Authorization header missing or malformed"}), 401

    token = auth_header.split(" ")[1]  # Extract the token
    decoded = verify_jwt(token)
    if not decoded or decoded['role'] != 'voter':
        return jsonify({'error': 'Unauthorized'}), 403
    
    # Fetch candidates and votes
    c.execute("SELECT username FROM users WHERE role = 'candidate'")
    candidates = [row[0] for row in c.fetchall()]
    tally = {candidate: 0 for candidate in candidates}

    c.execute('SELECT candidate_name FROM votes')
    for row in c.fetchall():
        if row[0] in tally:
            tally[row[0]] += 1

    return jsonify({'live_results': tally})

# For Future Work where we can integrate Paillier Encryption Algorithm

# @app.route('/tally', methods=['POST'])
# def tally_votes():
#     token = request.headers.get('Authorization')
#     if token:
#         token = token.replace("Bearer ", "")
    
#     decoded = verify_jwt(token)
#     if not decoded or decoded['role'] != 'admin':
#         return jsonify({'error': 'Unauthorized'}), 403
    
#     c.execute('SELECT encrypted_vote FROM votes')
#     encrypted_votes = [int(row[0]) for row in c.fetchall()]
    
#     encrypted_tally = encrypted_votes[0]
#     for enc_vote in encrypted_votes[1:]:
#         encrypted_tally += enc_vote

#     # Decrypt once at the end
#     decrypted_tally = private_key.decrypt(encrypted_tally)

#     return jsonify({'tally': decrypted_tally})

@app.route('/results_new', methods=['GET'])
def get_results_new():
    c.execute("SELECT username FROM users WHERE role = 'candidate'")
    candidates = [row[0] for row in c.fetchall()]
    tally = {candidate: 0 for candidate in candidates}

    c.execute('SELECT encrypted_data FROM votes')
    encrypted_rows = c.fetchall()
    for row in encrypted_rows:
        vote_data = decrypt_data(row[0])
        candidate = vote_data['candidate']
        if candidate in tally:
            tally[candidate] += 1

    return jsonify({'Final Results': tally})

@app.route('/live_results', methods=['GET'])
def live_results():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Authorization header missing or malformed"}), 401

    token = auth_header.split(" ")[1]
    decoded = verify_jwt(token)

    if not decoded or decoded['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403

    c.execute("SELECT username FROM users WHERE role = 'candidate'")
    candidates = [row[0] for row in c.fetchall()]
    tally = {candidate: 0 for candidate in candidates}

    c.execute('SELECT encrypted_data FROM votes')
    encrypted_rows = c.fetchall()
    for row in encrypted_rows:
        vote_data = decrypt_data(row[0])
        candidate = vote_data['candidate']
        if candidate in tally:
            tally[candidate] += 1

    return jsonify({'live_results': tally})

@app.route('/shutdown', methods=['POST'])
def shutdown():
    data = request.json
    token = data.get('token')
    decoded = verify_jwt(token)
    if not decoded or decoded['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    os._exit(0)
    return jsonify({'message': 'Shutting down the server'})

@app.route('/', methods=['GET'])
def health_check():
    return jsonify({"status": "running"}), 200

if __name__ == '__main__':
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile='certificates/cert.pem', keyfile='certificates/key.pem')
    # app.run(host='0.0.0.0', port=5000, ssl_context=context)
    app.run(host='127.0.0.1', port=5000, debug=True)
    # register_admin('admin', 'admin', 'admin')
