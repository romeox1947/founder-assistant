from urllib.parse import urlparse, urlunparse
import hashlib

def normalize_url(url):
    p = urlparse(url.strip())
    if p.scheme not in ("http", "https"):
        raise ValueError("Please provide a valid http:// or https:// URL.")
    return urlunparse((p.scheme, p.netloc, p.path or "/", "", p.query, ""))

def content_hash(text):
    return hashlib.sha256((text or "").encode("utf-8", errors="ignore")).hexdigest()

def make_source_label(doc):
    return doc.get("title") or doc.get("source_url")
