"""User-facing legal feed API + scheduler ingest endpoint."""
import os
from flask import Blueprint, request, jsonify, g

from app.middleware.jwt_auth import jwt_required
from app.models.auth import User
from app.utils.pagination import pagination_requested, get_pagination_args
from app.services.legal_feed.query import query_feed, list_courts, query_for_you
from app.services.legal_feed.preferences import get_preference, upsert_preference
from app.services.legal_feed.events import record_event, get_rejected_item_ids
from app.services.legal_feed.ingest import run_ingestion

bp = Blueprint('legal_feed', __name__)


def _current_user_id():
    user = User.query.filter_by(supabase_id=getattr(g, 'user_id', None)).first()
    return user.id if user else None


@bp.route('/legal-feed', methods=['GET'])
@jwt_required
def get_feed():
    if pagination_requested():
        page, page_size = get_pagination_args()
    else:
        page, page_size = 1, 50
    uid = _current_user_id()
    demote_ids = get_rejected_item_ids(uid) if uid else None
    return jsonify(query_feed(
        content_type=request.args.get('type'),
        court=request.args.get('court'),
        page=page, page_size=page_size, demote_ids=demote_ids,
    ))


@bp.route('/legal-feed/courts', methods=['GET'])
@jwt_required
def get_courts():
    return jsonify({'courts': list_courts()})


@bp.route('/legal-feed/for-you', methods=['GET'])
@jwt_required
def get_for_you():
    uid = _current_user_id()
    if uid is None:
        return jsonify({'error': 'User not found'}), 401
    limit = request.args.get('limit', default=10, type=int)
    offset = request.args.get('offset', default=0, type=int)
    data = query_for_you(uid, content_type=request.args.get('type'),
                         limit=limit, offset=offset)
    return jsonify({'data': data})


@bp.route('/legal-feed/preferences', methods=['GET'])
@jwt_required
def get_preferences():
    uid = _current_user_id()
    if uid is None:
        return jsonify({'error': 'User not found'}), 401
    pref = get_preference(uid)
    if pref is None:
        return jsonify({'user_id': uid, 'topic_weights': {}, 'courts': [],
                        'interest_phrases': [], 'updated_at': None})
    return jsonify(pref.to_dict())


@bp.route('/legal-feed/preferences', methods=['PUT'])
@jwt_required
def put_preferences():
    uid = _current_user_id()
    if uid is None:
        return jsonify({'error': 'User not found'}), 401
    body = request.get_json() or {}
    pref = upsert_preference(
        uid, body.get('topic_weights', {}), body.get('courts', []),
        body.get('interest_phrases', []),
    )
    return jsonify(pref.to_dict())


@bp.route('/legal-feed/events', methods=['POST'])
@jwt_required
def post_event():
    uid = _current_user_id()
    if uid is None:
        return jsonify({'error': 'User not found'}), 401
    body = request.get_json() or {}
    if record_event(uid, body.get('item_id'), body.get('kind')):
        return jsonify({'ok': True})
    return jsonify({'error': 'invalid event'}), 400


@bp.route('/legal-feed/ingest', methods=['POST'])
def ingest():
    secret = os.getenv('LEGAL_FEED_INGEST_SECRET')
    if not secret or request.headers.get('X-Ingest-Secret') != secret:
        return jsonify({'error': 'unauthorized'}), 401
    return jsonify(run_ingestion('scheduled'))
