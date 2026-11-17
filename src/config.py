"""Configuración de la marca y de las fuentes de noticias."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FONTS = ROOT / "fonts"
STATE_FILE = ROOT / "state" / "posted.json"
POSTS_DIR = ROOT / "posts"

# ---- Marca ----
BRAND_NAME = "Lo Último en IA"
HANDLE = os.getenv("IG_HANDLE") or "@loultimoenia"
COLORS = {
    "bg": "#080A1C",       # azul noche
    "bg2": "#11153A",
    "accent": "#00DCFF",   # celeste eléctrico (palabras resaltadas)
    "accent2": "#7C3AED",  # violeta (etiquetas y botones)
}
SIZE = (1080, 1350)           # formato vertical 4:5 de Instagram

# ---- Reels (video vertical 9:16 con voz) ----
REEL_SIZE = (1080, 1920)
REEL_FPS = 30
# voz de Piper (gratis y de código abierto); los modelos se bajan a voices/ (no se suben al repo)
REEL_VOICE = os.getenv("REEL_VOICE") or "es_MX-claude-high"
REEL_SPEED = float(os.getenv("REEL_SPEED") or 0.88)  # <1 = habla más rápido
VOICES_DIR = ROOT / "voices"
# "natural" = Chatterbox (suena humana; usa voices/referencia.wav si existe) | "piper"
REEL_TTS = os.getenv("REEL_TTS") or "natural"

# ---- Fuentes (RSS) ----
# Mezcla de medios en inglés y español. Una historia que aparece en varios
# medios a la vez se considera "en tendencia".
FEEDS = [
    # Medios de IA y tecnología (inglés)
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "https://venturebeat.com/category/ai/feed/",
    "https://www.technologyreview.com/topic/artificial-intelligence/feed",
    "https://arstechnica.com/ai/feed/",
    "https://www.wired.com/feed/tag/ai/latest/rss",
    "https://the-decoder.com/feed/",
    "https://www.zdnet.com/topic/artificial-intelligence/rss.xml",
    "https://www.engadget.com/rss.xml",
    "https://9to5google.com/feed/",
    "https://9to5mac.com/feed/",
    # Grandes medios, sección tecnología
    "https://www.cnbc.com/id/19854910/device/rss/rss.html",
    "https://rss.nytimes.com/services/xml/rss/nyt/Technology.xml",
    "https://feeds.bbci.co.uk/news/technology/rss.xml",
    # Español
    "https://www.xataka.com/feedburner.xml",
    "https://hipertextual.com/inteligencia-artificial/feed",
    "https://www.genbeta.com/feedburner.xml",
    "https://es.wired.com/feed/rss",
    "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/tecnologia/portada",
    "https://www.infobae.com/arc/outboundfeeds/rss/category/tecno/",
    # Fuentes oficiales (anuncios confirmados)
    "https://openai.com/news/rss.xml",
    "https://blog.google/technology/ai/rss/",
    "https://deepmind.google/blog/rss.xml",
    "https://nvidianews.nvidia.com/releases.xml",
    "https://huggingface.co/blog/feed.xml",
    # Agregadores (muchos medios a la vez, últimas horas)
    "https://news.google.com/rss/search?q=inteligencia+artificial+when:6h&hl=es-419&gl=AR&ceid=AR:es-419",
    "https://news.google.com/rss/search?q=AI+OR+%22artificial+intelligence%22+when:6h&hl=en-US&gl=US&ceid=US:en",
]

# Nombre de cada medio (igual al que usa Google Noticias, para no contarlo dos veces).
SOURCE_NAMES = {
    "techcrunch.com": "TechCrunch", "theverge.com": "The Verge", "venturebeat.com": "VentureBeat",
    "technologyreview.com": "MIT Technology Review", "arstechnica.com": "Ars Technica",
    "wired.com": "WIRED", "the-decoder.com": "The Decoder", "zdnet.com": "ZDNET",
    "engadget.com": "Engadget", "9to5google.com": "9to5Google", "9to5mac.com": "9to5Mac",
    "cnbc.com": "CNBC", "rss.nytimes.com": "The New York Times", "feeds.bbci.co.uk": "BBC",
    "xataka.com": "Xataka", "hipertextual.com": "Hipertextual", "genbeta.com": "Genbeta",
    "es.wired.com": "WIRED en Español", "feeds.elpais.com": "El País", "infobae.com": "Infobae",
    "openai.com": "OpenAI", "blog.google": "Google", "deepmind.google": "Google DeepMind",
    "nvidianews.nvidia.com": "NVIDIA", "huggingface.co": "Hugging Face",
}
# Un anuncio en el blog oficial de la empresa cuenta como 2 medios: es la fuente primaria.
OFFICIAL_SOURCES = {"OpenAI", "Google", "Google DeepMind", "NVIDIA", "Hugging Face"}

# ---- Ritmo de publicación (modo "último momento") ----
# La tarea revisa las fuentes seguido; estos límites evitan que Instagram trate la
# cuenta como spam (la API permite hasta 50 posts por día).
# 6-10 posts por día es lo recomendado para una cuenta nueva (ver informe de estrategia);
# subir MAX_POSTS_PER_DAY (hasta ~30) solo si las métricas acompañan.
MIN_MINUTES_BETWEEN_POSTS = int(os.getenv("MIN_MINUTES_BETWEEN_POSTS", "45"))
MAX_POSTS_PER_DAY = int(os.getenv("MAX_POSTS_PER_DAY", "10"))

# Medios que no se usan: sitios de recomendaciones bursátiles que se republican
# entre sí y harían pasar una nota copiada por "tendencia".
BLOCKED_SOURCES = {
    "the motley fool", "yahoo finance", "benzinga", "zacks", "investorplace",
    "seeking alpha", "24/7 wall st.", "marketbeat", "insider monkey", "tipranks",
    "nasdaq", "aol.com", "simply wall st", "gurufocus",
}

MAX_AGE_HOURS = int(os.getenv("MAX_AGE_HOURS", "12"))  # solo noticias de las últimas horas
# Mínimo de medios distintos que deben cubrir la historia (reduce el riesgo
# de publicar rumores o noticias falsas). Si ninguna historia llega, no publica.
MIN_SOURCES = int(os.getenv("MIN_SOURCES", "2"))

# ---- Claude ----
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5-5")
