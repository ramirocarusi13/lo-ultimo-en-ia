# Lo Último en IA — bot de Instagram

Publica sola carruseles de noticias de IA con diseño propio (azul noche, celeste y violeta):
portada con foto + titular grande, 2 imágenes que explican la noticia y una imagen final
para seguir la cuenta.

![ejemplo](docs/ejemplo/preview.jpg)

## Cómo funciona

1. **Busca noticias de último momento** (`src/news.py`): lee ~27 fuentes (TechCrunch, The Verge,
   Ars Technica, Engadget, CNBC, NYT, BBC, Xataka, Infobae, El País, Google Noticias y los blogs
   oficiales de OpenAI, Google, DeepMind, NVIDIA y Hugging Face) y agrupa los titulares que
   hablan de lo mismo (también entre inglés y español). Elige la historia de las últimas 12 h
   que cubren **más medios distintos**, priorizando lo más reciente; exige al menos 2
   (`MIN_SOURCES`; un anuncio oficial cuenta doble). Respeta un mínimo de 25 min entre posts y
   un máximo de 30 por día (`MIN_MINUTES_BETWEEN_POSTS`, `MAX_POSTS_PER_DAY`). Una nota copiada
   tal cual en varios sitios cuenta como una sola, y los sitios de recomendaciones bursátiles
   están bloqueados (`BLOCKED_SOURCES` en `src/config.py`).
2. **Redacta**: Claude, en una tarea programada de la app de Claude (con la suscripción, sin
   API paga), lee las notas y escribe titular, los 2 textos del carrusel, el caption, los
   hashtags y las descripciones de las fotos, siguiendo `prompts/redaccion.md`. Solo usa
   datos de las notas; si la noticia es un rumor, acusa a alguien sin pruebas o es una
   recomendación de inversión, la descarta.
3. **Genera las fotos gratis con IA open source** (`src/imagegen.py`): Claude describe 3
   escenas y **ComfyUI** las genera en esta PC con **FLUX.2 [klein] 4B** (Black Forest Labs,
   licencia Apache 2.0). Nunca muestra personas reales ni logos. Si ComfyUI no está
   disponible, usa la foto principal de la nota con el crédito del medio.
4. **Diseña** (`src/render.py` + `src/templates/carousel.html`): plantilla HTML/CSS
   renderizada con Chromium (Playwright), con tipografías Archivo, Inter y Space Grotesk.
5. **Arma un Reel con voz** (`src/video.py` + `src/templates/reel.html`): video vertical 9:16
   de ~30 s con las mismas fotos en movimiento, titular, subtítulos estilo karaoke y voz en off
   de **Piper** (TTS de código abierto, corre en la PC en segundos; voces en `voices/`, no se
   suben al repo). ffmpeg une todo en `posts/<id>/reel.mp4`. El guion sale del campo
   `reel_script` del borrador. Rearmar solo el Reel: `python src/main.py reel <id>`.
   **Videos reales** (`src/clips.py`): cuando existe video de la noticia con licencia que permite
   reutilizarlo (YouTube con licencia Creative Commons subido por el autor real, Wikimedia
   Commons o NASA), el Reel lo muestra en formato noticiero y el caption cita al autor
   ("🎥 Video: …"). Nunca se bajan videos de X/Twitter, TikTok, Instagram ni de YouTube con
   licencia estándar.
6. **Equipo de agentes** (`agentes/`): un analista de tendencias elige la noticia, y un
   verificador de datos, un editor de estilo, un revisor legal y un director de arte revisan
   cada post en paralelo. El informe queda en `posts/<id>/informe_agentes.md`.
7. **Te lo manda para revisar**: los 4 slides, el Reel, el caption y el informe llegan con una
   notificación. Se publica solo si lo pedís (o con `AUTO_PUBLISH=true` y la API de Instagram).
8. **Se repite solo**: la tarea programada de la app de Claude (instrucciones en
   `prompts/tarea_programada.md`) revisa las fuentes cada 10 minutos. `state/posted.json` recuerda lo
   publicado para no repetir.

¿Por qué en la PC y no en GitHub Actions? Los servidores de Actions no tienen placa de video
y ComfyUI tardaría muchísimo ahí. En esta PC (Intel Core Ultra 5, solo procesador) cada
foto tarda ~5 minutos, ~15 minutos por post.

## Puesta en marcha

### 1. ComfyUI (fotos gratis)
En `Documentos\ComfyUI` (fuera de este repo):
```powershell
git clone https://github.com/Comfy-Org/ComfyUI.git
cd ComfyUI
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/xpu
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```
Modelos (todos Apache 2.0):

