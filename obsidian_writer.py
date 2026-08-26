import os
import re
from datetime import datetime


class ObsidianWriter:
    """Creates structured Markdown notes in an Obsidian vault."""

    def __init__(self, vault_path, subfolder="Remoto/0 Inbox"):
        self.vault_path = vault_path
        self.notes_dir = os.path.join(vault_path, subfolder)
        os.makedirs(self.notes_dir, exist_ok=True)
        # Persistent counter so the sequence keeps growing even when notes
        # are moved out of the Inbox after being processed.
        self.counter_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), ".seq_counter"
        )

    def _next_sequence_number(self):
        """Read, increment and persist the global note counter."""
        try:
            with open(self.counter_path, "r", encoding="utf-8") as f:
                current = int(f.read().strip() or "0")
        except (FileNotFoundError, ValueError):
            current = 0
        nxt = current + 1
        try:
            with open(self.counter_path, "w", encoding="utf-8") as f:
                f.write(str(nxt))
        except Exception as e:
            print(f"  Aviso: no se pudo guardar el contador de secuencia: {e}")
        return nxt

    def _sanitize_filename(self, title):
        """Remove characters that are problematic in filenames."""
        # Remove or replace problematic chars
        sanitized = re.sub(r'[\\/:*?"<>|]', "", title)
        sanitized = sanitized.strip(". ")
        # Truncate if too long
        if len(sanitized) > 120:
            sanitized = sanitized[:120].rsplit(" ", 1)[0]
        return sanitized

    def create_note(self, video_title, video_url, video_id, summary=None):
        """Create an Obsidian note for a YouTube video.

        Args:
            video_title: Title of the video
            video_url: Full YouTube URL
            video_id: YouTube video ID
            summary: Markdown summary from Claude (or None for metadata-only note)

        Returns:
            Path to the created note, or None on failure.
        """
        today = datetime.now().strftime("%Y-%m-%d")
        seq = self._next_sequence_number()
        base_name = f"{seq:04d} {self._sanitize_filename(video_title)}"
        filepath = os.path.join(self.notes_dir, f"{base_name}.md")

        # Nunca sobreescribir una nota existente
        dedup = 2
        while os.path.exists(filepath):
            filepath = os.path.join(self.notes_dir, f"{base_name} ({dedup}).md")
            dedup += 1

        # Build the note content
        lines = []

        # YAML frontmatter
        lines.append("---")
        lines.append(f"title: \"{video_title.replace(chr(34), chr(39))}\"")
        lines.append("source: youtube")
        lines.append(f"url: {video_url}")
        lines.append(f"video_id: {video_id}")
        lines.append(f"date: {today}")
        lines.append("tags:")
        lines.append("  - video")
        lines.append("  - youtube")
        lines.append("  - inbox")
        lines.append("---")
        lines.append("")

        # Title
        lines.append(f"# {video_title}")
        lines.append("")

        # Embed
        lines.append(f"[![Video](https://img.youtube.com/vi/{video_id}/maxresdefault.jpg)]({video_url})")
        lines.append("")

        if summary:
            lines.append(summary)
        else:
            lines.append("## Resumen")
            lines.append("")
            lines.append("> No se pudo obtener la transcripción de este video.")
            lines.append("> Míralo directamente en YouTube para tomar notas.")
            lines.append("")
            lines.append(f"[Ver en YouTube]({video_url})")

        lines.append("")

        content = "\n".join(lines)

        tmp_path = filepath + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, filepath)
            print(f"  Nota guardada: {filepath}")
            return filepath
        except Exception as e:
            print(f"  Error escribiendo la nota: {e}")
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            return None


if __name__ == "__main__":
    # Quick test
    writer = ObsidianWriter(
        vault_path=os.path.expanduser("~/Obsidian"),
        subfolder="Remoto/0 Inbox",
    )
    path = writer.create_note(
        video_title="Test Video - Conceptos de IA",
        video_url="https://www.youtube.com/watch?v=jNQXAC9IVRw",
        video_id="jNQXAC9IVRw",
        summary="## Conceptos Principales\n\n- Concepto 1\n- Concepto 2\n",
    )
    if path:
        print(f"Created: {path}")
