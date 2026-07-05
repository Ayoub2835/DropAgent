# DropAgent (dropshipping) 🛒🤖

> Esta carpeta contiene el sistema de dropshipping automatizado. Es un
> proyecto independiente del pipeline de generación de video que vive en la
> raíz del repositorio; comparten nombre por coincidencia pero no código.

**DropAgent** es un sistema automatizado de dropshipping escrito en Python.
Busca productos trending en AliExpress, genera descripciones de venta con la
API de Claude, crea los productos automáticamente en tu tienda Shopify y
monitorea el rendimiento de tus campañas de Facebook Ads cada 24 horas.

Por ahora **no usa Telegram**: todas las notificaciones se muestran en la
consola y quedan guardadas en un archivo `log.json` para su consulta
posterior.

## Características

1. **Buscador de productos trending** (`dropagent/aliexpress_scraper.py`)
   Busca productos populares en AliExpress según palabras clave. Si el
   scraping en vivo falla (bloqueo anti-bot, sin conexión, etc.), usa
   automáticamente un catálogo de demostración para que el resto del
   sistema siga funcionando sin interrupciones.

2. **Creador automático de productos en Shopify** (`dropagent/shopify_manager.py`)
   Crea productos en tu tienda vía la Admin REST API de Shopify, aplicando
   un margen de ganancia configurable sobre el precio de AliExpress. Si
   Shopify no está configurado, funciona en modo "dry-run" (simulación).

3. **Generador de descripciones con Claude API** (`dropagent/claude_generator.py`)
   Usa la API de Anthropic (Claude) para redactar títulos, descripciones en
   HTML y tags de producto optimizados para venta. Si no hay API key
   configurada, usa una plantilla local como respaldo.

4. **Monitor de Facebook Ads** (`dropagent/facebook_ads_monitor.py`)
   Consulta el rendimiento de tus campañas (gasto, CTR, CPC, ROAS) cada 24
   horas (configurable) y notifica los anuncios de bajo rendimiento.

5. **Lanzador y monitor de TikTok Ads** (`dropagent/tiktok_ads_manager.py`)
   Usa la TikTok Marketing API para lanzar automáticamente una campaña
   (campaña -> grupo de anuncios -> anuncio) por cada producto creado en
   Shopify, y revisa el ROAS de las campañas cada 24 horas (configurable),
   notificando las que tengan bajo rendimiento. Si TikTok no está
   configurado, o si falla la creación en vivo, funciona en modo
   "dry-run" simulando el lanzamiento.

6. **Generador de vídeos publicitarios con Higgsfield** (`dropagent/video_generator.py`)
   Cuando un producto queda aprobado (creado en Shopify), llama a la API
   de Higgsfield para generar automáticamente un vídeo publicitario corto
   a partir de la imagen y descripción del producto, y lo descarga a
   `generated_videos/`. Si Higgsfield no está configurado, o si la
   llamada falla, funciona en modo "dry-run" sin gastar créditos.

7. **Generador de landing pages** (`dropagent/landing_page_generator.py`)
   Por cada producto aprobado, genera una landing page HTML autocontenida
   (sin dependencias externas) optimizada para conversión: hero con
   imagen del producto, descripción persuasiva, precio con descuento
   simulado y cuenta regresiva, botón de compra hacia Shopify, beneficios,
   testimonios generados por IA, garantía y urgencia. Se guarda en
   `landing_pages/<slug>.html`. No depende de ninguna API de pago (los
   testimonios usan Claude si está configurado, con plantilla local de
   respaldo), así que siempre se genera sin costo.

8. **Notificaciones en consola + log.json** (`dropagent/notifier.py`)
   Todos los eventos del sistema se imprimen en consola con íconos y
   timestamp, y se guardan de forma persistente en `log.json`.

## Requisitos

- Python 3.9 o superior
- Una cuenta de Shopify con una app privada/custom (permiso `write_products`)
- Una API key de Anthropic (Claude) — opcional pero recomendada
- Un token de acceso de Facebook Marketing API — opcional

## Instalación

```bash
# 1. Clona el repositorio y entra a esta subcarpeta
git clone <tu-fork-o-repo> DropAgent
cd DropAgent/dropshipping

# 2. Crea un entorno virtual (recomendado)
python3 -m venv venv
source venv/bin/activate   # En Windows: venv\Scripts\activate

# 3. Instala las dependencias
pip install -r requirements.txt

# 4. Copia el archivo de variables de entorno y complétalo con tus claves
cp .env.example .env
```

Edita `.env` con tus credenciales reales. Puedes dejar en blanco cualquier
sección (AliExpress, Shopify, Claude o Facebook): DropAgent detecta
automáticamente qué está configurado y usa modos de respaldo (demo /
plantilla / dry-run) para las secciones que falten, sin romper la
ejecución.

