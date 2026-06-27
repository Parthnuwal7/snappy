"""Tests for the RSS feed parser."""
import os
from datetime import datetime
from app.services.legal_feed import rss

FIXTURE = os.path.join(os.path.dirname(__file__), 'fixtures', 'sample_feed.xml')


def _raw():
    with open(FIXTURE, 'r', encoding='utf-8') as f:
        return f.read()


def test_parse_feed_returns_normalized_items():
    items = rss.parse_feed(_raw())
    assert len(items) == 2  # third entry skipped (no link)
    first = items[0]
    assert first['title'] == 'Alpha v. Beta'
    assert first['source_url'] == 'https://indiankanoon.org/doc/111/'
    assert 'Alpha' in first['summary']
    assert isinstance(first['published_at'], datetime)


def test_parse_feed_handles_empty():
    assert rss.parse_feed('') == []


def test_parse_feed_extracts_image_from_media_content():
    raw = '''<?xml version="1.0"?>
    <rss xmlns:media="http://search.yahoo.com/mrss/" version="2.0"><channel>
      <item><title>With image</title><link>http://x/1</link>
        <media:content url="http://img/pic.jpg"/></item>
      <item><title>No image</title><link>http://x/2</link></item>
    </channel></rss>'''
    items = rss.parse_feed(raw)
    assert items[0]['image_url'] == 'http://img/pic.jpg'
    assert items[1]['image_url'] is None


def test_parse_feed_falls_back_to_enclosure_image():
    raw = '''<?xml version="1.0"?>
    <rss version="2.0"><channel>
      <item><title>Enc</title><link>http://x/3</link>
        <enclosure url="http://img/enc.png" type="image/png"/></item>
    </channel></rss>'''
    assert rss.parse_feed(raw)[0]['image_url'] == 'http://img/enc.png'
