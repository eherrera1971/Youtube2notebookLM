import os
import pickle
import sys
import time

import google_auth_oauthlib.flow
import googleapiclient.discovery
import googleapiclient.errors
from google.auth.transport.requests import Request

from env_loader import load_dotenv

SCOPES = ["https://www.googleapis.com/auth/youtube.force-ssl"]
API_SERVICE_NAME = "youtube"
API_VERSION = "v3"
CLIENT_SECRETS_FILE = "client_secret.json"
TOKEN_FILE = "token.pickle"


class YouTubeManager:
    def __init__(self, base_dir=None):
        # Rutas absolutas: el script debe funcionar desde cualquier directorio
        # de trabajo (importante para cron).
        self.base_dir = base_dir or os.path.dirname(os.path.abspath(__file__))
        self.client_secrets_path = os.path.join(self.base_dir, CLIENT_SECRETS_FILE)
        self.token_path = os.path.join(self.base_dir, TOKEN_FILE)
        self.youtube = self.authenticate()

    def authenticate(self):
        creds = None
        if os.path.exists(self.token_path):
            try:
                with open(self.token_path, "rb") as token:
                    creds = pickle.load(token)
            except Exception as e:
                print(f"Token ilegible ({e}); se descarta.")
                creds = None

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    print(f"Falló la renovación del token: {e}")
                    print("Se borra el token vencido y se re-autentica...")
                    try:
                        os.remove(self.token_path)
                    except OSError:
                        pass
                    creds = None

            if creds is None or not creds.valid:
                if not os.path.exists(self.client_secrets_path):
                    raise FileNotFoundError(
                        f"Falta {self.client_secrets_path}. "
                        "Descárgalo desde Google Cloud Console."
                    )

                # El flujo OAuth abre un navegador: sin terminal interactiva
                # (cron) se quedaría colgado para siempre. Mejor fallar claro.
                if not sys.stdin.isatty():
                    raise RuntimeError(
                        "Se requiere autorización de Google y no hay terminal "
                        "interactiva. Ejecuta './bin/run --check' manualmente "
                        "una vez para renovar el acceso."
                    )

                flow = google_auth_oauthlib.flow.InstalledAppFlow.from_client_secrets_file(
                    self.client_secrets_path, SCOPES
                )
                creds = flow.run_local_server(
                    port=0, access_type="offline", prompt="consent"
                )

            with open(self.token_path, "wb") as token:
                pickle.dump(creds, token)

        return googleapiclient.discovery.build(
            API_SERVICE_NAME, API_VERSION, credentials=creds
        )

    def _find_playlist_id(self, playlist_name):
        """Busca la playlist por nombre, recorriendo todas las páginas."""
        request = self.youtube.playlists().list(part="snippet", mine=True, maxResults=50)
        while request:
            response = request.execute()
            for item in response.get("items", []):
                if item["snippet"]["title"] == playlist_name:
                    return item["id"]
            request = self.youtube.playlists().list_next(request, response)
        return None

    def get_playlist_videos(self, playlist_name="Celeste"):
        playlist_id = self._find_playlist_id(playlist_name)
        if not playlist_id:
            print(f"No se encontró la playlist '{playlist_name}'.")
            return []

        videos = []
        request = self.youtube.playlistItems().list(
            part="snippet,status", playlistId=playlist_id, maxResults=50
        )

        while request:
            response = request.execute()
            for item in response.get("items", []):
                snippet = item["snippet"]
                resource = snippet.get("resourceId", {})
                video_id = resource.get("videoId")
                if not video_id:
                    continue

                # Videos borrados o privados no tienen transcripción utilizable
                privacy = item.get("status", {}).get("privacyStatus")
                if privacy in ("private", "privacyStatusUnspecified"):
                    print(f"  Omitido (video {privacy}): {snippet.get('title')}")
                    continue
                if snippet.get("title") in ("Deleted video", "Private video"):
                    print(f"  Omitido (no disponible): {snippet.get('title')}")
                    continue

                videos.append(
                    {
                        "title": snippet["title"],
                        "video_id": video_id,
                        "url": f"https://www.youtube.com/watch?v={video_id}",
                        "playlist_item_id": item["id"],
                    }
                )

            request = self.youtube.playlistItems().list_next(request, response)

        return videos

    def remove_video_from_playlist(self, playlist_item_id, retries=3):
        for attempt in range(1, retries + 1):
            try:
                self.youtube.playlistItems().delete(id=playlist_item_id).execute()
                print(f"  Eliminado de la playlist (item: {playlist_item_id}).")
                return True
            except (ConnectionResetError, ConnectionError, OSError) as e:
                print(f"  Error de conexión, intento {attempt}/{retries}: {e}")
                if attempt < retries:
                    time.sleep(3 * attempt)
                else:
                    print("  No se pudo eliminar el video tras varios intentos.")
                    return False
            except googleapiclient.errors.HttpError as e:
                print(f"  Error de la API al eliminar el video: {e}")
                return False


if __name__ == "__main__":
    # Prueba rápida
    load_dotenv()
    try:
        yt = YouTubeManager()
        videos = yt.get_playlist_videos(os.environ.get("YOUTUBE_PLAYLIST", "Celeste"))
        print(f"Encontrados {len(videos)} videos.")
        for v in videos:
            print(f"- {v['title']}")
    except Exception as e:
        print(f"Configuración incompleta o error: {e}")