## Variables de entorno (`.env`)

| Variable | Descripción |
|---|---|
| `ALIEXPRESS_KEYWORDS` | Palabras clave (separadas por coma) para buscar productos trending |
| `SHOPIFY_SHOP_URL` | Dominio de tu tienda, ej. `mi-tienda.myshopify.com` |
| `SHOPIFY_ACCESS_TOKEN` | Token de acceso de tu app privada de Shopify |
| `SHOPIFY_PRICE_MARKUP_PERCENT` | Margen de ganancia aplicado al precio de AliExpress |
| `SHOPIFY_PUBLISH_IMMEDIATELY` | `true` para publicar de inmediato, `false` para dejar como borrador |
| `CLAUDE_API_KEY` | API key de Anthropic para generar descripciones |
| `CLAUDE_MODEL` | Modelo de Claude a usar (por defecto `claude-sonnet-5`) |
| `FACEBOOK_ACCESS_TOKEN` | Token de acceso de Facebook Marketing API |
| `FACEBOOK_AD_ACCOUNT_ID` | ID de tu cuenta publicitaria (con o sin prefijo `act_`) |
| `FACEBOOK_MONITOR_INTERVAL_HOURS` | Cada cuántas horas se revisan las campañas (default 24) |
| `FACEBOOK_MIN_ROAS` / `FACEBOOK_MAX_SPEND_NO_SALES` | Umbrales para marcar anuncios de bajo rendimiento |
| `TIKTOK_ACCESS_TOKEN` | Access token de la TikTok Marketing API |
| `TIKTOK_ADVERTISER_ID` | ID de tu cuenta publicitaria de TikTok |
| `TIKTOK_IDENTITY_ID` / `TIKTOK_IDENTITY_TYPE` | Identidad (perfil) usada para publicar los anuncios |
| `TIKTOK_PIXEL_ID` | ID del pixel de TikTok para medir conversiones (opcional) |
| `TIKTOK_DAILY_BUDGET` | Presupuesto diario (USD) de cada campaña nueva |
| `TIKTOK_OBJECTIVE_TYPE` / `TIKTOK_OPTIMIZATION_GOAL` | Objetivo de campaña y meta de optimización |
| `TIKTOK_LOCATION_IDS` | IDs de ubicación geográfica objetivo (separados por coma) |
| `TIKTOK_MONITOR_INTERVAL_HOURS` | Cada cuántas horas se revisa el ROAS (default 24) |
| `TIKTOK_MIN_ROAS` / `TIKTOK_MAX_SPEND_NO_SALES` | Umbrales para marcar campañas de bajo rendimiento |
| `TIKTOK_PURCHASE_METRIC` / `TIKTOK_REVENUE_METRIC` | Nombres de las métricas de compras/ingresos del reporte (ajustables según tu cuenta) |
| `HIGGSFIELD_API_KEY` | API key de tu cuenta de Higgsfield |
| `HIGGSFIELD_API_BASE_URL` | URL base de la API de Higgsfield |
| `HIGGSFIELD_MODEL` | Modelo de generación de vídeo a usar |
| `HIGGSFIELD_ASPECT_RATIO` | Formato del vídeo (`9:16`, `16:9`, `1:1`) |
| `HIGGSFIELD_VIDEO_DURATION_SECONDS` | Duración objetivo del vídeo generado |
| `HIGGSFIELD_POLL_INTERVAL_SECONDS` / `HIGGSFIELD_POLL_TIMEOUT_SECONDS` | Frecuencia y tiempo máximo de espera al consultar el estado del job |
| `HIGGSFIELD_VIDEO_OUTPUT_DIR` | Carpeta donde se guardan los vídeos generados (default `generated_videos`) |
| `LANDING_PAGES_OUTPUT_DIR` | Carpeta donde se guardan las landing pages generadas (default `landing_pages`) |
| `LANDING_PAGE_DISCOUNT_PERCENT` | Porcentaje de descuento simulado mostrado en la landing page |
| `LANDING_PAGE_MAX_STOCK` | Stock máximo simulado para el mensaje de urgencia |
| `MAX_PRODUCTS_PER_RUN` | Máximo de productos a crear por ejecución |
| `LOG_FILE` | Ruta del archivo JSON donde se guarda el historial (default `log.json`) |

Consulta `.env.example` para la lista completa y valores por defecto.

