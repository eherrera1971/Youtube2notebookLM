import sys
import os
from youtube_manager import YouTubeManager
from notebooklm_bot import NotebookLMBot

def main():
    print("Starting YouTube -> NotebookLM Automation")
    
    # 1. Setup YouTube
    try:
        yt = YouTubeManager()
    except Exception as e:
        print(f"Failed to initialize YouTube Manager: {e}")
        return

    # 2. Get Videos
    print("Fetching videos from 'Celeste' playlist...")
    videos = yt.get_playlist_videos("Celeste")
    
    if not videos:
        print("No videos found in playlist 'Celeste'. Exiting.")
        return
    
    print(f"Found {len(videos)} videos to process.")

    # 3. Setup NotebookLM Bot
    # Headless is False so user can see/login
    bot = NotebookLMBot(headless=False)

    # 4. Process Loop
    for video in videos:
        print(f"\nProcessing: {video['title']}")
        print(f"URL: {video['url']}")
        
        success = bot.create_notebook_and_add_source(video['url'])
        
        if success:
            print("Successfully added to NotebookLM.")
            # Remove from playlist
            yt.remove_video_from_playlist(video['playlist_item_id'])
        else:
            print("Failed to add to NotebookLM. Skipping removal.")

    print("\nAll tasks completed.")

if __name__ == "__main__":
    if not os.path.exists("client_secret.json"):
        print("ERROR: client_secret.json not found. Please place it in this directory.")
        sys.exit(1)
        
    main()
