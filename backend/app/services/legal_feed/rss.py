"""RSS fetching and parsing for the legal feed pipeline.

Split into a network half (fetch_raw) and a pure half (parse_feed) so the
parser can be unit-tested against a fixture without hitting the network.
"""
import time
from datetime import datetime

import feedparser
import requests

USER_AGENT = 'SnappyLegalFeed/1.0 (+https://snappy.app)'
TIMEOUT_SECONDS = 30


def fetch_raw(url: str) -> str:
    resp = requests.get(url, headers={'User-Agent': USER_AGENT}, timeout=TIMEOUT_SECONDS)
    resp.raise_for_status()
    return resp.text


def _parse_date(entry):
    parsed = entry.get('published_parsed') or entry.get('updated_parsed')
    if parsed:
        return datetime.fromtimestamp(time.mktime(parsed))
    return None


def _extract_image(entry):
    media = entry.get('media_content') or []
    for m in media:
        url = m.get('url')
        if url:
            return url
    for enc in entry.get('enclosures') or []:
        if str(enc.get('type', '')).startswith('image') and enc.get('href'):
            return enc.get('href')
        if enc.get('href') and not enc.get('type'):
            return enc.get('href')
    thumb = entry.get('media_thumbnail') or []
    if thumb and thumb[0].get('url'):
        return thumb[0]['url']
    return None


def parse_feed(raw: str) -> list:
    feed = feedparser.parse(raw)
    items = []
    for entry in feed.entries:
        title = (entry.get('title') or '').strip()
        link = (entry.get('link') or '').strip()
        if not title or not link:
            continue
        items.append({
            'title': title,
            'summary': (entry.get('summary') or '').strip() or None,
            'source_url': link,
            'published_at': _parse_date(entry),
            'image_url': _extract_image(entry),
        })
    return items