| Archivo | Carpeta | Origen |
|---|---|---|
| `flux-2-klein-4b-fp8.safetensors` (3,8 GB) | `models/diffusion_models` | huggingface.co/black-forest-labs/FLUX.2-klein-4b-fp8 |
| `qwen_3_4b_fp4_flux2.safetensors` (3,6 GB) | `models/text_encoders` | huggingface.co/Comfy-Org/flux2-klein-4B |
| `flux2-vae.safetensors` (0,3 GB) | `models/vae` | huggingface.co/Comfy-Org/flux2-dev |

No hace falta dejarlo prendido: `run_local.ps1 -Build` lo inicia y lo apaga en cada corrida.

### 2. Crear la cuenta de Instagram
- Creá la cuenta **@loultimoenia** (o el usuario que esté libre) desde la app.
- Pasala a **cuenta profesional** (Configuración → Tipo de cuenta → Creador o Empresa).
- Foto de perfil: `docs/logo.png`, o el logo que elijas de Canva.

### 3. Conseguir acceso a la API de Instagram
- Entrá a <https://developers.facebook.com> → Crear app → tipo *Empresa*.
- Agregá el producto **Instagram** → "API con inicio de sesión de Instagram".
- Conectá tu cuenta y generá un **token de acceso** con permisos
  `instagram_business_basic` e `instagram_business_content_publish`.
- Anotá el **ID de usuario de Instagram** que te muestra.
- El token dura 60 días; renovalo antes de que venza.

### 4. Claves (variables de entorno de tu usuario de Windows, nunca en archivos)
```powershell
powershell -ExecutionPolicy Bypass -File scripts\cargar_claves.ps1 IG_USER_ID IG_ACCESS_TOKEN IG_GRAPH_HOST IG_HANDLE AUTO_PUBLISH
```
(lo que pegás no se ve en pantalla ni queda en ningún archivo)

| Nombre | Valor |
|---|---|
| `IG_USER_ID` | ID de la cuenta de Instagram |
| `IG_ACCESS_TOKEN` | token del paso 3 |
| `IG_GRAPH_HOST` | `graph.instagram.com` |
| `IG_HANDLE` | `@loultimoenia` |
| `AUTO_PUBLISH` | `true` para publicar solo; si no, solo genera y sube las imágenes |

### 5. Subir este proyecto a GitHub
El repo tiene que ser **público** (Instagram descarga las imágenes desde
`raw.githubusercontent.com`). Si preferís privado, poné las imágenes en otro hosting y
definí `PUBLIC_BASE_URL`.

### 6. Programar
En la app de Claude (pestaña Code) hay una tarea programada "Lo Último en IA" que corre
3 veces por día con las instrucciones de `prompts/tarea_programada.md`. La app tiene que
estar abierta y la PC prendida; si estaba cerrada, la tarea corre al volver a abrirla.
Los registros quedan en `logs/`.

Recomendado: empezá con `AUTO_PUBLISH` vacío, revisá unos días los posts que aparecen en
`posts/`, y cuando te convenzan ponelo en `true`.

## Uso manual

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m playwright install chromium
.\.venv\Scripts\python.exe src\main.py pick            # elige noticia -> work/<id>/notas.md
# escribir work/<id>/draft.json según prompts/redaccion.md
powershell -ExecutionPolicy Bypass -File scripts\run_local.ps1 -Build <id>   # fotos + carrusel + push
powershell -ExecutionPolicy Bypass -File scripts\run_local.ps1 -Publish      # publica en Instagram
```
Con una clave de la API de Anthropic (`ANTHROPIC_API_KEY`, pago) también funciona
`src\main.py generate`, que redacta solo.

## Ajustes
- Medios y fuentes bloqueadas: `src/config.py`. Horarios: en la tarea programada de la app.
- Colores y nombre: `src/config.py`. Diseño: `src/templates/carousel.html` (HTML/CSS común).
- Fotos: estilo en `STYLE` (`src/imagegen.py`); tamaño con `IMAGE_WIDTH`/`IMAGE_HEIGHT`
  (por defecto 768×960); ComfyUI en otra máquina con `COMFYUI_URL`.
- Tipografías en `fonts/` (Archivo, Inter, Space Grotesk; licencia OFL).
- Estilo de redacción: `prompts/redaccion.md`.

## Ojo con
- **Fotos**: con ComfyUI las imágenes son propias (generadas con IA) y llevan la aclaración
  "Imagen generada con IA". Sin ComfyUI se usa la foto de la nota: tiene derechos de autor y
  un medio puede pedir que la bajes.
- **Límites de Instagram**: máximo 50 publicaciones por día vía API; 3 por día está bien.
- Aunque Claude filtra rumores, conviene revisar de vez en cuando lo que se publica.
