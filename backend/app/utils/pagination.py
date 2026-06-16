"""Shared server-side pagination helpers.

Pagination is opt-in: it only kicks in when the request carries a ``page``
query parameter. This keeps the legacy "return a plain array" behaviour intact
for autocomplete/dropdown callers that fetch the full list.
"""
from flask import request

DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 200


def pagination_requested():
    """True when the client asked for a paginated response."""
    return 'page' in request.args


def get_pagination_args():
    """Parse and clamp (page, page_size) from the current request."""
    page = request.args.get('page', default=1, type=int) or 1
    if page < 1:
        page = 1
    page_size = request.args.get('page_size', default=DEFAULT_PAGE_SIZE, type=int) or DEFAULT_PAGE_SIZE
    page_size = max(1, min(page_size, MAX_PAGE_SIZE))
    return page, page_size


def _envelope(items, total, page, page_size):
    total_pages = (total + page_size - 1) // page_size if total else 0
    return {
        'data': items,
        'total': total,
        'page': page,
        'page_size': page_size,
        'total_pages': total_pages,
    }


def paginate_query(query, page, page_size, serialize):
    """Paginate a SQLAlchemy query at the SQL level (count + limit/offset).

    ``serialize`` maps a row to its dict representation.
    """
    total = query.count()
    rows = query.limit(page_size).offset((page - 1) * page_size).all()
    return _envelope([serialize(r) for r in rows], total, page, page_size)


def paginate_sequence(items, page, page_size):
    """Paginate an already-materialised list of dicts (e.g. fuzzy results)."""
    total = len(items)
    start = (page - 1) * page_size
    return _envelope(items[start:start + page_size], total, page, page_size)
