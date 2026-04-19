#!/usr/bin

# Stop the Ollama server
launchctl unload -w /Library/LaunchDaemons/com.ollama.server.plist
echo "Ollama server has been stopped."
