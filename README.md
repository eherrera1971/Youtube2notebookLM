# Y2Obsidian — De YouTube a Obsidian

Procesa los videos de una playlist de YouTube (por defecto **"Celeste"**): baja la
transcripción, la resume con Claude, crea una nota estructurada en Obsidian y
saca el video de la playlist.

## Uso

```bash
./bin/run
```

Eso es todo. El script se encarga solo de:

1. Crear el entorno virtual si no existe (en `~/.venvs/Y2Obsidian`, fuera de iCloud).
2. Instalar/actualizar las dependencias cuando `requirements.txt` cambia.
3. Cargar las variables de `.env`.
4. Procesar la playlist y escribir el log en `automation.log` (rota al llegar a 1 MB).

### Opciones

| Comando | Qué hace |
|---|---|
| `./bin/run` | Procesa todos los videos pendientes |
| `./bin/run --check` | Verifica credenciales y muestra cuántos videos hay pendientes |
| `./bin/run --dry-run` | Lista los videos sin crear notas ni tocar la playlist |
| `./bin/run --limit 2` | Procesa como máximo 2 videos |
| `./bin/run --keep` | Crea las notas pero deja los videos en la playlist |

## Configuración inicial

1. **Credenciales de YouTube**: coloca `client_secret.json` (Google Cloud Console)
   en la raíz del proyecto. La primera ejecución abre el navegador para autorizar
   y guarda el token en `token.pickle`.

2. **Variables de entorno**: copia `.env.example` a `.env` y completa
   `ANTHROPIC_API_KEY`. Las demás variables son opcionales:

   | Variable | Por defecto | Para qué |
   |---|---|---|
   | `ANTHROPIC_API_KEY` | — | **Obligatoria.** API key de Anthropic |
   | `ANTHROPIC_MODEL` | `claude-opus-5` | Modelo usado para resumir |
   | `ANTHROPIC_EFFORT` | `medium` | Profundidad de razonamiento (`low`…`max`) |
   | `OBSIDIAN_VAULT` | `~/Remoto` | Ruta de la bóveda de Obsidian |
   | `OBSIDIAN_SUBFOLDER` | `4 YoutubeCeleste` | Carpeta destino dentro de la bóveda |
   | `YOUTUBE_PLAYLIST` | `Celeste` | Playlist a procesar |
   | `WHAPI_TOKEN` / `WHATSAPP_TO` | — | Aviso por WhatsApp si la corrida falla |

## Ejecución automática (cron)

```bash
crontab -e
```

```cron
0 */2 * * * /Users/eherrera/Documents/Proyectos/Y2Obsidian/bin/run >/dev/null 2>&1
```

**Ojo con el token de Google**: si el proyecto de Google Cloud está en modo
"Testing", el refresh token caduca cada 7 días y el flujo OAuth necesita un
navegador. En ese caso la corrida por cron falla con un mensaje claro en vez de
quedarse colgada, y basta con ejecutar `./bin/run --check` a mano para renovarlo.
Para evitarlo del todo, publica la app en Google Cloud Console (estado "In production").

## Elección del modelo

Medido sobre una transcripción real de 20.000 caracteres (entrevista en inglés,
resumen en español):

| Modelo | Costo/video | Tiempo | Resultado |
|---|---|---|---|
| `claude-sonnet-4-6` | $0,043 | 42 s | El más breve en cobertura; se le coló una errata |
| `claude-sonnet-5` | $0,034 | 22 s | Más barato y rápido que 4.6, y mejor escrito |
| **`claude-opus-5`** | **$0,112** | 41 s | Conserva matices y ejemplos que los otros omiten |

Se usa **Opus 5** por defecto: la diferencia es de ~7 centavos por video, y las
notas se escriben una vez pero se releen muchas. Si procesas gran volumen,
`claude-sonnet-5` es la alternativa sensata — es estrictamente mejor que el
`claude-sonnet-4-6` que se usaba antes (más barato, más rápido y más limpio).

## Arquitectura

Cuatro módulos, cada uno ejecutable por separado para probarlo:

- **`main.py`** — Orquesta el flujo y valida la configuración antes de empezar
  (preflight). Devuelve exit code distinto de 0 si algo falló.
- **`youtube_manager.py`** — YouTube Data API v3: OAuth, listar la playlist
  (omite videos privados o borrados) y eliminar items.
- **`transcript_summarizer.py`** — Baja la transcripción (español → inglés →
  cualquier idioma) y la resume con Claude. Las transcripciones muy largas se
  procesan por partes y luego se consolidan, en vez de recortarse.
- **`obsidian_writer.py`** — Escribe la nota Markdown con frontmatter YAML,
  miniatura del video y el resumen. Numera las notas con un contador persistente
  (`.seq_counter`) y nunca sobreescribe una nota existente.

## Notas

- Si un video no tiene transcripción, **no** se crea nota y el video se queda en
  la playlist para reintentarlo en la siguiente corrida.
- El log rota automáticamente: al pasar 1 MB, `automation.log` se mueve a
  `automation.log.1`.
