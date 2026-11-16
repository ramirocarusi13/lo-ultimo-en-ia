Tengo un proyecto ya armado en esta carpeta: un bot que publica solo en Instagram la cuenta
"Lo Último en IA" (@loultimoenia), con carruseles de noticias de inteligencia artificial en español.
Leé primero README.md y el código en src/ para entender cómo está hecho. No lo rehagas desde cero.

Cómo funciona hoy:
- src/news.py: lee feeds RSS de medios de tecnología (src/config.py), agrupa titulares parecidos y
  elige la noticia "en tendencia" (la que cubren más medios en las últimas 36 h, mínimo 2 medios).
  Guarda lo publicado en state/posted.json para no repetir.
- src/writer.py: Claude (SDK de Anthropic, modelo claude-opus-5-5, salida JSON con esquema) escribe
  titular con *palabras resaltadas*, 2 textos del carrusel, caption, hashtags y 3 prompts de imagen
  en inglés (sin personas reales, logos ni texto). Descarta rumores y acusaciones sin pruebas.
- src/imagegen.py: genera las fotos con FLUX.1 [schnell] (open source) vía Hugging Face
  (huggingface_hub.InferenceClient.text_to_image, variable HF_TOKEN). Sin token usa la foto de la nota.
- src/render.py + src/templates/carousel.html: plantilla HTML/CSS (Jinja2) que Chromium (Playwright)
  convierte en 4 imágenes 1080x1350: portada, "Qué pasó", "Por qué importa" y cierre "Seguí a...".
  Colores en src/config.py: azul noche #080A1C, celeste #00DCFF, violeta #7C3AED.
  Tipografías en fonts/ (Archivo, Inter, Space Grotesk). Logo SVG dentro de la plantilla; docs/logo.png.
- src/publish.py: publica el carrusel con la API oficial de Instagram (Graph API), necesita
  IG_USER_ID, IG_ACCESS_TOKEN e imágenes en URL pública.
- src/main.py: comandos generate / publish / run.
- .github/workflows/post.yml: GitHub Actions lo corre 3 veces por día, sube las imágenes al repo
  (público) y publica si la variable AUTO_PUBLISH es true.

Lo que quedó pendiente y quiero que hagas conmigo, paso a paso:
1. Instalar dependencias (pip install -r requirements.txt y python -m playwright install chromium)
   y correr una prueba completa local: python src/main.py generate. Antes revisá que tenga
   ANTHROPIC_API_KEY configurada; si no, decime cómo conseguirla. Mostrame las imágenes que salgan.
2. Probar la generación de fotos con FLUX usando mi HF_TOKEN y ajustar el estilo de las fotos
   (constante STYLE en src/imagegen.py) hasta que se vean profesionales.
3. Revisar el diseño con fotos reales y pulir lo que haga falta en carousel.html.
4. Ayudarme a crear el repo en GitHub, cargar los secretos (ANTHROPIC_API_KEY, HF_TOKEN,
   IG_USER_ID, IG_ACCESS_TOKEN) y las variables (IG_HANDLE, AUTO_PUBLISH), y lanzar el workflow
   a mano para probarlo.
5. Guiarme para pasar la cuenta de Instagram a profesional y sacar el token de la API de Instagram.

Reglas: nunca guardes contraseñas ni claves en archivos del proyecto ni en el chat; van como
variables de entorno o secretos de GitHub. No copies el diseño ni la marca de otras cuentas.
Hablame en español.
