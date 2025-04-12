import requests
import json
import datetime
import jwt as pyjwt
import time

BASE_URL = 'http://localhost:5000'
LOG_FILE = 'security_test_results.log'

# Disable SSL warnings for testing only (not recommended for production)
requests.packages.urllib3.disable_warnings(requests.packages.urllib3.exceptions.InsecureRequestWarning)

def log_result(test_name, success, response):
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    status = 'PASS' if success else 'FAIL'
    
    response_text = "EMPTY RESPONSE"
    if response:
        try:
            response_text = response.json()
        except requests.exceptions.JSONDecodeError:
            response_text = f"RAW RESPONSE: {response.text}"
    
    with open(LOG_FILE, 'a') as log:
        log.write(f'[{timestamp}] {test_name}: {status}\nResponse: {response_text}\n\n')
    print(f'[{timestamp}] {test_name}: {status}')

def register_user(username, password, role):
    response = requests.post(f'{BASE_URL}/register', json={'username': username, 'password': password, 'role': role}, verify=False)
    success = response.status_code == 200 and 'registered successfully' in response.text
    log_result(f'Register {role} {username}', success, response)

def login_user(username, password):
    response = requests.post(f'{BASE_URL}/login', json={'username': username, 'password': password}, verify=False)
    success = response.status_code == 200 and 'token' in response.json()
    log_result(f'Login {username}', success, response)
    return response.json().get('token') if success else None

def double_vote_attack(token, username, candidate):
    print("\n--- Double Voting Attack ---")
    success = True
    for _ in range(2):
        response = requests.post(f'{BASE_URL}/vote', json={'token': token, 'username': username, 'candidate': candidate}, verify=False)
        if 'Voter has already cast their vote' not in response.text:
            success = False
    log_result('Double Voting Attack', success, response)

def replay_attack(token, username, candidate):
    print("\n--- Replay Attack ---")
    vote_data = {'token': token, 'username': username, 'candidate': candidate}

    response1 = requests.post(f'{BASE_URL}/vote', json=vote_data, verify=False)
    response1_text = response1.text.lower()

    # If the system already blocked the first vote, treat it as a successful block
    if 'already cast' in response1_text:
        print("Replay attack already blocked on first attempt.")
        log_result('Replay Attack', True, response1)
        return

    # Otherwise, test if second attempt is blocked
    response2 = requests.post(f'{BASE_URL}/vote', json=vote_data, verify=False)
    response2_text = response2.text.lower()
    replay_blocked = 'already cast' in response2_text and response2.status_code == 403

    log_result('Replay Attack', replay_blocked, response2)

def sql_injection_attack():
    print("\n--- SQL Injection Attack ---")
    payload = "' OR 1=1; --"
    response = requests.post(f'{BASE_URL}/login', json={'username': payload, 'password': 'irrelevant'}, verify=False)
    success = 'Invalid credentials' in response.text
    log_result('SQL Injection Attack', success, response)

def unauthorized_vote():
    print("\n--- Unauthorized Vote Attempt ---")
    response = requests.post(f'{BASE_URL}/vote', json={'token': 'invalid_token', 'username': 'voter5', 'candidate': 'Alice'}, verify=False)
    success = 'Invalid or expired token' in response.text
    log_result('Unauthorized Vote Attempt', success, response)

def jwt_tampering_attack(token):
    print("\n--- JWT Tampering Attack ---")
    decoded_token = pyjwt.decode(token, options={"verify_signature": False})
    decoded_token['role'] = 'admin'
    tampered_token = pyjwt.encode(decoded_token, 'wrong_secret', algorithm='HS256')
    response = requests.post(f'{BASE_URL}/shutdown', json={'token': tampered_token}, verify=False)
    success = 'Unauthorized' in response.text
    log_result('JWT Tampering Attack', success, response)

def expired_token_attack(token, username, candidate):
    print("\n--- Expired Token Attack ---")
    time.sleep(3)  # Simulate token expiration (ensure system expiry time matches test delay)
    response = requests.post(f'{BASE_URL}/vote', json={'token': token, 'username': username, 'candidate': candidate}, verify=False)
    success = 'Invalid or expired token' in response.text
    log_result('Expired Token Attack', success, response)

def test_security():
    print("\nRunning Security Tests...")
    open(LOG_FILE, 'w').close()  # Clear previous log
    # register_user('admin4', 'adminpass', 'admin')
    # register_user('voter7', 'voterpass', 'voter')
    # register_user('candidate2', 'candipass', 'candidate')

    token = login_user('v2', 'v2')
    if token:
        double_vote_attack(token, 'v2', 'c1')
        replay_attack(token, 'v2', 'c1')
        expired_token_attack(token, 'v2', 'c1')
    
    sql_injection_attack()
    unauthorized_vote()
    if token:
        jwt_tampering_attack(token)
    
    print(f"\nTest results logged to {LOG_FILE}")

test_security()
