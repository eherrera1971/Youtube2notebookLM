import argparse
import os
import sys

from env_loader import BASE_DIR, load_dotenv

load_dotenv()

from youtube_manager import YouTubeManager  # noqa: E402
from transcript_summarizer import TranscriptSummarizer  # noqa: E402
from obsidian_writer import ObsidianWriter  # noqa: E402

# Configuración (sobreescribible por variables de entorno)
OBSIDIAN_VAULT_PATH = os.path.expanduser(os.environ.get("OBSIDIAN_VAULT", "~/Remoto"))
OBSIDIAN_SUBFOLDER = os.environ.get("OBSIDIAN_SUBFOLDER", "4 YoutubeCeleste")
PLAYLIST_NAME = os.environ.get("YOUTUBE_PLAYLIST", "Celeste")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Procesa videos de una playlist de YouTube y crea notas en Obsidian."
    )
    parser.add_argument(
        "--limit", type=int, default=0,
        help="Procesar como máximo N videos (0 = todos).",
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="No escribe notas ni toca la playlist; solo muestra qué haría.",
    )
    parser.add_argument(
        "--keep", action="store_true",
        help="No eliminar los videos de la playlist tras procesarlos.",
    )
    parser.add_argument(
        "--check", action="store_true",
        help="Verifica credenciales y configuración, y sale.",
    )
    return parser.parse_args()


def preflight():
    """Valida lo necesario antes de arrancar. Devuelve lista de errores."""
    errors = []
    if not os.path.exists(os.path.join(BASE_DIR, "client_secret.json")):
        errors.append(
            "Falta client_secret.json — descárgalo desde Google Cloud Console "
            "y déjalo en la raíz del proyecto."
        )
    if not os.environ.get("ANTHROPIC_API_KEY"):
        errors.append(
            "Falta ANTHROPIC_API_KEY — defínela en el archivo .env "
            "(usa .env.example como plantilla)."
        )
    vault = OBSIDIAN_VAULT_PATH
    if not os.path.isdir(vault):
        errors.append(
            f"No existe la bóveda de Obsidian en {vault} — "
            "ajusta OBSIDIAN_VAULT en .env."
        )
    else:
        # Comprobar que se puede escribir ahora, y no después de haber
        # gastado tokens resumiendo un video que no se podrá guardar.
        notes_dir = os.path.join(vault, OBSIDIAN_SUBFOLDER)
        try:
            os.makedirs(notes_dir, exist_ok=True)
            probe = os.path.join(notes_dir, ".escritura_ok")
            with open(probe, "w", encoding="utf-8"):
                pass
            os.remove(probe)
        except OSError as e:
            errors.append(f"No se puede escribir en {notes_dir}: {e}")
    return errors


def main(args):
    print("Iniciando automatización YouTube -> Obsidian")

    # 1. YouTube
    try:
        yt = YouTubeManager(base_dir=BASE_DIR)
    except Exception as e:
        print(f"No se pudo inicializar YouTube: {e}")
        return 1

    # 2. Videos
    print(f"Buscando videos en la playlist '{PLAYLIST_NAME}'...")
    try:
        videos = yt.get_playlist_videos(PLAYLIST_NAME)
    except Exception as e:
        print(f"Error consultando la playlist: {e}")
        return 1

    if not videos:
        print(f"No hay videos en la playlist '{PLAYLIST_NAME}'. Nada que hacer.")
        return 0

    if args.limit and args.limit < len(videos):
        print(f"Encontrados {len(videos)} videos; se procesarán los primeros {args.limit}.")
        videos = videos[: args.limit]
    else:
        print(f"Encontrados {len(videos)} videos para procesar.")

    if args.dry_run:
        for i, video in enumerate(videos, 1):
            print(f"  [{i}] {video['title']} — {video['url']}")
        print("\n(dry-run: no se creó ninguna nota ni se modificó la playlist)")
        return 0

    # 3. Resumidor y escritor
    try:
        summarizer = TranscriptSummarizer()
    except ValueError as e:
        print(f"No se pudo inicializar el resumidor: {e}")
        return 1

    writer = ObsidianWriter(
        vault_path=OBSIDIAN_VAULT_PATH,
        subfolder=OBSIDIAN_SUBFOLDER,
    )

    # 4. Procesamiento
    success_count = 0
    fail_count = 0

    for i, video in enumerate(videos, 1):
        print(f"\n[{i}/{len(videos)}] Procesando: {video['title']}")
        print(f"  URL: {video['url']}")

        try:
            summary = summarizer.process_video(
                video_id=video["video_id"],
                video_title=video["title"],
                video_url=video["url"],
            )

            # Sin resumen: el video se queda en la playlist para reintentar luego
            if not summary:
                print("  Sin resumen — el video se mantiene en la playlist.")
                fail_count += 1
                continue

            note_path = writer.create_note(
                video_title=video["title"],
                video_url=video["url"],
                video_id=video["video_id"],
                summary=summary,
            )

            if note_path:
                print("  Nota creada correctamente.")
                if args.keep:
                    print("  (--keep: el video permanece en la playlist)")
                else:
                    yt.remove_video_from_playlist(video["playlist_item_id"])
                success_count += 1
            else:
                print("  No se pudo crear la nota.")
                fail_count += 1

        except KeyboardInterrupt:
            print("\nInterrumpido por el usuario.")
            return 130
        except Exception as e:
            print(f"  Error inesperado: {e}")
            fail_count += 1

    print(f"\nListo. Éxitos: {success_count}, Fallos: {fail_count}")
    return 1 if fail_count else 0


if __name__ == "__main__":
    cli_args = parse_args()

    problems = preflight()
    if problems:
        print("Configuración incompleta:")
        for p in problems:
            print(f"  - {p}")
        sys.exit(1)

    if cli_args.check:
        print("Configuración OK. Verificando acceso a YouTube...")
        try:
            yt = YouTubeManager(base_dir=BASE_DIR)
            vids = yt.get_playlist_videos(PLAYLIST_NAME)
            print(f"Acceso OK. Playlist '{PLAYLIST_NAME}': {len(vids)} videos pendientes.")
            sys.exit(0)
        except Exception as e:
            print(f"Fallo de acceso a YouTube: {e}")
            sys.exit(1)

    sys.exit(main(cli_args))
