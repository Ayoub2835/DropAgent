# DropAgent

Sistema modular en Python que genera historias 100% originales con IA y las
convierte automáticamente en vídeos listos para publicar en **YouTube
Shorts (16:9)**, **TikTok (9:16)** y **Snapchat Spotlight (9:16)**.

## Flujo del pipeline

1. **Historia original** generada por un LLM (OpenAI o Anthropic), con
   instrucciones explícitas de no copiar ni parafrasear obras protegidas.
2. **Guion** con estructura gancho → desarrollo → clímax → resolución.
3. **División en escenas**, cada una con narración + prompt visual.
4. **Narración (TTS)** por escena.
5. **Imágenes/vídeo** por escena generados por IA.
6. **Música libre de derechos** seleccionada de tu propia librería local.
7. **Subtítulos automáticos** (SRT) sincronizados con la narración.
8. **Montaje con FFmpeg**: zoom Ken Burns por escena + transiciones
   `xfade`/`acrossfade` + mezcla de música + subtítulos incrustados.
9. **Miniatura** para YouTube generada automáticamente.
10. **Metadatos SEO** (título, descripción, hashtags, keywords) por
    plataforma.
11. **Exportación multi-formato**: YouTube 16:9, TikTok 9:16, Snapchat 9:16.
12. **Carpeta de proyecto organizada** con todos los artefactos.
13. **Publicación opcional** vía APIs oficiales (YouTube ya, TikTok con
    audit de la app, Snapchat solo manual — ver limitaciones abajo).

## Arquitectura

```
dropagent/
  config.py            Configuración centralizada (.env)
  logging_config.py    Logging a consola + archivo rotativo
  models.py             Dataclasses: Story, Script, Scene, PlatformMetadata...
  exceptions.py         Jerarquía de excepciones tipadas
  pipeline.py            Orquestador de las 12 etapas
  llm/                   Generación de texto (OpenAI, Anthropic, mock offline)
  story/                 Historia -> guion -> escenas
  voice/                 TTS (ElevenLabs, OpenAI, gTTS, pyttsx3)
  visuals/               Imágenes por escena (OpenAI, Stability, placeholder offline)
  audio/                 Librería de música libre de derechos
  subtitles/             Generación de subtítulos SRT
  video/                 Ensamblado FFmpeg, miniatura, exportación por plataforma
  metadata/              SEO por plataforma
  publishing/            Integración con APIs oficiales
  storage/               Organización de carpetas de salida
main.py                  CLI
tests/                   Suite de pruebas (usa proveedores offline/mock)
assets/music/            Tu librería de música (no incluida, ver README interno)
output/                  Proyectos generados (uno por ejecución)
```

Cada integración externa (LLM, TTS, imágenes) está detrás de una interfaz
(`BaseLLMProvider`, `BaseTTSProvider`, `BaseImageProvider`) con una
*factory* que resuelve el proveedor configurado en `.env` y hace *fallback*
automático a una alternativa gratuita/offline si faltan credenciales, para
que el pipeline **siempre pueda ejecutarse** de extremo a extremo.

## Requisitos

- Python 3.11+
- FFmpeg y FFprobe en el PATH (o usa Docker, que ya lo incluye)
- Docker + Docker Compose (opcional pero recomendado)
- Claves de API opcionales según los proveedores que quieras usar

## Instalación local

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Instala ffmpeg si no lo tienes (ejemplo Debian/Ubuntu):
sudo apt-get install -y ffmpeg

cp .env.example .env
# Edita .env con tus claves (todas son opcionales, ver más abajo)
```

## Ejecución

```bash
python main.py generate \
  --topic "un guardafaros que encuentra un mensaje en una botella" \
  --genre mystery \
  --platforms youtube tiktok snapchat
