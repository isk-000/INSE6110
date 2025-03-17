#!/bin/bash

read -p "Enter your username: " username
read -p "Enter candidate's name you want to vote for: " candidate

curl -X POST https://localhost:5000/vote \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"$username\", \"candidate\": \"$candidate\"}" -k
