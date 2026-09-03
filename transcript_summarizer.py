import os

import anthropic
from youtube_transcript_api import YouTubeTranscriptApi

from env_loader import load_dotenv

# Antes de leer las constantes de abajo: si el módulo se ejecuta suelto
# nadie más habrá cargado el .env.
load_dotenv()

# Modelo configurable. Opus 5 es el más capaz: en pruebas sobre transcripciones
# reales conserva más detalle y matices que Sonnet, por ~$0.11 por video.
# Alternativa más barata: claude-sonnet-5 (~$0.03 por video).
DEFAULT_MODEL = os.environ.get("ANTHROPIC_MODEL", "claude-opus-5")

# Profundidad de razonamiento: low | medium | high | xhigh | max.
# "medium" basta para resumir; deja vacío para no enviar el parámetro
# (necesario si usas un modelo antiguo que no lo soporta).
EFFORT = os.environ.get("ANTHROPIC_EFFORT", "medium").strip()

# Umbral a partir del cual la transcripción se resume por partes en vez de
# mandarla completa en una sola petición.
CHUNK_THRESHOLD_CHARS = 120_000
CHUNK_SIZE_CHARS = 60_000


class TranscriptSummarizer:
    """Obtiene transcripciones de YouTube y las resume con Claude."""

    def __init__(self, api_key=None, model=None):
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Se requiere la API key de Anthropic. Define ANTHROPIC_API_KEY "
                "en .env o pásala al constructor."
            )
        self.model = model or DEFAULT_MODEL
        self.effort = EFFORT
        # max_retries cubre 429 y errores 5xx con backoff exponencial.
        self.client = anthropic.Anthropic(
            api_key=self.api_key, max_retries=4, timeout=300.0
        )
        self.transcript_api = YouTubeTranscriptApi()

    def get_transcript(self, video_id, languages=("es", "en")):
        """Devuelve (texto, idioma) de la transcripción del video.
        Prueba español, luego inglés, luego cualquier idioma disponible."""
        try:
            transcript_list = self.transcript_api.list(video_id)

            # Idiomas preferidos primero
            for lang in languages:
                try:
                    transcript = transcript_list.find_transcript([lang])
                    fetched = transcript.fetch()
                    return " ".join(s.text for s in fetched), lang
                except Exception:
                    continue

            # Alternativa: transcripción automática en inglés traducida al español
            try:
                transcript = transcript_list.find_generated_transcript(["en"])
                fetched = transcript.translate("es").fetch()
                return " ".join(s.text for s in fetched), "es (traducido)"
            except Exception:
                pass

            # Último recurso: lo que haya
            for transcript in transcript_list:
                fetched = transcript.fetch()
                return " ".join(s.text for s in fetched), transcript.language_code

            return None, None

        except Exception as e:
            print(f"  No se pudo obtener la transcripción de {video_id}: {e}")
            return None, None

    def _ask_claude(self, prompt, max_tokens=8000):
        try:
            return self._create(prompt, max_tokens)
        except anthropic.BadRequestError as e:
            if not self.effort:
                print(f"  Petición inválida a la API de Claude: {e.message}")
                return None
            # Un modelo antiguo puede rechazar output_config. Se desactiva
            # para toda la sesión: si no, una transcripción larga pagaría
            # el reintento en cada uno de sus trozos.
            print(f"  El modelo no acepta 'effort' ({e.message}); se desactiva y se reintenta.")
            self.effort = ""
            try:
                return self._create(prompt, max_tokens)
            except Exception as e2:
                print(f"  Error de la API de Claude: {e2}")
        except anthropic.APIStatusError as e:
            print(f"  Error de la API de Claude ({e.status_code}): {e.message}")
        except anthropic.APIConnectionError as e:
            print(f"  Error de conexión con la API de Claude: {e}")
        except Exception as e:
            print(f"  Error inesperado llamando a Claude: {e}")
        return None

    def _create(self, prompt, max_tokens):
        """Una llamada a la API, devuelta ya como texto. Se usa streaming
        porque con max_tokens alto una petición normal puede exceder el
        timeout HTTP."""
        kwargs = {"output_config": {"effort": self.effort}} if self.effort else {}
        with self.client.messages.stream(
            model=self.model,
            max_tokens=max_tokens,
            messages=[{"role": "user", "content": prompt}],
            **kwargs,
        ) as stream:
            response = stream.get_final_message()
        return "".join(b.text for b in response.content if b.type == "text")

    def _summary_prompt(self, transcript_text, video_title, video_url):
        return f"""Analiza la siguiente transcripción de un video de YouTube y genera un resumen estructurado en español.

**Título del video:** {video_title}
**URL:** {video_url}

**Instrucciones:**
- No pongas título ni encabezado al principio: la nota ya lleva el título del video arriba. Empieza directamente con el párrafo de introducción
- Escribe un párrafo breve de introducción que explique de qué trata el video
- Lista los conceptos principales como bullet points claros y concisos
- Cada bullet point debe ser autocontenido y fácil de entender
- Si hay sub-conceptos, usa sub-bullets
- Al final, incluye una sección de "Conclusiones clave" con los 3-5 takeaways más importantes
- Escribe todo en español, incluso si la transcripción está en inglés
- Usa un tono informativo pero accesible

**Transcripción:**
{transcript_text}"""

    def _chunks(self, text, size=CHUNK_SIZE_CHARS):
        """Parte el texto en trozos, cortando en el espacio más cercano."""
        parts = []
        start = 0
        while start < len(text):
            end = min(start + size, len(text))
            if end < len(text):
                space = text.rfind(" ", start + size // 2, end)
                if space != -1:
                    end = space
            parts.append(text[start:end])
            start = end
        return parts

    def summarize(self, transcript_text, video_title, video_url):
        """Resume la transcripción. Si es muy larga, la procesa por partes
        y luego consolida (así no se pierde el contenido del final)."""
        if len(transcript_text) <= CHUNK_THRESHOLD_CHARS:
            return self._ask_claude(
                self._summary_prompt(transcript_text, video_title, video_url)
            )

        parts = self._chunks(transcript_text)
        print(f"  Transcripción larga: se procesa en {len(parts)} partes.")
        partial_notes = []
        for i, part in enumerate(parts, 1):
            print(f"    Parte {i}/{len(parts)}...")
            notes = self._ask_claude(
                f"""Esta es la parte {i} de {len(parts)} de la transcripción del video "{video_title}".
Extrae en español, como bullet points, todos los conceptos e ideas relevantes de esta parte.
No escribas introducción ni conclusiones: solo las ideas.

**Transcripción (parte {i}):**
{part}""",
                max_tokens=4000,
            )
            if notes:
                partial_notes.append(notes)

        if not partial_notes:
            return None

        combined = "\n\n".join(partial_notes)
        return self._ask_claude(
            f"""A continuación tienes notas parciales extraídas de un video largo de YouTube.

**Título del video:** {video_title}
**URL:** {video_url}

**Instrucciones:**
- No pongas título ni encabezado al principio: la nota ya lleva el título del video arriba. Empieza directamente con el párrafo de introducción
- Consolida las notas en un único resumen estructurado en español, sin repeticiones
- Empieza con un párrafo breve de introducción sobre de qué trata el video
- Organiza los conceptos principales como bullet points claros (usa sub-bullets si hace falta)
- Termina con una sección "Conclusiones clave" con los 3-5 takeaways más importantes
- Usa un tono informativo pero accesible

**Notas parciales:**
{combined}"""
        )

    def process_video(self, video_id, video_title, video_url):
        """Flujo completo: transcripción → resumen → markdown."""
        print("  Obteniendo transcripción...")
        transcript, lang = self.get_transcript(video_id)

        if not transcript:
            print("  Sin transcripción disponible.")
            return None

        print(f"  Transcripción obtenida ({lang}, {len(transcript)} caracteres)")
        print(f"  Resumiendo con Claude ({self.model}, effort={self.effort or 'default'})...")

        summary = self.summarize(transcript, video_title, video_url)
        if not summary:
            print("  Falló el resumen.")
            return None

        print("  Resumen generado.")
        return summary


if __name__ == "__main__":
    # Prueba rápida
    summarizer = TranscriptSummarizer()
    result = summarizer.process_video(
        "jNQXAC9IVRw",
        "Me at the zoo",
        "https://www.youtube.com/watch?v=jNQXAC9IVRw",
    )
    if result:
        print(result)
