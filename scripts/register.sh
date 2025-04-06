#!/bin/bash

read -p "Enter username: " username
read -p "Enter password: " password
read -p "Enter role (voter/candidate/admin): " role

curl -X POST http://localhost:5000/register \
  -H "Content-Type: application/json" \
  -d "{\"username\": \"$username\", \"password\": \"$password\", \"role\": \"$role\"}" -k
