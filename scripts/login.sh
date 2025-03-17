#!/bin/bash

read -p "Enter username: " username
read -p "Enter password: " password

curl -X POST https://localhost:5000/login \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"$username\", \"password\": \"$password\"}" -k
