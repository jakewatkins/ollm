#!/bin/bash

# Start the Ollama server
launchctl load -w ~/Library/LaunchAgents/com.ollama.server.plist
echo "Ollama server has been started."