# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Project Does

Automates processing videos from a YouTube playlist named "Celeste": fetches the transcript of each video, summarizes its key concepts using Claude AI, creates a structured Obsidian note in the vault, and removes the video from the playlist.

## Running

```bash
./bin/run              # process everything pending
./bin/run --check      # validate config + credentials, show pending count
./bin/run --dry-run    # list videos without writing notes or touching the playlist
./bin/run --limit N    # process at most N videos
./bin/run --keep       # write notes but leave videos in the playlist
```

`bin/run` delegates to `run_task.sh`, which bootstraps everything: it creates the venv at `~/.venvs/Y2Obsidian` if missing (outside iCloud — `~/Documents` is synced and corrupts venvs), installs deps when `requirements.txt` changes (tracked by a sha stamp), sources `.env`, rotates `automation.log` past 1 MB, and notifies via WhatsApp on failure if `WHAPI_TOKEN`/`WHATSAPP_TO` are set.

Do not create a `.venv` inside the project — that's what the iCloud note above is about.

## Configuration

`.env` (see `.env.example`). Only `ANTHROPIC_API_KEY` is required. Overridable: `ANTHROPIC_MODEL` (default `claude-opus-5`), `ANTHROPIC_EFFORT` (default `medium`; empty = omit the param), `OBSIDIAN_VAULT` (default `~/Remoto`), `OBSIDIAN_SUBFOLDER` (default `4 YoutubeCeleste`), `YOUTUBE_PLAYLIST` (default `Celeste`).

`client_secret.json` (OAuth creds from Google Cloud Console) and `token.pickle` (auto-generated) are not committed.

## Architecture

Four modules, each independently runnable for testing:

- **`main.py`** — Entry point. Parses CLI flags, loads `.env` (dependency-free loader — no `python-dotenv`), runs a preflight check on credentials and vault path, then orchestrates: fetch playlist → transcript → summarize → write note → remove from playlist. Non-zero exit code when any video failed, so cron/WhatsApp notification triggers.

- **`youtube_manager.py`** — Wraps YouTube Data API v3. OAuth2 with absolute paths derived from `base_dir` (must work from any cwd under cron). `get_playlist_videos(name)` paginates over both playlists and items and skips private/deleted videos. Raises a clear error instead of hanging when OAuth is needed with no TTY.

- **`transcript_summarizer.py`** — Fetches transcripts via `youtube-transcript-api` (Spanish → English → translated → any). Summarizes with Claude via streaming (`output_config.effort`, with an automatic retry without it for models that reject the param). Transcripts over `CHUNK_THRESHOLD_CHARS` are map-reduced (chunk summaries → consolidation) rather than truncated.

- **`obsidian_writer.py`** — Writes Markdown notes with YAML frontmatter, thumbnail link and summary. Notes are numbered from a persistent counter (`.seq_counter`) so the sequence survives notes being moved out of the folder. Writes atomically via a `.tmp` file and never overwrites an existing note.

## Key Constraints

- **Google OAuth token expiry** — If the Google Cloud project is in "Testing" mode, refresh tokens expire after 7 days and re-auth needs a browser. Cron runs fail fast with a clear message; `./bin/run --check` renews interactively.
- **No transcript → no note** — The video stays in the playlist to be retried on the next run.
- **Summaries are in Spanish** — The Claude prompt instructs output in Spanish regardless of transcript language.
