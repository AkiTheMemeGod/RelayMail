#!/bin/bash

# Configuration
API_URL="http://localhost:5001/api/v1/send"
API_KEY="l9Vb3qkUrErbCjoMFdD0oUF2Pq5AtwugzMhLbgbrCPc"  # Corrected key from DB check

if [ "$API_KEY" == "YOUR_API_KEY_HERE" ]; then
    echo "Error: Please edit this script and set your API_KEY"
    exit 1
fi

echo "Sending test email..."

curl -X POST "$API_URL" \
  -H "Authorization: Bearer $API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "shrimithaakishared@gmail.com",
    "subject": "Test from RelayMail CLI",
    "body": "This is a test email sent via the RelayMail test script."
  }'

echo -e "\nDone."
