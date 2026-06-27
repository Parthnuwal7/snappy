"""Eager loading (no N+1) + opt-in pagination on the case/writing/task list endpoints.

Two guarantees per endpoint:
  * Listing rows that each reference a *distinct* case_file fires ONE batched
    SELECT against case_files (selectinload), not one-per-row (the N+1 bug).
  * A ``?page=`` query returns the {data,total,page,page_size,total_pages}
    envelope at page_size 50; without it the legacy plain array is preserved.
"""
from sqlalchemy import event

from app.models.models import db, Client
from app.models.auth import User
from app.models.case import CaseFile
from app.models.writing import WritingDoc
from app.models.task import Task


def _owner_uid():
    return User.query.first().id


def _make_case(firm_id, uid, i):
    c = Client(firm_id=firm_id, created_by_user_id=uid, name=f'Client {i:03d}')
    db.session.add(c)
    db.session.flush()
    cf = CaseFile(firm_id=firm_id, created_by_user_id=uid,
                  case_number=f'CF/2026/{i:04d}', title=f'Matter {i:03d}', client_id=c.id)
    db.session.add(cf)
    db.session.flush()
    return cf


def _seed_drafts(app, firm_id, n, link_distinct_cases):
    with app.app_context():
        uid = _owner_uid()
        for i in range(n):
            cf = _make_case(firm_id, uid, i) if link_distinct_cases else None
            db.session.add(WritingDoc(firm_id=firm_id, created_by_user_id=uid, kind='draft',
                                      title=f'Draft {i:03d}', body='',
                                      case_file_id=cf.id if cf else None))
        db.session.commit()


def _seed_tasks(app, firm_id, n, link_distinct_cases):
    with app.app_context():
        uid = _owner_uid()
        for i in range(n):
            cf = _make_case(firm_id, uid, i) if link_distinct_cases else None
            db.session.add(Task(firm_id=firm_id, created_by_user_id=uid, title=f'Task {i:03d}',
                                case_file_id=cf.id if cf else None))
        db.session.commit()


class _QueryCounter:
    """Count SQL statements that hit a given table during a block."""

    def __init__(self, app, table):
        self.app = app
        self.table = table.lower()
        self.count = 0

    def __enter__(self):
        with self.app.app_context():
            self._engine = db.engine
        event.listen(self._engine, 'before_cursor_execute', self._cb)
        return self

    def _cb(self, conn, cursor, statement, params, context, executemany):
        s = statement.lower()
        if s.startswith('select') and f'from {self.table}' in s:
            self.count += 1

    def __exit__(self, *exc):
        event.remove(self._engine, 'before_cursor_execute', self._cb)
        return False


# ---- Eager loading: no N+1 against case_files ----

def test_drafts_list_batches_case_file_lookups(app, client, make_owner):
    headers, firm_id = make_owner()
    _seed_drafts(app, firm_id, 5, link_distinct_cases=True)
    with _QueryCounter(app, 'case_files') as qc:
        resp = client.get('/api/v1/drafts', headers=headers)
    assert resp.status_code == 200
    assert len(resp.get_json()) == 5
    # selectinload => exactly one IN(...) batch, not one query per distinct case.
    assert qc.count == 1


def test_tasks_list_batches_case_file_lookups(app, client, make_owner):
    headers, firm_id = make_owner()
    _seed_tasks(app, firm_id, 5, link_distinct_cases=True)
    with _QueryCounter(app, 'case_files') as qc:
        resp = client.get('/api/v1/tasks', headers=headers)
    assert resp.status_code == 200
    assert len(resp.get_json()) == 5
    assert qc.count == 1


def test_case_files_list_batches_client_lookups(app, client, make_owner):
    headers, firm_id = make_owner()
    with app.app_context():
        uid = _owner_uid()
        for i in range(5):
            _make_case(firm_id, uid, i)  # each case has its own client
        db.session.commit()
    with _QueryCounter(app, 'clients') as qc:
        resp = client.get('/api/v1/case-files', headers=headers)
    assert resp.status_code == 200
    assert len(resp.get_json()) == 5
    assert qc.count == 1


# ---- Opt-in pagination (page_size default 50) ----

def test_drafts_pagination_envelope_and_default_size(app, client, make_owner):
    headers, firm_id = make_owner()
    _seed_drafts(app, firm_id, 60, link_distinct_cases=False)

    page1 = client.get('/api/v1/drafts?page=1', headers=headers).get_json()
    assert page1['total'] == 60
    assert page1['page'] == 1
    assert page1['page_size'] == 50      # default kept at 50
    assert page1['total_pages'] == 2
    assert len(page1['data']) == 50

    page2 = client.get('/api/v1/drafts?page=2', headers=headers).get_json()
    assert len(page2['data']) == 10


def test_list_without_page_returns_plain_array(app, client, make_owner):
    """Backwards-compat: no ?page => legacy bare array (Kanban/calendar rely on it)."""
    headers, firm_id = make_owner()
    _seed_drafts(app, firm_id, 3, link_distinct_cases=False)
    body = client.get('/api/v1/drafts', headers=headers).get_json()
    assert isinstance(body, list)
    assert len(body) == 3


def test_case_files_pagination_envelope(app, client, make_owner):
    headers, firm_id = make_owner()
    with app.app_context():
        uid = _owner_uid()
        for i in range(55):
            _make_case(firm_id, uid, i)
        db.session.commit()
    env = client.get('/api/v1/case-files?page=1', headers=headers).get_json()
    assert env['total'] == 55
    assert env['page_size'] == 50
    assert len(env['data']) == 50
    assert env['total_pages'] == 2
