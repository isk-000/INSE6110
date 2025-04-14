# SecVote – Secure E-Voting System

A cryptographically secure electronic voting system prototype built using Python, Flask, and SQLite. The system ensures confidentiality, integrity, authenticity, and privacy using industry-standard algorithms like AES-256, RSA, HMAC-SHA256, and JWT.

---

## Features

- **Confidential Voting**: Votes are encrypted using AES-256.
- **Double Voting Prevention**: Decryption-based validation checks if a voter has already voted.
- **Digital Signatures**: Each vote is digitally signed using RSA.
- **Integrity Protection**: Every vote is protected by an HMAC.
- **Encrypted Metadata**: Signature, MAC, and nonce are stored encrypted with the vote.
- **JWT Authentication**: Stateless role-based access for voters, candidates, and admin.
- **Automatic Tally Display**: Final results shown after all voters cast their ballots.
- **REST API**: Exposes endpoints for registration, login, voting, result viewing, and admin operations.

---

## Cryptographic Design

| Purpose                | Algorithm                          |
|------------------------|------------------------------------|
| Vote Confidentiality   | AES-256                            |
| Vote Authenticity      | RSA Digital Signatures             |
| Data Integrity         | HMAC-SHA256                        |
| Session Authentication | JWT (HS256)                        |
| Secure Storage         | Fernet (AES symmetric)             |

---

## Setup Instructions

### Requirements
- Python 3.9+
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```

### Note: In case running on localhost:5000 is unauthorized, then you may need to kill any processes listening on that port or use another one for all endpoints (e.g., 5001).

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

### Future Work
The project can be extended to use Holomorphic encryption algorithms like Paillier Cryptosystem in order to ensure anonymity of the voters 
throughout the tallying process, in case the voting options were more diverse. However, since this prototype uses simple counters for voting as a POC, the algorithm need not be utilized at the moment.

## Author

**Osama Iskandarani**  
Course Name: INSE 6110: Foundations of Cryptography <br />
Instructor: Dr. Ayda Basyouni <br />
Concordia University, Canada – April 2025
