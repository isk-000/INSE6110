#!/bin/bash

read -p "Enter candidate name: " candidate

curl -X POST https://localhost:5000/add_candidate \
  -H "Content-Type: application/json" \
  -d "{\"name\": \"$candidate\"}" -k
