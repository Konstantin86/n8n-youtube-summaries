from fastapi import FastAPI, HTTPException, Header
from typing import List, Optional, Any
from pydantic import BaseModel
import os, json, time, threading, hashlib, pathlib, re

from youtube_transcript_api import (
    YouTubeTranscriptApi,
    NoTranscriptFound,
    TranscriptsDisabled,
)
from youtube_transcript_api.proxies import WebshareProxyConfig

app = FastAPI(title="YT Transcript API", version="1.1.0")

# ---------- Configuration ----------
BASE_DIR = pathlib.Path(os.path.expanduser("~/yt-transcript"))
BASE_DIR.mkdir(parents=True, exist_ok=True)

CACHE_DIR = BASE_DIR / "cache"
CACHE_DIR.mkdir(parents=True, exist_ok=True)

WEBSHARE_USER = os.getenv("WEBSHARE_USER", "")
WEBSHARE_PASS = os.getenv("WEBSHARE_PASS", "")
WEBSHARE_LOCATIONS = os.getenv("WEBSHARE_LOCATIONS", "")  # e.g. "de,us"

# Polite throttle between remote calls to reduce bans
REQUEST_SLEEP_SEC = float(os.getenv("TRANSCRIPT_REQUEST_SLEEP_SEC", "0.6"))

_lock = threading.Lock()

# ---------- Transcript cache ----------
def _cache_path(video_id: str, lang_key: str) -> pathlib.Path:
    h = hashlib.sha1(f"{video_id}:{lang_key}".encode()).hexdigest()[:16]
    return CACHE_DIR / f"{video_id}_{lang_key}_{h}.txt"

def _cache_read(video_id: str, lang_key: str) -> Optional[str]:
    p = _cache_path(video_id, lang_key)
    if p.exists():
        return p.read_text(encoding="utf-8")
    return None

def _cache_write(video_id: str, lang_key: str, text: str):
    _cache_path(video_id, lang_key).write_text(text, encoding="utf-8")

# ---------- Proxy-enabled client ----------
def make_ytt_client() -> YouTubeTranscriptApi:
    if WEBSHARE_USER and WEBSHARE_PASS:
        locs = [s.strip() for s in WEBSHARE_LOCATIONS.split(",") if s.strip()] or None
        cfg = WebshareProxyConfig(
            proxy_username=WEBSHARE_USER,
            proxy_password=WEBSHARE_PASS,
            filter_ip_locations=locs,
        )
        return YouTubeTranscriptApi(proxy_config=cfg)
    return YouTubeTranscriptApi()

# ---------- Utility ----------
def _to_plain_text(segments: Any) -> str:
    # supports both FetchedTranscript and raw list[dict]
    raw = getattr(segments, "to_raw_data", None)
    data = raw() if callable(raw) else segments
    lines: List[str] = []
    for s in data:
        t = s.get("text", "")
        if t:
            lines.append(t)
    return "\n".join(lines)

def _looks_ip_block(msg: str) -> bool:
    msg = (msg or "").lower()
    return (
        "blocking requests from your ip" in msg
        or "requestblocked" in msg
        or "ipblocked" in msg
        or "captcha" in msg
    )

# =========================
#  TRANSCRIPT ENDPOINT
# =========================

@app.get("/transcript")
def get_transcript(
    videoId: str,
    lang: Optional[str] = "en",
    langs: Optional[str] = None,   # e.g., "en,uk,ru"
    plain: bool = True,            # default to plain text for your flow
    preserve_formatting: bool = False,
):
    prefer: List[str] = [x.strip() for x in (langs.split(",") if langs else [lang]) if x.strip()] or ["en"]
    lang_key = ",".join(prefer)

    # 1) Serve from cache
    cached = _cache_read(videoId, lang_key)
    if cached and plain:
        return {"videoId": videoId, "langPref": prefer, "text": cached, "cached": True}

    try:
        # 2) Polite throttle + proxy-enabled client
        time.sleep(REQUEST_SLEEP_SEC)
        ytt = make_ytt_client()

        # Try preferred languages first
        fetched = ytt.fetch(videoId, languages=prefer, preserve_formatting=preserve_formatting)

        if plain:
            text = _to_plain_text(fetched)
            if text:
                _cache_write(videoId, lang_key, text)
                return {"videoId": videoId, "langPref": prefer, "text": text, "cached": False}
            # rare: empty
            raise HTTPException(status_code=404, detail="Empty transcript")
        else:
            # raw JSON segments
            data = getattr(fetched, "to_raw_data", lambda: fetched)()
            return {"videoId": videoId, "langPref": prefer, "transcript": data, "cached": False}

    except (NoTranscriptFound, TranscriptsDisabled):
        try:
            time.sleep(REQUEST_SLEEP_SEC)
            ytt = make_ytt_client()
            tl = ytt.list(videoId)
            target = prefer[0]
            for t in tl:
                if t.is_translatable:
                    translated = t.translate(target).fetch(preserve_formatting=preserve_formatting)
                    if plain:
                        text = _to_plain_text(translated)
                        if text:
                            _cache_write(videoId, lang_key, text)
                            return {"videoId": videoId, "langPref": prefer, "text": text, "cached": False, "translated": True}
                        raise HTTPException(status_code=404, detail="Empty translated transcript")
                    else:
                        data = getattr(translated, "to_raw_data", lambda: translated)()
                        return {"videoId": videoId, "langPref": prefer, "transcript": data, "cached": False, "translated": True}
        except Exception as e2:
            msg = str(e2)
            if _looks_ip_block(msg):
                raise HTTPException(status_code=429, detail="YouTube temporarily blocked this IP (translation)") from e2
            raise HTTPException(status_code=404, detail="No transcript available (including translation).") from e2

    except Exception as e:
        msg = str(e)
        if _looks_ip_block(msg):
            raise HTTPException(status_code=429, detail="YouTube temporarily blocked this IP") from e
        raise HTTPException(status_code=500, detail=msg) from e