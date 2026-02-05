#!/bin/bash

# Define the user data directory for this manual profile
# We use the same one or a compatible one so cookies are saved.
# notebooklm_bot.py uses "browser_context" in the CWD if it launches it, 
# but if we connect via CDP, the profile is determined by the running instance.
# Let's use a specific directory "chrome_manual_profile" to keep it clean and persistent.
USER_DATA_DIR="$(pwd)/chrome_manual_profile"

mkdir -p "$USER_DATA_DIR"

echo "Launching Google Chrome with Remote Debugging on Port 9222..."
echo "User Data Directory: $USER_DATA_DIR"
echo ""
echo "IMPORTANT:"
echo "1. Chrome will open."
echo "2. Log in to your Google Account inside this new window."
echo "3. Leave this window OPEN."
echo "4. Return to your terminal and run './run_task.sh' or 'python main.py'"
echo ""

"/Applications/Google Chrome.app/Contents/MacOS/Google Chrome" \
  --remote-debugging-port=9222 \
  --user-data-dir="$USER_DATA_DIR" \
  --no-first-run \
  --no-default-browser-check \
  &

echo "Chrome launched in background (PID: $!)."
