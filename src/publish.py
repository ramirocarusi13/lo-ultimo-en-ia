"""Publica el carrusel en Instagram con la API oficial (Instagram Graph API).

Requisitos: cuenta de Instagram profesional (Empresa o Creador) y un token de
acceso con permisos instagram_basic + instagram_content_publish.
Las imágenes tienen que estar en una URL pública (Instagram las descarga).
"""
from __future__ import annotations

import os
import time

import requests

HOST = os.getenv("IG_GRAPH_HOST") or "graph.facebook.com"  # o graph.instagram.com
VERSION = os.getenv("IG_GRAPH_VERSION") or "v21.0"


def _api(method: str, path: str, **params) -> dict:
    params["access_token"] = os.environ["IG_ACCESS_TOKEN"]
    r = requests.request(method, f"https://{HOST}/{VERSION}/{path}", params=params, timeout=60)
    data = r.json()
    if r.status_code >= 400 or "error" in data:
        raise RuntimeError(f"Instagram API {path}: {data}")
    return data


def _wait_ready(container_id: str, timeout: int = 300) -> None:
    t0 = time.time()
    while time.time() - t0 < timeout:
        status = _api("GET", container_id, fields="status_code").get("status_code")
        if status == "FINISHED":
            return
        if status in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"Contenedor {container_id} en estado {status}")
        time.sleep(5)
    raise TimeoutError(f"Contenedor {container_id} no terminó de procesarse")


def publish_carousel(image_urls: list[str], caption: str) -> str:
    user = os.environ["IG_USER_ID"]
    children = []
    for url in image_urls:
        c = _api("POST", f"{user}/media", image_url=url, is_carousel_item="true")
        children.append(c["id"])
    for cid in children:
        _wait_ready(cid)
    carousel = _api("POST", f"{user}/media", media_type="CAROUSEL",
                    children=",".join(children), caption=caption)
    _wait_ready(carousel["id"])
    media = _api("POST", f"{user}/media_publish", creation_id=carousel["id"])
    permalink = _api("GET", media["id"], fields="permalink").get("permalink", "")
    print(f"[publish] publicado: {permalink}")
    return permalink
