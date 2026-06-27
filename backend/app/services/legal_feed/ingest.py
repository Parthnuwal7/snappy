"""Orchestrates one ingestion run across all enabled sources."""
from datetime import datetime

from app.models.models import db, LegalFeedSource, LegalFeedItem, LegalFeedRun
from app.utils.legal_feed_dedup import compute_dedup_key
from app.services.legal_feed import rss
from app.services.legal_feed.enrichment import get_enrichment_client, enrich_item

# Fetchers keyed by source.kind. v1 ships RSS only.
FETCHERS = {'rss': rss}


def _ingest_source(source) -> dict:
    result = {'source_id': source.id, 'fetched': 0, 'inserted': 0,
              'inserted_ids': [], 'error': None}
    fetcher = FETCHERS.get(source.kind)
    if fetcher is None:
        result['error'] = f'unknown source kind: {source.kind}'
        return result
    try:
        raw = fetcher.fetch_raw(source.feed_url)
        items = fetcher.parse_feed(raw)
        result['fetched'] = len(items)
        for it in items:
            key = compute_dedup_key(it['source_url'], source.name, it['title'])
            if LegalFeedItem.query.filter_by(dedup_key=key).first():
                continue
            row = LegalFeedItem(
                source_id=source.id, content_type=source.content_type,
                title=it['title'], summary=it.get('summary'),
                source_url=it['source_url'], source_name=source.name,
                court=source.court, published_at=it.get('published_at'),
                image_url=it.get('image_url'), hidden=False, dedup_key=key,
            )
            db.session.add(row)
            db.session.flush()
            result['inserted'] += 1
            result['inserted_ids'].append(row.id)
        db.session.commit()
    except Exception as exc:  # one bad source must not abort the run
        db.session.rollback()
        result['error'] = str(exc)
    return result


def _enrich_ids(ids, client) -> tuple:
    """Enrich the given item ids. Returns (enriched, failed)."""
    enriched = failed = 0
    for item_id in ids:
        item = LegalFeedItem.query.get(item_id)
        # Only news is enriched for now; skip judgements without counting them.
        if item is None or item.enriched_at is not None or item.content_type != 'news':
            continue
        if enrich_item(item, client):
            enriched += 1
        else:
            failed += 1
    db.session.commit()
    return enriched, failed


def run_ingestion(trigger: str) -> dict:
    run = LegalFeedRun(started_at=datetime.utcnow(), trigger=trigger,
                       status='success', total_ingested=0, results=[])
    db.session.add(run)
    db.session.commit()

    sources = LegalFeedSource.query.filter_by(enabled=True).all()
    results = [_ingest_source(s) for s in sources]

    enriched = failed = 0
    client = get_enrichment_client()
    if client is not None:
        new_ids = [i for r in results for i in r.get('inserted_ids', [])]
        enriched, failed = _enrich_ids(new_ids, client)

    error_count = sum(1 for r in results if r['error'])
    if error_count == 0:
        status = 'success'
    elif error_count == len(results):
        status = 'failed'
    else:
        status = 'partial'

    # inserted_ids is internal bookkeeping; drop it from the persisted audit log.
    for r in results:
        r.pop('inserted_ids', None)

    run.finished_at = datetime.utcnow()
    run.total_ingested = sum(r['inserted'] for r in results)
    run.enriched = enriched
    run.enrich_failed = failed
    run.status = status
    run.results = results
    db.session.commit()
    return run.to_dict()


def enrich_backlog(limit=100, client=None) -> dict:
    """Deliberately enrich already-ingested items (enriched_at IS NULL)."""
    client = client or get_enrichment_client()
    if client is None:
        return {'attempted': 0, 'enriched': 0, 'failed': 0}
    rows = (LegalFeedItem.query
            .filter(LegalFeedItem.enriched_at.is_(None),
                    LegalFeedItem.content_type == 'news')
            .order_by(LegalFeedItem.id.desc()).limit(limit).all())
    ids = [r.id for r in rows]
    enriched, failed = _enrich_ids(ids, client)
    return {'attempted': len(ids), 'enriched': enriched, 'failed': failed}
