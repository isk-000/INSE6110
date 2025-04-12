# SecVote – Secure E-Voting System

A cryptographically secure electronic voting system prototype built using Python, Flask, and SQLite. The system ensures confidentiality, integrity, authenticity, and privacy using industry-standard algorithms like AES-256, RSA, Paillier homomorphic encryption, HMAC-SHA256, and JWT.

---

## Features

- **Confidential Voting**: Votes are encrypted using Paillier and AES-256.
- **Double Voting Prevention**: Decryption-based validation checks if a voter has already voted.
- **Digital Signatures**: Each vote is digitally signed using RSA.
- **Integrity Protection**: Every vote is protected by an HMAC.
- **Encrypted Metadata**: Signature, MAC, and nonce are stored encrypted with the vote.
- **JWT Authentication**: Stateless role-based access for voters, candidates, and admin.
- **Automatic Tally Display**: Final results shown after all voters cast their ballots.
- **REST API**: Exposes endpoints for registration, login, voting, result viewing, and admin operations.

---

## Cryptographic Design

| Purpose              | Algorithm                          |
|----------------------|------------------------------------|
| Vote Confidentiality | Paillier (Homomorphic) + AES-256   |
| Vote Authenticity    | RSA Digital Signatures             |
| Data Integrity       | HMAC-SHA256                        |
| Session Authentication | JWT (HS256)                      |
| Secure Storage       | Fernet (AES symmetric)             |

---

## Setup Instructions

### Requirements
- Python 3.9+
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```

### Project Structure
```
secure-voting-system/
├── src/
│   └── inse6110_voting_system.py
├── scripts/
│   ├── main_menu.sh
│   └── *.sh (login/register scripts)
├── database/
│   └── voting_system.db
├── certificates/
│   ├── cert.pem
│   └── key.pem
└── tests/
```

### Run the Server
```bash
python src/inse6110_voting_system.py
```

### Launch Voting Interface
```bash
bash scripts/main_menu.sh
```

---

## Security Highlights

- **Encrypted Payloads**: The entire vote, including metadata (candidate, nonce, mac, signature), is encrypted before storage.
- **JWT-Based Access Control**: Admin-only result tallying.
- **Replay Attack Protection**: Unique nonce in each vote.
- **Auditability**: All votes are signed and timestamped.

---

## Testing

Run test scripts from the `tests/` directory to validate:

- Authentication
- Replay protection
- Signature integrity
- Encrypted vote format

---

## Author

**Osama Iskandarani**  
Course Name: INSE 6110: Foundations of Cryptography
Instructor: Dr. Ayda Basyouni
Concordia University, Canada – April 2025