> `HIGGSFIELD_API_KEY` se obtiene desde tu cuenta en
> [platform.higgsfield.ai](https://platform.higgsfield.ai) → sección de API
> keys. Los nombres de endpoint (`HIGGSFIELD_GENERATE_ENDPOINT`,
> `HIGGSFIELD_STATUS_ENDPOINT`) son configurables por si la documentación
> oficial usa rutas distintas a las que trae por defecto este proyecto.

## Uso

Todos los comandos se ejecutan con `python main.py <comando>`.

### Buscar productos trending

```bash
python main.py trending
python main.py trending --keyword "gadgets" --limit 10
```

### Crear productos automáticamente en Shopify

Busca productos trending, genera su descripción con Claude, los publica
en tu tienda, lanza una campaña de TikTok Ads, genera un vídeo
publicitario con Higgsfield y crea la landing page de cada producto
aprobado:

```bash
python main.py create-products
python main.py create-products --max 3 --json
```

Cada producto aprobado (creado en Shopify) genera además:
- Un vídeo publicitario en `generated_videos/` (vía Higgsfield, o un
  registro "dry-run" si no está configurado).
- Una landing page en `landing_pages/<slug>.html`, lista para abrir en
  el navegador o subir a cualquier hosting estático.

### Revisar Facebook Ads

```bash
# Una sola revisión
python main.py monitor-ads

# Revisión continua cada 24h (o el intervalo configurado en .env)
python main.py monitor-ads --loop
python main.py monitor-ads --loop --interval 12
```

### Revisar el ROAS de TikTok Ads

```bash
# Una sola revisión
python main.py monitor-tiktok-ads

# Revisión continua cada 24h (o el intervalo configurado en .env)
python main.py monitor-tiktok-ads --loop
python main.py monitor-tiktok-ads --loop --interval 12
```

### Ejecutar todo el sistema

Crea productos (con su campaña de TikTok) una vez y deja los monitores de
Facebook Ads y TikTok Ads corriendo cada 24h, de forma concurrente:

```bash
python main.py run
python main.py run --fb-interval 24 --tiktok-interval 12
```

### Ver el historial de eventos

```bash
python main.py history
python main.py history --limit 50 --json
```

## Estructura del proyecto

```
DropAgent/
├── main.py                       # CLI principal
├── requirements.txt
├── .env.example
├── log.json                      # Se genera automáticamente al ejecutar
├── generated_videos/              # Vídeos publicitarios generados (Higgsfield)
├── landing_pages/                 # Landing pages HTML generadas por producto
└── dropagent/
    ├── __init__.py
    ├── config.py                 # Carga y validación de variables de entorno
    ├── notifier.py                # Notificaciones: consola + log.json
    ├── scheduler.py                # Bucle compartido para tareas programadas
    ├── utils.py                    # Utilidades compartidas (slugify)
    ├── aliexpress_scraper.py      # Buscador de productos trending
    ├── claude_generator.py        # Generador de descripciones y testimonios con Claude
    ├── shopify_manager.py         # Creador de productos en Shopify
    ├── facebook_ads_monitor.py    # Monitor de Facebook Ads cada 24h
    ├── tiktok_ads_manager.py       # Lanzador y monitor de TikTok Ads cada 24h
    ├── video_generator.py          # Generador de vídeos publicitarios (Higgsfield)
    ├── landing_page_generator.py   # Generador de landing pages HTML
    └── pipeline.py                # Orquesta el flujo completo
```

## Modo demo (sin API keys)

DropAgent está diseñado para funcionar de extremo a extremo incluso sin
ninguna clave configurada, para que puedas probar el flujo completo:

- **AliExpress**: usa un catálogo de demostración con productos de ejemplo.
- **Claude**: usa una plantilla de texto local en vez de la API.
- **Shopify**: simula la creación de productos (modo "dry-run"), mostrando
  el precio final calculado sin llamar a la API real.
- **Facebook Ads**: omite la revisión y lo indica claramente en consola.
- **TikTok Ads**: simula el lanzamiento de campaña (modo "dry-run") y omite
  la revisión de ROAS si no está configurado.
- **Higgsfield**: omite la generación de vídeo y registra un resultado
  "dry-run" si no está configurado, sin consumir créditos.
- **Landing pages**: se generan siempre (no dependen de ninguna API de
  pago); los testimonios usan una plantilla local si Claude no está
  configurado.

Esto te permite ejecutar `python main.py create-products` inmediatamente
después de clonar el repo, sin configurar nada, y ver el flujo completo
funcionando.

## Notas de seguridad

- Nunca subas tu archivo `.env` a un repositorio público (ya está listado
  en `.gitignore`).
- Usa una app privada/custom de Shopify con permisos mínimos
  (`write_products` es suficiente).
- Rota tus tokens de Facebook y Shopify periódicamente.

## Próximos pasos sugeridos

- Integración con Telegram para notificaciones push (actualmente reemplazada
  por consola + `log.json`).
- Soporte para actualizar precios/inventario de productos ya publicados.
- Panel web para visualizar el historial de `log.json`.
