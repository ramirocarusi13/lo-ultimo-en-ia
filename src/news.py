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

from config import FEEDS, MAX_AGE_HOURS, MIN_SOURCES, STATE_FILE

UA = {"User-Agent": "Mozilla/5.0 (compatible; news-carousel-bot/1.0)"}

STOP = set("""
a al ante con contra de del desde el en entre es esta este hacia la las lo los
para por que se sin sobre su sus tras un una y o u ya mas más como the of to in
for on and with is are its it's at by from as an be has have new how why what
after over into will this that ai ia inteligencia artificial
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

    def score(self) -> float:
        newest = max(a.published for a in self.articles)
        age_h = (time.time() - newest) / 3600
        return len(self.sources) * 10 - age_h * 0.5


def _words(title: str) -> set[str]:
    toks = re.findall(r"[a-záéíóúñü0-9\.]+", title.lower())
    return {t for t in toks if t not in STOP and len(t) > 2}


def _source_of(entry, feed_url: str) -> str:
    # Google News trae el medio real en entry.source
    src = getattr(entry, "source", None)
    if src and getattr(src, "title", None):
        return src.title
    return urlparse(feed_url).netloc.replace("www.", "")


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
            title = re.sub(r"\s+-\s+[^-]+$", "", e.get("title", "")).strip()  # quita " - Medio"
            summary = BeautifulSoup(e.get("summary", ""), "html.parser").get_text(" ", strip=True)
            out.append(Article(title, e.get("link", ""), _source_of(e, url), ts, summary[:600]))
    print(f"[news] {len(out)} artículos recientes")
    return out


def cluster(articles: list[Article], threshold: float = 0.3) -> list[Story]:
    stories: list[tuple[set[str], Story]] = []
    for a in sorted(articles, key=lambda x: -x.published):
        w = _words(a.title)
        if not w:
            continue
        best, best_sim = None, 0.0
        for words, st in stories:
            sim = len(w & words) / len(w | words)
            if sim > best_sim:
                best, best_sim = (words, st), sim
        if best and best_sim >= threshold:
            best[0].update(w)
            best[1].articles.append(a)
        else:
            stories.append((set(w), Story([a])))
    return [s for _, s in stories]


def load_posted() -> dict:
    if STATE_FILE.exists():
        return json.loads(STATE_FILE.read_text())
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
        soup = BeautifulSoup(r.text, "html.parser")
        og = soup.find("meta", property="og:image") or soup.find("meta", attrs={"name": "twitter:image"})
        if og and og.get("content", "").startswith("http"):
            article.image = og["content"]
        paras = [p.get_text(" ", strip=True) for p in soup.find_all("p")]
        article.text = "\n".join(p for p in paras if len(p) > 60)[:6000]
        article.link = r.url
    except Exception as e:
        print(f"[news] no se pudo leer {article.link}: {e}")
    return article


def pick_trending_story() -> Story | None:
    posted = load_posted()
    stories = [s for s in cluster(fetch_articles()) if not already_posted(s, posted)]
    stories = [s for s in stories if len(s.sources) >= MIN_SOURCES]
    if not stories:
        print(f"[news] ninguna historia nueva cubierta por >= {MIN_SOURCES} medios")
        return None
    best = max(stories, key=Story.score)
    # nos quedamos con un artículo por medio, máx 4
    seen, arts = set(), []
    for a in best.articles:
        if a.source not in seen:
            seen.add(a.source)
            arts.append(enrich(a))
        if len(arts) == 4:
            break
    best.articles = arts
    print(f"[news] elegida: '{arts[0].title}' ({len(best.sources)} medios)")
    return best


def mark_posted(story: Story, permalink: str | None = None) -> None:
    posted = load_posted()
    posted.setdefault("links", []).extend(a.link for a in story.articles)
    posted.setdefault("titles", []).append(story.articles[0].title)
    posted.setdefault("history", []).append(
        {"title": story.articles[0].title, "at": int(time.time()), "permalink": permalink}
    )
    posted["links"] = posted["links"][-1000:]
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(posted, ensure_ascii=False, indent=1))
