import os
import re

from env_loader import load_dotenv


class ObsidianWriter:
    """Creates structured Markdown notes in an Obsidian vault."""

    def __init__(self, vault_path, subfolder="4 YoutubeCeleste"):
        self.vault_path = vault_path
        self.notes_dir = os.path.join(vault_path, subfolder)
        os.makedirs(self.notes_dir, exist_ok=True)
        # Persistent counter so the sequence keeps growing even when notes
        # are moved out of the Inbox after being processed.
        self.counter_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), ".seq_counter"
        )

    def _peek_sequence_number(self):
        """Siguiente número de la secuencia, sin consumirlo todavía."""
        try:
            with open(self.counter_path, "r", encoding="utf-8") as f:
                current = int(f.read().strip() or "0")
        except (FileNotFoundError, ValueError):
            current = 0
        return current + 1

    def _commit_sequence_number(self, seq):
        """Persiste el número una vez que la nota quedó escrita.

        Se separa de _peek_sequence_number para que una escritura fallida
        no deje un hueco permanente en la numeración.
        """
        try:
            with open(self.counter_path, "w", encoding="utf-8") as f:
                f.write(str(seq))
        except Exception as e:
            print(f"  Aviso: no se pudo guardar el contador de secuencia: {e}")

    @staticmethod
    def _strip_leading_title(summary):
        """Quita el encabezado con el que el resumen abre, si lo trae.

        El prompt pide no incluirlo, pero el modelo a veces lo agrega igual
        y quedaría repitiendo el nombre del archivo.
        """
        texto = summary.lstrip()
        if not texto.startswith("#"):
            return texto
        primera, _, resto = texto.partition("\n")
        # Solo un H1: un H2 es una sección legítima del resumen
        # ("## Introducción"); un H1 siempre repetiría el título de la nota.
        if re.match(r"^# +\S", primera):
            return resto.lstrip("\n")
        return texto

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
        seq = self._peek_sequence_number()
        base_name = f"{seq:04d} {self._sanitize_filename(video_title)}"
        filepath = os.path.join(self.notes_dir, f"{base_name}.md")

        # Nunca sobreescribir una nota existente
        dedup = 2
        while os.path.exists(filepath):
            filepath = os.path.join(self.notes_dir, f"{base_name} ({dedup}).md")
            dedup += 1

        # Estructura: miniatura, resumen y la URL al final. Sin frontmatter
        # (Obsidian lo muestra como "Propiedades") y sin título: el nombre
        # del archivo ya lo es.
        lines = [
            f"![Video](https://img.youtube.com/vi/{video_id}/maxresdefault.jpg)",
            "",
        ]

        if summary:
            # El resumen suele abrir con su propio encabezado, que repetiría
            # el nombre del archivo.
            lines.append(self._strip_leading_title(summary))
        else:
            lines.append("## Resumen")
            lines.append("")
            lines.append("> No se pudo obtener la transcripción de este video.")
            lines.append("> Míralo directamente en YouTube para tomar notas.")

        lines.append("")
        lines.append(video_url)
        lines.append("")

        content = "\n".join(lines)

        tmp_path = filepath + ".tmp"
        try:
            with open(tmp_path, "w", encoding="utf-8") as f:
                f.write(content)
            os.replace(tmp_path, filepath)
            self._commit_sequence_number(seq)
            print(f"  Nota guardada: {filepath}")
            return filepath
        except Exception as e:
            print(f"  Error escribiendo la nota: {e}")
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
            return None


if __name__ == "__main__":
    # Quick test
    load_dotenv()
    writer = ObsidianWriter(
        vault_path=os.path.expanduser(os.environ.get("OBSIDIAN_VAULT", "~/Remoto")),
        subfolder=os.environ.get("OBSIDIAN_SUBFOLDER", "4 YoutubeCeleste"),
    )
    path = writer.create_note(
        video_title="Test Video - Conceptos de IA",
        video_url="https://www.youtube.com/watch?v=jNQXAC9IVRw",
        video_id="jNQXAC9IVRw",
        summary="## Conceptos Principales\n\n- Concepto 1\n- Concepto 2\n",
    )
    if path:
        print(f"Created: {path}")
