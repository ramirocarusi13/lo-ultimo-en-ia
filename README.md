# Lo Último en IA — bot de Instagram

Publica solo carruseles de noticias de IA con el estilo de la cuenta de referencia:
portada con foto + titular grande con palabras en verde, 2 imágenes con la explicación
y una imagen final de "Síguenos".

![ejemplo](docs/ejemplo/preview.jpg)

## Cómo funciona

1. **Busca tendencias** (`src/news.py`): lee ~10 medios de tecnología (TechCrunch, The Verge,
   Xataka, Wired, Google Noticias…) y agrupa los titulares parecidos. La historia que
   cubren **más medios en las últimas horas** es la que está en tendencia. Por defecto
   exige que la cubran al menos 2 medios (`MIN_SOURCES`) para no publicar rumores.
2. **Redacta** (`src/writer.py`): Claude lee las notas y escribe titular, los 2 textos del
   carrusel, el caption y los hashtags en español. Solo usa datos de las notas; si la
   noticia es un rumor o acusa a alguien sin pruebas, la descarta.
3. **Diseña** (`src/render.py`): arma las 4 imágenes 1080×1350 con la foto de la nota.
4. **Publica** (`src/publish.py`): sube el carrusel con la API oficial de Instagram.
5. **Se repite solo**: GitHub Actions lo corre 3 veces por día (`.github/workflows/post.yml`).
   `state/posted.json` recuerda lo publicado para no repetir.

## Puesta en marcha

### 1. Crear la cuenta de Instagram
- Creá la cuenta **@loultimoenia** (o el usuario que esté libre) desde la app.
- Pasala a **cuenta profesional** (Configuración → Tipo de cuenta → Creador o Empresa).
- Foto de perfil: podés usar `docs/logo.png`.

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
export ANTHROPIC_API_KEY=...
python src/main.py generate   # genera posts/<fecha>/slide_1..4.jpg + caption
python src/main.py publish    # publica (necesita IG_USER_ID, IG_ACCESS_TOKEN, PUBLIC_BASE_URL)
```

## Ajustes
- Medios y frecuencia: `src/config.py` y los `cron` del workflow.
- Colores, nombre y tipografías: `src/config.py` y `fonts/` (Anton y Montserrat, licencia OFL).
- Estilo de redacción: el prompt en `src/writer.py`.

## Ojo con
- **Fotos**: se usa la imagen principal de cada nota con el crédito del medio. Es lo que hacen
  muchas cuentas de noticias, pero esas fotos tienen derechos de autor y un medio puede pedir
  que la bajes. Si querés evitar ese riesgo, cambiá las fotos por imágenes propias o de bancos libres.
- **Límites de Instagram**: máximo 50 publicaciones por día vía API; 3 por día está bien.
- Aunque Claude filtra rumores, conviene revisar de vez en cuando lo que se publica.
