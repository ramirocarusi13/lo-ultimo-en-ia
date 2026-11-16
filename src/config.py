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
ACCENT = (0, 220, 255)        # celeste eléctrico: palabras resaltadas
VIOLET = (124, 58, 237)       # violeta: logo, etiqueta y botón
VIOLET_DARK = (60, 20, 140)
BG = (8, 10, 28)              # azul noche de fondo
WHITE = (255, 255, 255)
SIZE = (1080, 1350)           # formato vertical 4:5 de Instagram

# ---- Fuentes (RSS) ----
# Mezcla de medios en inglés y español. Una historia que aparece en varios
# medios a la vez se considera "en tendencia".
FEEDS = [
    "https://techcrunch.com/category/artificial-intelligence/feed/",
    "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
    "https://venturebeat.com/category/ai/feed/",
    "https://www.technologyreview.com/topic/artificial-intelligence/feed",
    "https://arstechnica.com/ai/feed/",
    "https://www.wired.com/feed/tag/ai/latest/rss",
    "https://www.xataka.com/tag/inteligencia-artificial/rss2.xml",
    "https://hipertextual.com/tag/inteligencia-artificial/feed",
    "https://news.google.com/rss/search?q=inteligencia+artificial+when:1d&hl=es-419&gl=AR&ceid=AR:es-419",
    "https://news.google.com/rss/search?q=artificial+intelligence+when:1d&hl=en-US&gl=US&ceid=US:en",
]

MAX_AGE_HOURS = int(os.getenv("MAX_AGE_HOURS", "36"))
# Mínimo de medios distintos que deben cubrir la historia (reduce el riesgo
# de publicar rumores o noticias falsas). Si ninguna historia llega, no publica.
MIN_SOURCES = int(os.getenv("MIN_SOURCES", "2"))

# ---- Claude ----
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-opus-5-5")
