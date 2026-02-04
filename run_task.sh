#!/bin/bash

# Configuration
PROJECT_DIR="/Users/eherrera/Proyectos/Y2NLM"
LOG_FILE="$PROJECT_DIR/automation.log"

# Navigate to project directory
cd "$PROJECT_DIR" || exit 1

# Activate virtual environment (optional if calling python directly, but good practice)
source venv/bin/activate

# Timestamp
echo "--- Starting run at $(date) ---" >> "$LOG_FILE"

# Run the script
# We filter grep/awk noise if any, or just capture all output
./venv/bin/python main.py >> "$LOG_FILE" 2>&1

echo "--- Finished run at $(date) ---" >> "$LOG_FILE"
