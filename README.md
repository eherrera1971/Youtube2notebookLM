# YouTube to NotebookLM Automation

This tool automates the process of adding videos from your "Celeste" YouTube playlist to NotebookLM as sources, and then removing them from the playlist.

## Features

-   **YouTube Integration**: Automatically fetches videos from a specific playlist ("Celeste").
-   **NotebookLM Automation**: Uses Playwright (connected to an existing Chrome instance) to create notebooks and add sources.
-   **Cleanup**: Removes the video from the YouTube playlist after successful addition.
-   **Infographic**: Tries to click the "Infografía" button after processing.

## Prerequisites

1.  **Python Environment**: Ensure you have Python 3 installed.
2.  **Google Chrome**: You must have Google Chrome installed.
3.  **Credentials**: `client_secret.json` must be in the project root (for YouTube API).

## Installation

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install
```

## How to Run

Because Google blocks automated browsers (appearing as "This browser is not secure"), we use a special method connecting to an existing Chrome window.

### Step 1: Open Chrome for Automation

Run this command in your terminal to open a special Chrome window listening for automation:

```bash
open -na "Google Chrome" --args --remote-debugging-port=9222 --user-data-dir="/tmp/chrome_dev_profile" --no-first-run
```

### Step 2: Log In

In the Chrome window that opens:
1.  Go to [notebooklm.google.com](https://notebooklm.google.com).
2.  **Log in** with your Google account.
3.  Ensure you can see your notebooks dashboard.

### Step 3: Run the Script

In your terminal (in the project folder), run:

```bash
./venv/bin/python main.py
```

### Step 4: Watch it Go

The script will:
1.  Connect to the Chrome window you opened.
2.  Fetch videos from your "Celeste" playlist.
3.  For each video:
    - Create a new notebook.
    - Add the video as a source.
    - Click "Infografía" (if available).
    - Remove the video from the YouTube playlist.

## Troubleshooting

-   **"Connection Refused"**: Ensure you ran the `open ...` command in Step 1 and the window is still open.
-   **"Verification Required"**: If Google asks for verification during login, just complete it manually in the browser window.
