#!/bin/bash

# Exit on error
set -e

# Ensure venv directory exists
if [ ! -d "venv" ]; then
  echo "Creating virtual environment..."
  python -m venv venv
fi

# Activate virtual environment
if [ -f "venv/bin/activate" ]; then
  source venv/bin/activate
elif [ -f "venv/Scripts/activate" ]; then
  source venv/Scripts/activate
else
  echo "Failed to find venv activation script. Exiting."
  exit 1
fi

# Force pip upgrade (cross-platform)
echo "Upgrading pip..."
python -m pip install --upgrade pip

# Install dependencies
echo "Installing dependencies..."
pip install -r src/requirements.txt

# Run unit tests
echo "Running unit tests..."
PYTHONPATH=src python -m unittest discover -s tests -p 'test_*.py'

# Generate TLS certificates
mkdir -p certificates
if [ ! -f certificates/cert.pem ] || [ ! -f certificates/key.pem ]; then
  echo "Generating TLS certificates..."
  openssl req -x509 -newkey rsa:4096 -keyout certificates/key.pem -out certificates/cert.pem -days 365 -nodes -subj "/CN=localhost"
fi

# Clear old database
mkdir -p database
if [ -f database/voting_system.db ]; then
  echo "Removing old database..."
  rm database/voting_system.db
fi

# Run Flask app in the background
echo "Starting Flask app..."
python src/inse6110_voting_system.py &
FLASK_PID=$!

# Wait for Flask app to start (max 10 seconds)
echo "Waiting for Flask app to start..."
for i in {1..10}; do
  if curl -k https://localhost:5000/ &>/dev/null; then
    echo "Flask app is up!"
    break
  fi
  echo "Waiting for server... ($i sec)"
  sleep 1
done

# If still not up, exit
if ! curl -k https://localhost:5000/ &>/dev/null; then
  echo "Flask app failed to start. Exiting."
  kill $FLASK_PID
  exit 1
fi

# Register users
echo "Registering users..."
curl -X POST https://localhost:5000/register \
  -H "Content-Type: application/json" \
  -d '{"username": "voter1", "password": "securepass", "role": "voter"}' -k

curl -X POST https://localhost:5000/register \
  -H "Content-Type: application/json" \
  -d '{"username": "candidate1", "password": "securepass", "role": "candidate"}' -k

curl -X POST https://localhost:5000/register \
  -H "Content-Type: application/json" \
  -d '{"username": "admin1", "password": "adminpass", "role": "admin"}' -k

# Voter login
echo "Logging in voter1..."
curl -X POST https://localhost:5000/login \
  -H "Content-Type: application/json" \
  -d '{"username": "voter1", "password": "securepass"}' -k

# Cast a vote
echo "Casting vote for voter1..."
VOTE_RESPONSE=$(curl -X POST https://localhost:5000/vote \
  -H "Content-Type: application/json" \
  -d '{"username": "voter1", "vote": 1}' -k)
echo "Vote response: $VOTE_RESPONSE"

# View encrypted votes
echo "Fetching encrypted votes..."
curl -X GET https://localhost:5000/votes -k

# Admin tallies the votes
echo "Admin tallying the votes..."
TALLY_RESPONSE=$(curl -X POST https://localhost:5000/tally \
  -H "Content-Type: application/json" \
  -d '{"username": "admin1"}' -k)
echo "Tally response: $TALLY_RESPONSE"

# Kill Flask server
echo "Stopping Flask server..."
kill $FLASK_PID

echo "Automation complete!"
