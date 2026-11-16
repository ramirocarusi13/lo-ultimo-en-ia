# Lo Último en IA — bot de Instagram

Publica sola carruseles de noticias de IA con diseño propio (azul noche, celeste y violeta):
portada con foto + titular grande, 2 imágenes que explican la noticia y una imagen final
para seguir la cuenta.

![ejemplo](docs/ejemplo/preview.jpg)

## Cómo funciona

1. **Busca tendencias** (`src/news.py`): lee ~10 medios de tecnología (TechCrunch, The Verge,
   Xataka, Wired, Google Noticias…) y agrupa los titulares parecidos. La historia que
   cubren **más medios en las últimas horas** es la que está en tendencia. Por defecto
   exige que la cubran al menos 2 medios (`MIN_SOURCES`) para no publicar rumores.
2. **Redacta** (`src/writer.py`): Claude lee las notas y escribe titular, los 2 textos del
   carrusel, el caption y los hashtags en español. Solo usa datos de las notas; si la
   noticia es un rumor o acusa a alguien sin pruebas, la descarta.
3. **Genera las fotos con IA open source** (`src/imagegen.py`): Claude describe 3 escenas
   y el modelo **FLUX.1 [schnell]** (Black Forest Labs, licencia Apache 2.0) las genera
   en Hugging Face. Nunca muestra personas reales ni logos. Si no hay token de Hugging
   Face, usa la foto principal de la nota con el crédito del medio.
4. **Diseña** (`src/render.py` + `src/templates/carousel.html`): plantilla HTML/CSS
   renderizada con Chromium (Playwright), con tipografías Archivo, Inter y Space Grotesk.
5. **Publica** (`src/publish.py`): sube el carrusel con la API oficial de Instagram.
6. **Se repite solo**: GitHub Actions lo corre 3 veces por día (`.github/workflows/post.yml`).
   `state/posted.json` recuerda lo publicado para no repetir.

## Puesta en marcha

### 1. Crear la cuenta de Instagram
- Creá la cuenta **@loultimoenia** (o el usuario que esté libre) desde la app.
- Pasala a **cuenta profesional** (Configuración → Tipo de cuenta → Creador o Empresa).
- Foto de perfil: `docs/logo.png`, o el logo que elijas de Canva.

### 2. Conseguir acceso a la API de Instagram
- Entrá a <https://developers.facebook.com> → Crear app → tipo *Empresa*.
- Agregá el producto **Instagram** → "API con inicio de sesión de Instagram".
- Conectá tu cuenta y generá un **token de acceso** con permisos
  `instagram_business_basic` e `instagram_business_content_publish`.
- Anotá el **ID de usuario de Instagram** que te muestra.
- Con este método, creá también la variable de Actions `IG_GRAPH_HOST` = `graph.instagram.com`.
- El token dura 60 días; renovalo antes de que venza.

### 3. Subir este proyecto a GitHub
El repo tiene que ser **público** (Instagram descarga las imágenes desde la URL del repo).
Si preferís privado, poné las imágenes en otro hosting y definí `PUBLIC_BASE_URL`.

En el repo → Settings → Secrets and variables → Actions:

| Tipo | Nombre | Valor |
|---|---|---|
| Secret | `ANTHROPIC_API_KEY` | tu clave de <https://console.anthropic.com> |
| Secret | `HF_TOKEN` | token de <https://huggingface.co/settings/tokens> con permiso *Make calls to Inference Providers* (opcional, para fotos con FLUX) |
| Secret | `IG_USER_ID` | ID de la cuenta de Instagram |
| Secret | `IG_ACCESS_TOKEN` | token del paso 2 |
| Variable | `IG_HANDLE` | `@loultimoenia` |
| Variable | `AUTO_PUBLISH` | `true` para publicar solo; si no, solo genera las imágenes |

Recomendado: empezá con `AUTO_PUBLISH` vacío, revisá unos días los posts que aparecen en
`posts/`, y cuando te convenzan ponelo en `true`.

### 4. Probar
Actions → "Publicar noticia de IA" → *Run workflow*.

## Uso local

```bash
pip install -r requirements.txt
python -m playwright install chromium
export ANTHROPIC_API_KEY=...
python src/main.py generate   # genera posts/<fecha>/slide_1..4.jpg + caption
python src/main.py publish    # publica (necesita IG_USER_ID, IG_ACCESS_TOKEN, PUBLIC_BASE_URL)
```

## Ajustes
- Medios y frecuencia: `src/config.py` y los `cron` del workflow.
- Colores y nombre: `src/config.py`. Diseño: `src/templates/carousel.html` (HTML/CSS común).
- Modelo de imágenes: variable `IMAGE_MODEL` (por defecto `black-forest-labs/FLUX.1-schnell`;
  con más créditos podés usar `black-forest-labs/FLUX.1-dev`, de mejor calidad).
- Tipografías en `fonts/` (Archivo, Inter, Space Grotesk; licencia OFL).
- Estilo de redacción: el prompt en `src/writer.py`.

## Ojo con
- **Fotos**: con `HF_TOKEN` las imágenes son propias (generadas con IA) y llevan la aclaración
  "Imagen generada con IA". Sin token se usa la foto de la nota: tiene derechos de autor y un
  medio puede pedir que la bajes.
- **Límites de Instagram**: máximo 50 publicaciones por día vía API; 3 por día está bien.
- Aunque Claude filtra rumores, conviene revisar de vez en cuando lo que se publica.
