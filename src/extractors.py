import time
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup
import trafilatura
from yt_dlp import YoutubeDL
from src.utils import normalize_url, content_hash

HEADERS = {"User-Agent": "SatvicIntelligenceResearchBot/1.0 (personal research demo)"}

def _robots_allowed(base_url, target_url):
    parsed = urlparse(base_url)
    robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
    rp = RobotFileParser()
    rp.set_url(robots_url)
    try:
        rp.read()
        return rp.can_fetch(HEADERS["User-Agent"], target_url)
    except Exception:
        # If robots cannot be read, proceed cautiously; the site may still block requests.
        return True

def crawl_website(start_url, max_pages=15, delay=0.7):
    start_url = normalize_url(start_url)
    parsed = urlparse(start_url)
    domain = parsed.netloc.lower()
    queue = [start_url]
    visited = set()
    results = []
    session = requests.Session()
    session.headers.update(HEADERS)

    while queue and len(visited) < max_pages:
        url = queue.pop(0)
        if url in visited:
            continue
        visited.add(url)
        if not _robots_allowed(start_url, url):
            continue
        try:
            response = session.get(url, timeout=18)
            response.raise_for_status()
            ctype = response.headers.get("Content-Type", "")
            if "text/html" not in ctype:
                continue
            html = response.text
            extracted = trafilatura.extract(
                html, include_comments=False, include_tables=True,
                favor_recall=True, url=url
            )
            soup = BeautifulSoup(html, "html.parser")
            title = soup.title.get_text(" ", strip=True) if soup.title else url
            if extracted and len(extracted.strip()) > 120:
                results.append({
                    "source_type": "website", "source_url": url, "title": title,
                    "content": extracted[:50000],
                    "metadata": {"domain": domain, "content_hash": content_hash(extracted)}
                })
            for a in soup.find_all("a", href=True):
                href = urljoin(url, a["href"]).split("#")[0]
                p = urlparse(href)
                if p.scheme not in ("http", "https") or p.netloc.lower() != domain:
                    continue
                if any(p.path.lower().endswith(ext) for ext in [".pdf",".jpg",".jpeg",".png",".zip",".mp4",".xml"]):
                    continue
                clean = normalize_url(href)
                if clean not in visited and clean not in queue and len(queue) < max_pages * 5:
                    queue.append(clean)
        except requests.RequestException:
            pass
        time.sleep(delay)
    return results

def _transcript(video_id):
    try:
        from youtube_transcript_api import YouTubeTranscriptApi
        api = YouTubeTranscriptApi()
        fetched = api.fetch(video_id)
        parts = []
        for item in fetched:
            text = getattr(item, "text", None)
            if text:
                parts.append(text)
        return " ".join(parts)
    except Exception:
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
            data = YouTubeTranscriptApi.get_transcript(video_id)
            return " ".join(x.get("text", "") for x in data)
        except Exception:
            return ""

def fetch_youtube_channel(channel_url, max_videos=20, with_transcripts=True):
    channel_url = channel_url.strip()
    if not channel_url.startswith(("http://", "https://")):
        raise ValueError("Enter a full YouTube channel URL.")
    opts = {
        "extract_flat": "in_playlist",
        "playlistend": max_videos,
        "quiet": True,
        "no_warnings": True,
        "ignoreerrors": True,
        "skip_download": True,
    }
    messages = []
    results = []
    with YoutubeDL(opts) as ydl:
        info = ydl.extract_info(channel_url.rstrip("/") + "/videos", download=False)
    entries = (info or {}).get("entries") or []
    for entry in entries[:max_videos]:
        if not entry:
            continue
        video_id = entry.get("id")
        if not video_id:
            continue
        video_url = entry.get("url") or f"https://www.youtube.com/watch?v={video_id}"
        if not video_url.startswith("http"):
            video_url = f"https://www.youtube.com/watch?v={video_id}"
        title = entry.get("title") or f"YouTube video {video_id}"
        description = entry.get("description") or ""
        transcript = _transcript(video_id) if with_transcripts else ""
        content = "\n".join([
            f"Video title: {title}",
            f"Description: {description}",
            f"Transcript:\n{transcript}" if transcript else "Transcript: Not publicly available or retrieval failed."
        ])
        results.append({
            "source_type": "youtube",
            "source_url": video_url,
            "title": title,
            "content": content[:50000],
            "metadata": {
                "video_id": video_id,
                "channel": channel_url,
                "transcript_available": bool(transcript),
                "duration": entry.get("duration"),
                "upload_date": entry.get("upload_date"),
            }
        })
        messages.append(f"{title}: {'transcript found' if transcript else 'metadata only (no transcript)'}")
        time.sleep(0.25)
    return results, messages
