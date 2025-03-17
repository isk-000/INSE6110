import os
import json
import sqlite3
from flask import Flask, request, jsonify
from phe import paillier
import bcrypt
import rsa
import hashlib
import hmac
import ssl
from cryptography.fernet import Fernet

# Initialize Flask app
app = Flask(__name__)

# Generate Paillier key pair for homomorphic encryption
public_key, private_key = paillier.generate_paillier_keypair()

# RSA keys for digital signatures
rsa_public_key, rsa_private_key = rsa.newkeys(512)

# AES-256 key generation
aes_key = Fernet.generate_key()
cipher = Fernet(aes_key)

# HMAC key for integrity checks
hmac_key = os.urandom(32)

# SQLite database setup
db_path = 'database/voting_system.db'
conn = sqlite3.connect(db_path, check_same_thread=False)
c = conn.cursor()

# Create tables
c.execute('''CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE,
                password TEXT,
                role TEXT CHECK(role IN ('voter', 'candidate', 'admin'))
             )''')

c.execute('''CREATE TABLE IF NOT EXISTS candidates (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE
             )''')

c.execute('''CREATE TABLE IF NOT EXISTS votes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                voter_username TEXT UNIQUE,
                candidate_name TEXT,
                encrypted_vote TEXT,
                signature TEXT,
                mac TEXT,
                FOREIGN KEY (voter_username) REFERENCES users(username),
                FOREIGN KEY (candidate_name) REFERENCES candidates(name)
             )''')

conn.commit()

def hash_password(password):
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode('utf-8'), hashed)

def sign_vote(vote):
    vote_hash = hashlib.sha256(str(vote).encode()).digest()
    return rsa.sign(vote_hash, rsa_private_key, 'SHA-256')

def encrypt_data(data):
    return cipher.encrypt(json.dumps(data).encode('utf-8'))

def decrypt_data(encrypted_data):
    return json.loads(cipher.decrypt(encrypted_data).decode('utf-8'))

def generate_hmac(message):
    return hmac.new(hmac_key, message.encode('utf-8'), hashlib.sha256).hexdigest()

def verify_hmac(message, mac):
    expected_mac = generate_hmac(message)
    return hmac.compare_digest(expected_mac, mac)

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
    return jsonify({'message': f'Login successful for {username}', 'role': result[1]})

@app.route('/add_candidate', methods=['POST'])
def add_candidate():
    data = request.json
    name = data.get('name')
    try:
        c.execute('INSERT INTO candidates (name) VALUES (?)', (name,))
        conn.commit()
        return jsonify({'message': f'Candidate {name} added successfully'})
    except sqlite3.IntegrityError:
        return jsonify({'error': 'Candidate already exists'}), 400

@app.route('/vote', methods=['POST'])
def vote():
    data = request.json
    username = data.get('username')
    candidate = data.get('candidate')
    c.execute('SELECT role FROM users WHERE username = ?', (username,))
    result = c.fetchone()
    if not result or result[0] != 'voter':
        return jsonify({'error': 'Only voters can cast ballots'}), 403
    c.execute('SELECT name FROM candidates WHERE name = ?', (candidate,))
    if not c.fetchone():
        return jsonify({'error': 'Invalid candidate'}), 400
    c.execute('SELECT * FROM votes WHERE voter_username = ?', (username,))
    if c.fetchone():
        return jsonify({'error': 'Voter has already cast their vote'}), 403
    encrypted_vote = public_key.encrypt(1)  # Each vote counts as 1
    signature = sign_vote(1)
    mac = generate_hmac(candidate)
    c.execute('INSERT INTO votes (voter_username, candidate_name, encrypted_vote, signature, mac) VALUES (?, ?, ?, ?, ?)', (username, candidate, str(encrypted_vote.ciphertext()), signature.hex(), mac))
    conn.commit()
    return jsonify({'message': f'Vote cast successfully by {username} for {candidate}'})

@app.route('/votes', methods=['GET'])
def get_votes():
    c.execute('SELECT * FROM votes')
    votes = [{'id': row[0], 'voter': row[1], 'candidate': row[2], 'encrypted_vote': row[3]} for row in c.fetchall()]
    return jsonify(votes)

@app.route('/candidates', methods=['GET'])
def get_candidates():
    c.execute('SELECT name FROM candidates')
    candidates = [row[0] for row in c.fetchall()]
    return jsonify(candidates)

@app.route('/live_results', methods=['GET'])
def live_results():
    c.execute('SELECT candidate_name, COUNT(*) FROM votes GROUP BY candidate_name')
    results = {row[0]: row[1] for row in c.fetchall()}
    return jsonify(results)

if __name__ == '__main__':
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(certfile='certificates/cert.pem', keyfile='certificates/key.pem')
    app.run(host='0.0.0.0', port=5000, ssl_context=context)
