"""Busca noticias de IA en varios medios y elige la más 'en tendencia'.

Tendencia = la misma historia cubierta por varios medios distintos en las
últimas horas. Se agrupan titulares parecidos y se puntúa cada grupo por
cantidad de medios y por lo reciente que es.
"""
from __future__ import annotations

import calendar
import json
import re
import time
from dataclasses import dataclass, field
from urllib.parse import urlparse

import feedparser
import requests
from bs4 import BeautifulSoup

from config import (BLOCKED_SOURCES, FEEDS, MAX_AGE_HOURS, MAX_POSTS_PER_DAY,
                    MIN_MINUTES_BETWEEN_POSTS, MIN_SOURCES, OFFICIAL_SOURCES, SOURCE_NAMES,
                    STATE_FILE)

UA = {"User-Agent": "Mozilla/5.0 (compatible; news-carousel-bot/1.0)"}

STOP = set("""
a al ante con contra de del desde el en entre es esta este hacia la las lo los
para por que se sin sobre su sus tras un una y o u ya mas más como the of to in
for on and with is are its it's at by from as an be has have new how why what
after over into will this that ai ia inteligencia artificial intelligence
could would says said about just more most latest here than their they you your news
""".split())


@dataclass
class Article:
    title: str
    link: str
    source: str
    published: float
    summary: str = ""
    image: str | None = None
    text: str = ""


@dataclass
class Story:
    articles: list[Article] = field(default_factory=list)

    @property
    def sources(self) -> set[str]:
        return {a.source for a in self.articles}

    @property
    def key(self) -> str:
        return self.articles[0].link

    @property
    def coverage(self) -> int:
        """Medios distintos que la cubren con su propio titular. Una nota copiada
        tal cual en varios sitios (sindicación) cuenta como uno solo."""
        titles = {re.sub(r"\W+", " ", a.title.lower()).strip() for a in self.articles}
        official = any(a.source in OFFICIAL_SOURCES for a in self.articles)
        return min(len(self.sources), len(titles)) + (1 if official else 0)

    def score(self) -> float:
        # lo más cubierto y lo más reciente primero (modo "último momento")
        newest = max(a.published for a in self.articles)
        age_h = (time.time() - newest) / 3600
        return self.coverage * 10 - age_h * 2


def _words(title: str) -> set[str]:
    toks = re.findall(r"[a-záéíóúñü0-9\.]+", title.lower())
    return {t for t in toks if t not in STOP and len(t) > 2}


def _source_of(entry, feed_url: str) -> str:
    # Google News trae el medio real en entry.source
    src = getattr(entry, "source", None)
    if src and getattr(src, "title", None):
        name = src.title.strip()
        return {"BBC News": "BBC", "NVIDIA Newsroom": "NVIDIA", "The Verge.": "The Verge"}.get(name, name)
    host = urlparse(feed_url).netloc.replace("www.", "")
    return SOURCE_NAMES.get(host, host)


def fetch_articles() -> list[Article]:
    cutoff = time.time() - MAX_AGE_HOURS * 3600
    out: list[Article] = []
    for url in FEEDS:
        try:
            resp = requests.get(url, headers=UA, timeout=20)
            resp.raise_for_status()
            feed = feedparser.parse(resp.content)
        except Exception as e:  # una fuente caída no frena al resto
            print(f"[news] fuente falló {url}: {e}")
            continue
        for e in feed.entries[:30]:
            t = e.get("published_parsed") or e.get("updated_parsed")
            ts = calendar.timegm(t) if t else time.time()
            if ts < cutoff:
                continue
            source = _source_of(e, url)
            if source.lower() in BLOCKED_SOURCES:
                continue
            title = re.sub(r"\s+-\s+[^-]+$", "", e.get("title", "")).strip()  # quita " - Medio"
            summary = BeautifulSoup(e.get("summary", ""), "html.parser").get_text(" ", strip=True)
            out.append(Article(title, e.get("link", ""), source, ts, summary[:600]))
    print(f"[news] {len(out)} artículos recientes")
    return out


def _similarity(a: set[str], b: set[str]) -> float:
    """Palabras en común sobre el titular más corto, con al menos 2 en común.
    Funciona mejor que Jaccard con titulares de largo distinto y entre idiomas
    (los nombres propios como 'Jensen Huang' o 'Nvidia' se repiten)."""
    shared = a & b
    if len(shared) < 2:
        return 0.0
    return len(shared) / min(len(a), len(b))