```

Esto genera un proyecto completo en `output/<slug>-<timestamp>/` con:

```
scenes/       imágenes de cada escena
audio/        narración por escena
subtitles/    captions.srt
video/        master.mp4 (vídeo maestro 9:16 con transiciones y subtítulos)
thumbnails/   thumbnail.jpg (1280x720 para YouTube)
exports/      youtube.mp4 (16:9), tiktok.mp4 (9:16), snapchat.mp4 (9:16)
metadata/     story.json, script.json, scenes.json, youtube.json, tiktok.json, snapchat.json
```

Para publicar automáticamente tras generar (requiere credenciales, ver
abajo):

```bash
python main.py generate --topic "..." --publish
```

O publicar un proyecto ya generado:

```bash
python main.py publish --project output/mi-historia-20260704-101500 --platforms youtube
```

## Ejecución con Docker

```bash
docker compose build
docker compose run --rm dropagent generate --topic "tu tema aquí" --genre horror
```

Los volúmenes `output/`, `assets/` y `logs/` quedan montados desde el host,
así que los proyectos generados aparecen directamente en tu máquina.

## Configuración de proveedores (`.env`)

Todos los proveedores tienen un *fallback* gratuito/offline, así que el
proyecto funciona "de fábrica" sin ninguna clave. Para calidad de
producción real, configura:

| Etapa | Proveedor recomendado | Variable |
|---|---|---|
| Texto (historia/guion/SEO) | OpenAI o Anthropic | `LLM_PROVIDER`, `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` |
| Voz | ElevenLabs (mejor calidad) u OpenAI TTS | `TTS_PROVIDER`, `ELEVENLABS_API_KEY` |
| Imágenes | OpenAI (DALL-E 3) o Stability AI | `IMAGE_PROVIDER`, `OPENAI_API_KEY` / `STABILITY_API_KEY` |
| Subtítulos | `even` (sin dependencias) o `whisper` (`pip install faster-whisper`) | `SUBTITLE_MODE` |

Sin claves configuradas: el texto usa un generador mock determinista, la
voz usa `gTTS` (gratis, necesita internet) o `pyttsx3` (100% offline), y
las imágenes usan un generador de tarjetas con gradiente + texto (Pillow,
sin red). Esto permite probar todo el pipeline sin gastar en APIs.

## Música libre de derechos

DropAgent **no** incluye música de terceros para evitar problemas de
copyright. Añade tus propios archivos a `assets/music/` y etiquétalos en
`assets/music/manifest.json` (ver `assets/music/README.md` para fuentes
recomendadas: YouTube Audio Library, Pixabay Music, Free Music Archive,
Incompetech, Uppbeat). Si no hay música configurada, el vídeo se genera
igualmente sin pista de fondo.

## Publicación automática y sus límites reales

- **YouTube**: integración funcional vía YouTube Data API v3 (OAuth
  "installed app"). Necesitas crear credenciales OAuth en Google Cloud
  Console y apuntar `YOUTUBE_CLIENT_SECRETS_FILE` al JSON descargado.
- **TikTok**: integración vía Content Posting API oficial (`video/init` +
  subida). Requiere una app de desarrollador con el scope
  `video.publish` aprobado; mientras tu app no pase el *audit* de TikTok,
  solo podrás publicar en modo privado (`SELF_ONLY`).
- **Snapchat**: **no existe** actualmente una API pública para publicar
  contenido orgánico en Spotlight de forma desatendida (la Marketing API
  es solo para anuncios pagados, y Creative Kit requiere que un humano
  toque "enviar" en la app). `SnapchatPublisher.prepare_manual_package()`
  deja el vídeo, la miniatura y el caption listos en una carpeta para
  publicación manual, y el mismo punto de integración quedará listo si
  Snapchat libera una API pública en el futuro.

## Pruebas

```bash
pytest
```

La suite usa los proveedores mock/offline (LLM mock, imágenes placeholder,
TTS gtts/pyttsx3) para no depender de red ni de credenciales.

## Logging

Cada ejecución registra en consola y en `logs/dropagent.log` (rotación de
5 MB x 5 archivos). Ajusta el nivel con `LOG_LEVEL` en `.env`.

## Originalidad y derechos de autor

El *system prompt* de generación de historias instruye explícitamente al
modelo a no reproducir ni parafrasear libros, películas o autores
existentes, y a inventar personajes y tramas originales en cada
ejecución. Aun así, revisa siempre el resultado antes de publicar: eres
responsable del contenido final.
