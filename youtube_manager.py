import os
import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
import pickle
from google.auth.transport.requests import Request

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"
CLIENT_SECRETS_FILE = "client_secret.json"
TOKEN_FILE = "token.pickle"

class YouTubeManager:
    def __init__(self):
        self.youtube = self.authenticate()

    def authenticate(self):
        creds = None
        if os.path.exists(TOKEN_FILE):
            with open(TOKEN_FILE, 'rb') as token:
                creds = pickle.load(token)
        
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(CLIENT_SECRETS_FILE):
                     raise FileNotFoundError(f"Missing {CLIENT_SECRETS_FILE}. Please download it from Google Cloud Console.")

                flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                    CLIENT_SECRETS_FILE, SCOPES)
                creds = flow.run_local_server(port=0)
            
            with open(TOKEN_FILE, 'wb') as token:
                pickle.dump(creds, token)

        return googleapiclient.discovery.build(API_SERVICE_NAME, API_VERSION, credentials=creds)

    def get_playlist_videos(self, playlist_name="Celeste"):
        # 1. Find the playlist ID for "Celeste"
        request = self.youtube.playlists().list(
            part="snippet",
            mine=True,
            maxResults=50
        )
        response = request.execute()
        
        playlist_id = None
        for item in response.get("items", []):
            if item["snippet"]["title"] == playlist_name:
                playlist_id = item["id"]
                break
        
        if not playlist_id:
            print(f"Playlist '{playlist_name}' not found.")
            return []

        # 2. Get videos from the playlist
        videos = []
        request = self.youtube.playlistItems().list(
            part="snippet",
            playlistId=playlist_id,
            maxResults=50
        )
        
        while request:
            response = request.execute()
            for item in response.get("items", []):
                snippet = item["snippet"]
                video_id = snippet["resourceId"]["videoId"]
                videos.append({
                    "title": snippet["title"],
                    "video_id": video_id,
                    "url": f"https://www.youtube.com/watch?v={video_id}",
                    "playlist_item_id": item["id"]
                })
            
            request = self.youtube.playlistItems().list_next(request, response)
            
        return videos

    def remove_video_from_playlist(self, playlist_item_id):
        try:
            self.youtube.playlistItems().delete(id=playlist_item_id).execute()
            print(f"Removed video (playlistItem: {playlist_item_id}) from playlist.")
        except googleapiclient.errors.HttpError as e:
            print(f"Error removing video: {e}")

if __name__ == "__main__":
    # Test execution
    try:
        yt = YouTubeManager()
        videos = yt.get_playlist_videos()
        print(f"Found {len(videos)} videos.")
        for v in videos:
            print(f"- {v['title']}")
    except Exception as e:
        print(f"Setup incomplete or error: {e}")