def cluster(articles: list[Article], threshold: float = 0.4) -> list[Story]:
    # cada grupo guarda las palabras de cada titular; un artículo se suma al grupo
    # si se parece lo suficiente a alguno de sus titulares
    groups: list[tuple[list[set[str]], Story]] = []
    for a in sorted(articles, key=lambda x: -x.published):
        w = _words(a.title)
        if not w:
            continue
        best, best_sim = None, 0.0
        for word_sets, st in groups:
            sim = max(_similarity(w, ws) for ws in word_sets)
            if sim > best_sim:
                best, best_sim = (word_sets, st), sim
        if best and best_sim >= threshold:
            best[0].append(w)
            best[1].articles.append(a)
        else:
            groups.append(([w], Story([a])))
    return [s for _, s in groups]


def load_posted() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    return {"links": [], "titles": []}


def already_posted(story: Story, posted: dict) -> bool:
    links = set(posted.get("links", []))
    if any(a.link in links for a in story.articles):
        return True
    w = _words(story.articles[0].title)
    for t in posted.get("titles", [])[-200:]:
        tw = _words(t)
        if tw and len(w & tw) / len(w | tw) >= 0.35:
            return True
    return False


def enrich(article: Article) -> Article:
    """Descarga la nota: imagen principal (og:image) y texto."""
    try:
        r = requests.get(article.link, headers=UA, timeout=20, allow_redirects=True)
        if urlparse(r.url).netloc.endswith("news.google.com"):
            # Google Noticias no redirige a la nota sin JavaScript: su página trae el
            # logo de Google como imagen y ningún texto útil. Nos quedamos con el resumen.
            return article
        soup = BeautifulSoup(r.text, "html.parser")
        og = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
        if og and og.get("content", "").startswith("http"):
            article.image = og["content"]
        paras = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        boiler = ("daily email digest", "Sign in to", "subsidiary of", "newsletter")
        paras = [p for p in dict.fromkeys(paras)  # sin repetidos (avisos del sitio)
                 if len(p) > 60 and not any(b in p for b in boiler)]
        article.text = "\n".join(paras)[:6000]
        article.link = r.url
    except Exception as e:
        print(f"[news] no se pudo leer {article.link}: {e}")
    return article


def rate_limited(posted: dict) -> str | None:
    """Motivo para no publicar todavía (ritmo máximo), o None si se puede."""
    now = time.time()
    posts = [h["at"] for h in posted.get("history", []) if h.get("kind", "post") == "post"]
    if posts and now - max(posts) < MIN_MINUTES_BETWEEN_POSTS * 60:
        mins = int((now - max(posts)) / 60)
        return f"el último post fue hace {mins} min (mínimo {MIN_MINUTES_BETWEEN_POSTS})"
    if sum(1 for t in posts if now - t < 86400) >= MAX_POSTS_PER_DAY:
        return f"ya hay {MAX_POSTS_PER_DAY} posts en las últimas 24 h"
    return None


def pick_trending_story() -> Story | None:
    posted = load_posted()
    wait = rate_limited(posted)
    if wait:
        print(f"[news] en pausa: {wait}")
        return None
    stories = [s for s in cluster(fetch_articles()) if not already_posted(s, posted)]
    stories = [s for s in stories if s.coverage >= MIN_SOURCES]
    if not stories:
        print(f"[news] ninguna historia nueva cubierta por >= {MIN_SOURCES} medios")
        return None
    best = max(stories, key=Story.score)
    # nos quedamos con un artículo por medio, máx 4; primero los enlaces directos
    # al medio (los de Google Noticias no permiten leer la nota)
    seen, arts = set(), []
    for a in sorted(best.articles, key=lambda x: "news.google.com" in x.link):
        if a.source not in seen:
            seen.add(a.source)
            arts.append(enrich(a))
        if len(arts) == 4:
            break
    best.articles = arts
    print(f"[news] elegida: '{arts[0].title}' ({best.coverage} medios)")
    return best


def mark_posted(story: Story, permalink: str | None = None, kind: str = "post") -> None:
    """kind: "post" (se armó un carrusel) o "skip" (noticia descartada)."""
    posted = load_posted()
    if story.articles and all(a.link in set(posted.get("links", [])) for a in story.articles):
        return  # ya registrada (p. ej. al rearmar el mismo post)
    posted.setdefault("links", []).extend(a.link for a in story.articles)
    posted.setdefault("titles", []).append(story.articles[0].title)
    posted.setdefault("history", []).append(
        {"title": story.articles[0].title, "at": int(time.time()), "permalink": permalink, "kind": kind}
    )
    posted["links"] = posted["links"][-1000:]
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(posted, ensure_ascii=False, indent=1), encoding="utf-8")
