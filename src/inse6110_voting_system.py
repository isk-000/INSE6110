import os
import json
import sqlite3
import time
import secrets
import jwt as pyjwt
from flask import Flask, request, jsonify
from phe import paillier
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

# Generate Paillier key pair for homomorphic encryption
public_key, private_key = paillier.generate_paillier_keypair()

# RSA keys for digital signatures
rsa_public_key, rsa_private_key = rsa.newkeys(512)

# AES-256 key generation
aes_key = Fernet.generate_key()
cipher = Fernet(aes_key)

# SQLite database setup
db_path = 'database/voting_system.db'

# Delete the database file to simulate a new voting session.
if os.path.exists(db_path):
    os.remove(db_path)

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
                voter_username TEXT UNIQUE,
                candidate_name TEXT,
                encrypted_vote TEXT,
                signature TEXT,
                mac TEXT,
                nonce TEXT UNIQUE,
                timestamp INTEGER,
                FOREIGN KEY (voter_username) REFERENCES users(username),
                FOREIGN KEY (candidate_name) REFERENCES candidates(name)
             )''')

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

# def verify_hmac(message, mac):
#     expected_mac = generate_hmac(message)
#     return hmac.compare_digest(expected_mac, mac)

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

@app.route('/all_voters_voted', methods=['GET'])
def all_voters_voted():
    c.execute("SELECT COUNT(*) FROM users WHERE role = 'voter'")
    total_voters = c.fetchone()[0]
    
    c.execute("SELECT COUNT(*) FROM users WHERE role = 'voter' AND has_voted = TRUE")
    voted_voters = c.fetchone()[0]

    return jsonify({
        'all_voted': total_voters == voted_voters,
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
    if not decoded or decoded['role'] != 'voter':
        return jsonify({'error': 'Invalid or expired token'}), 403

    # Enforce that token's user matches the provided username
    if decoded['username'] != username:
        return jsonify({'error': 'Token does not match username'}), 403

    # Ensure the voter exists and has voter role
    c.execute('SELECT role FROM users WHERE username = ?', (username,))
    row = c.fetchone()
    if not row or row[0] != 'voter':
        return jsonify({'error': 'Invalid voter'}), 400

    # Ensure the candidate exists and is a candidate
    c.execute("SELECT role FROM users WHERE username = ?", (candidate,))
    candidate_row = c.fetchone()
    if not candidate_row or candidate_row[0] != 'candidate':
        return jsonify({'error': 'Invalid candidate'}), 400

    # Prevent double voting
    c.execute('SELECT * FROM votes WHERE voter_username = ?', (username,))
    if c.fetchone():
        return jsonify({'error': 'Voter has already cast their vote'}), 403

    encrypted_vote = public_key.encrypt(1)
    signature = sign_vote(1, username)
    mac = generate_hmac(username, candidate, nonce)

    c.execute('''
        INSERT INTO votes (voter_username, candidate_name, encrypted_vote, signature, mac, nonce, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (username, candidate, str(encrypted_vote.ciphertext()), signature.hex(), mac, nonce, timestamp))

    c.execute("UPDATE users SET has_voted = 1 WHERE username = ?", (username,))
    conn.commit()

    return jsonify({'message': f'Vote cast successfully by {username} for {candidate}'})
    
@app.route('/results_new', methods=['GET'])
def get_results_new():
    # conn = get_db_connection()
    # c = conn.cursor()
    # Fetch candidates and votes
    c.execute("SELECT username FROM users WHERE role = 'candidate'")
    candidates = [row[0] for row in c.fetchall()]
    tally = {candidate: 0 for candidate in candidates}

    c.execute('SELECT candidate_name FROM votes')
    for row in c.fetchall():
        if row[0] in tally:
            tally[row[0]] += 1
    print("tally: ", tally)

    return jsonify({'Final Results': tally})


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

@app.route('/tally', methods=['POST'])
def tally_votes():
    token = request.headers.get('Authorization')
    if token:
        token = token.replace("Bearer ", "")
    
    decoded = verify_jwt(token)
    if not decoded or decoded['role'] != 'admin':
        return jsonify({'error': 'Unauthorized'}), 403
    
    c.execute('SELECT encrypted_vote FROM votes')
    encrypted_votes = [int(row[0]) for row in c.fetchall()]
    
    if not encrypted_votes:
        return jsonify({'error': 'No votes found'}), 404
    
    decrypted_tally = sum([private_key.decrypt(public_key.raw_encrypt(vote)) for vote in encrypted_votes])
    return jsonify({'tally': decrypted_tally})

@app.route('/live_results', methods=['GET'])
def live_results():
    auth_header = request.headers.get('Authorization')
    if not auth_header or not auth_header.startswith('Bearer '):
        return jsonify({"error": "Authorization header missing or malformed"}), 401

    token = auth_header.split(" ")[1]  # Extract the token
    decoded = verify_jwt(token)

    if not decoded or decoded['role'] != 'admin':
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
    app.run(host='127.0.0.1', port=5001, debug=True)
