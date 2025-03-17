#!/bin/bash

# Function to check if Flask server is running
check_server() {
  curl -k --silent --head https://localhost:5000 | grep "HTTP" > /dev/null
  return $?
}

# Start Flask server if not running
if ! check_server; then
  echo "Starting Flask server..."
  nohup python src/inse6110_voting_system.py > flask.log 2>&1 &
  FLASK_PID=$!
  sleep 3
  if ! check_server; then
    echo "Failed to start Flask server. Check flask.log for details."
    exit 1
  fi
else
  echo "Flask server is already running."
fi

# Main menu
while true; do
  clear
  echo "==================================="
  echo "      Secure Voting System       "
  echo "==================================="
  echo "1) Register a new user"
  echo "2) Login"
  echo "3) Add a candidate"
  echo "4) Vote for a candidate"
  echo "5) View live results"
  echo "6) Exit"
  echo "==================================="
  read -p "Select an option [1-6]: " choice

  case $choice in
    1)
      ./scripts/register.sh
      ;;
    2)
      ./scripts/login.sh
      ;;
    3)
      ./scripts/add_candidate.sh
      ;;
    4)
      ./scripts/vote.sh
      ;;
    5)
      ./scripts/live_results.sh
      ;;
    6)
      echo "Exiting... (Flask server will keep running)"
      exit 0
      ;;
    *)
      echo "Invalid option. Please select a number between 1-6."
      ;;
  esac

  read -p "Press Enter to continue..."
done
