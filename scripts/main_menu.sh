# !/bin/bash

# Check if Flask server is running
check_server() {
  curl -k --silent http://localhost:5000 | grep -q "running"
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

watch_results() {
  echo "Waiting for all voters to vote..."
  while true; do
    response=$(curl -s http://localhost:5000/all_voters_voted)
    all_voted=$(echo "$response" | grep -Po '"all_voted":\s*\K(true|false)')

    if [ "$all_voted" == "true" ]; then
      echo
      echo "==================================="
      echo "      ✅ All voters have voted!"
      echo "      📊 Final Voting Results"
      echo "==================================="
      curl -s -X GET http://localhost:5000/results_new
      echo
      read -p "Press Enter to end the session..." temp
      exit 0
    fi

    sleep 2
  done
}

TOKEN=""
LOGGED_IN=false

# Store JWT token after login
store_token() {
  TOKEN=$1
  LOGGED_IN=true
  echo "Token stored."
}

# Clear token and logout
logout() {
  TOKEN=""
  LOGGED_IN=false
  echo "You have been logged out."
}

# Main menu
while true; do
  watch_results &
  clear
  echo "==================================="
  echo "      Secure Voting System       "
  echo "==================================="
  if [ "$LOGGED_IN" = false ]; then
    echo "1) Register a new user"
    echo "2) Login"
  fi
  # echo "3) Add a candidate"
  echo "3) Vote for a candidate"
  echo "4) View live results"
  if [ "$LOGGED_IN" = true ]; then
    echo "5) Logout"
  else
    echo "5) Exit"
  fi
  echo "==================================="
  read -p "Select an option [1-6]: " choice

  case $choice in
    1)
      if [ "$LOGGED_IN" = false ]; then
        ./scripts/register.sh
      else
        echo "Already logged in. Logout first to register a new user."
      fi
      ;;
    2)
      if [ "$LOGGED_IN" = false ]; then
        LOGIN_RESPONSE=$(./scripts/login.sh)
        TOKEN=$(echo $LOGIN_RESPONSE | grep -Po '"token":\s*"\K[^"]+')

        if [ -n "$TOKEN" ]; then
          store_token $TOKEN
        else
          echo "Login failed."
        fi
      else
        echo "Already logged in."
      fi
      ;;
    # 3)
    #   ./scripts/add_candidate.sh
    #   ;;
    3)
      if [ -z "$TOKEN" ]; then
        echo "You must login first!"
      else
        echo "Fetching list of candidates..."
        response=$(curl -s -X GET http://localhost:5000/candidates -H "Content-Type: application/json" -k)
        echo "$response"

        read -p "Enter your username: " username
        read -p "Enter candidate's name you want to vote for: " candidate

        vote_response=$(curl -s -X POST http://localhost:5000/vote \
          -H "Content-Type: application/json" \
          -d "{\"token\": \"$TOKEN\", \"username\": \"$username\", \"candidate\": \"$candidate\"}" -k)

        echo "$vote_response"

        # Check if all voters have now voted
        check=$(curl -s http://localhost:5000/all_voters_voted)
        all_voted=$(echo $check | grep -Po '"all_voted":\s*\K(true|false)')

        if [ "$all_voted" = "true" ]; then
          echo
          echo "==================================="
          echo "   All voters have voted! Showing results:"
          echo "==================================="
          curl -X GET http://localhost:5000/votes \
          -H "Authorization: Bearer $TOKEN" \
          -H "Content-Type: application/json" -k
          echo
          read -p "Press Enter to end session..." temp
          exit 0
        fi
      fi
      ;;
    4)
      if [ -z "$TOKEN" ]; then
        echo "You must login first!"
      else
        curl -X GET http://localhost:5000/live_results \
          -H "Authorization: Bearer $TOKEN" \
          -H "Content-Type: application/json" -k
        echo
        read -p "Press Enter to end session..." temp
        exit 0
      fi
      ;;
    5)
      if [ "$LOGGED_IN" = true ]; then
        logout
      else
        echo "Exiting... (Flask server will keep running)"
        exit 0
      fi
      ;;
    *)
      echo "Invalid option. Please select a valid number."
      ;;
  esac

  read -p "Press Enter to continue..." temp

done
