#!/bin/bash
# use curl to test if the Ollama server is running
# usage: ./test-ollama-server.sh servername 

#set url
url="http://$1:11434/v1/models"

response=$(curl -s -o /dev/null -w "%{http_code}" "$url")
if [ "$response" -eq 200 ]; then
  echo "Ollama server is running and responded with status code 200."
else
  echo "Ollama server is not responding. Status code: $response"
fi

