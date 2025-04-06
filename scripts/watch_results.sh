#!/bin/bash

while true; do
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
    echo "Voting in Progress"

    if [[ $voting_complete ]]; then
        echo "🎉 Voting complete. Fetching final results..."
        curl -s http://127.0.0.1:5000/results_new
        break
    fi

    sleep 2
done
