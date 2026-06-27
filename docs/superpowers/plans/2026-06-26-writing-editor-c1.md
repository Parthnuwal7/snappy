# Writing Editor — Phase C1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans. Steps use checkbox (`- [ ]`).

**Goal:** TipTap editor + Templates + Drafts + load-template-as-draft + merge-fields + PDF export.

**Architecture:** `templates`/`drafts` tables + a `writing` blueprint (CRUD + meta with built-in templates & merge-field catalog). Frontend: TipTap `Editor` component, a Writing page (Templates/Drafts subtabs), full-page Draft/Template editors, and a chrome-free `/print/draft/:id` for PDF.

**Tech Stack:** Flask + SQLAlchemy (SQLite tests), pytest; React 18 + TS + Vite, TanStack Query, TipTap v2, Tailwind.

## Global Constraints

- Never commit/push — Parth does git. Stage only; report.
- Migration `019_writing.sql` for Parth. C2 (AI/DOCX/save-to-vault) out of scope.
- `templates` RBAC: Partner CRUD, Associate/Staff read. `drafts` RBAC: Partner/Associate/Staff CRUD.
- Backend green (`pytest`); frontend builds clean (`npm run build`) after TipTap install.

---

### Task 1: Models + built-in/merge catalogs + RBAC + migration

**Files:**
- Create: `backend/app/models/writing.py`, `backend/app/writing/__init__.py`, `backend/app/writing/builtin.py`, `backend/app/writing/merge.py`
- Modify: `backend/app/main.py` (model import), `backend/app/rbac/permissions.py` (modules + grants)
- Create: `backend/migrations/019_writing.sql`
- Test: `backend/tests/test_writing_models.py`, `backend/tests/test_writing_permissions.py`

**Interfaces:**
- Produces: `Template(firm_id, created_by_user_id, name, category, body, created_at, updated_at)`, `Draft(firm_id, created_by_user_id, title, body, case_file_id?, template_id?, ...)` with `to_dict`. `BUILTIN_TEMPLATES`, `TEMPLATE_CATEGORIES`, `MERGE_FIELDS`. Perms `templates.*`, `drafts.*`.

- [ ] **Step 1: Failing tests**

`backend/tests/test_writing_models.py`:
```python
from app.models.models import db, Client
from app.models.case import CaseFile
from app.models.writing import Template, Draft


def _case(app):
    with app.app_context():
        c = Client(firm_id=1, created_by_user_id=1, name='X'); db.session.add(c); db.session.flush()
        cf = CaseFile(firm_id=1, created_by_user_id=1, case_number='CF/2026/0001', title='Sharma', client_id=c.id)
        db.session.add(cf); db.session.commit()
        return cf.id


def test_template_to_dict(app):
    with app.app_context():
        t = Template(firm_id=1, created_by_user_id=1, name='Notice', category='notice', body='<p>{{court}}</p>')
        db.session.add(t); db.session.commit()
        d = t.to_dict()
        assert d['name'] == 'Notice' and d['category'] == 'notice' and '{{court}}' in d['body']


def test_draft_to_dict_with_case(app):
    cf_id = _case(app)
    with app.app_context():
        dr = Draft(firm_id=1, created_by_user_id=1, title='Reply', body='<p>x</p>', case_file_id=cf_id)
        db.session.add(dr); db.session.commit()
        d = dr.to_dict()
        assert d['title'] == 'Reply' and d['case_number'] == 'CF/2026/0001' and d['case_title'] == 'Sharma'
```

`backend/tests/test_writing_permissions.py`:
```python
from app.rbac.permissions import ALL_PERMISSIONS, DEFAULT_ROLES


def test_writing_modules_present():
    for m in ('templates', 'drafts'):
        for a in ('create', 'read', 'update', 'delete'):
            assert f'{m}.{a}' in ALL_PERMISSIONS


def test_writing_grants():
    assert {'templates.create', 'drafts.delete'} <= set(DEFAULT_ROLES['Owner'])
    assert {'templates.create', 'drafts.create'} <= set(DEFAULT_ROLES['Partner'])
    assert 'templates.read' in DEFAULT_ROLES['Associate'] and 'templates.create' not in DEFAULT_ROLES['Associate']
    assert {'drafts.create', 'drafts.update', 'drafts.delete'} <= set(DEFAULT_ROLES['Staff'])
```

- [ ] **Step 2: Run — expect fail.** `cd backend && python -m pytest tests/test_writing_models.py tests/test_writing_permissions.py -q`

- [ ] **Step 3: Models** — `backend/app/models/writing.py`:
```python
"""Writing module models: reusable Templates and working Drafts (HTML bodies)."""
from datetime import datetime
from app.models.models import db


class Template(db.Model):
    __tablename__ = 'templates'
    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    name = db.Column(db.String(200), nullable=False)
    category = db.Column(db.String(40), default='other')
    body = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {'id': self.id, 'firm_id': self.firm_id, 'created_by_user_id': self.created_by_user_id,
                'name': self.name, 'category': self.category, 'body': self.body,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None}


class Draft(db.Model):
    __tablename__ = 'drafts'
    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    title = db.Column(db.String(300), nullable=False)
    body = db.Column(db.Text)
    case_file_id = db.Column(db.Integer, db.ForeignKey('case_files.id'))
    template_id = db.Column(db.Integer, db.ForeignKey('templates.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    case_file = db.relationship('CaseFile')

    def to_dict(self):
        return {'id': self.id, 'firm_id': self.firm_id, 'created_by_user_id': self.created_by_user_id,
                'title': self.title, 'body': self.body, 'case_file_id': self.case_file_id,
                'case_number': self.case_file.case_number if self.case_file else None,
                'case_title': self.case_file.title if self.case_file else None,
                'template_id': self.template_id,
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None}
```

- [ ] **Step 4: Catalogs** — `backend/app/writing/__init__.py` (empty), `backend/app/writing/merge.py`:
```python
"""Merge-field catalog. `source` is resolved client-side against the linked case."""
MERGE_FIELDS = [
    {"token": "{{petitioner}}", "label": "Petitioner / Plaintiff", "source": "petitioner"},
    {"token": "{{respondent}}", "label": "Respondent / Defendant", "source": "respondent"},
    {"token": "{{court}}",       "label": "Court",                  "source": "court"},
    {"token": "{{case_number}}", "label": "Court case no.",         "source": "court_case_number"},
    {"token": "{{file_number}}", "label": "File no. (CF)",          "source": "case_number"},
    {"token": "{{client}}",      "label": "Client",                 "source": "client_name"},
    {"token": "{{matter}}",      "label": "Matter title",           "source": "title"},
    {"token": "{{date}}",        "label": "Today's date",           "source": "today"},
]
TEMPLATE_CATEGORIES = [
    {"key": "wakalatnama", "label": "Wakalatnama"},
    {"key": "notice",      "label": "Legal notice"},
    {"key": "application", "label": "Application"},
    {"key": "other",       "label": "Other"},
]
```

`backend/app/writing/builtin.py`:
```python
"""Built-in starter templates (mock skeletons) available to every firm."""
BUILTIN_TEMPLATES = [
    {"key": "wakalatnama", "name": "Wakalatnama (starter)", "category": "wakalatnama",
     "body": "<h2 style=\"text-align:center\">WAKALATNAMA</h2>"
             "<p>IN THE COURT OF {{court}}</p>"
             "<p>{{petitioner}} &hellip;Petitioner</p><p>versus</p><p>{{respondent}} &hellip;Respondent</p>"
             "<p>I/We, the above-named {{client}}, do hereby appoint and retain my/our advocate to "
             "appear, act and plead on my/our behalf in the above matter ({{case_number}}).</p>"
             "<p>Dated: {{date}}</p>"},
    {"key": "legal_notice", "name": "Legal notice (starter)", "category": "notice",
     "body": "<p>Date: {{date}}</p><p>To,<br>{{respondent}}</p>"
             "<p><strong>Subject: Legal notice on behalf of {{client}}</strong></p>"
             "<p>Under instructions from and on behalf of my client {{client}}, I hereby serve you "
             "with the following notice in the matter of {{matter}} &hellip;</p>"
             "<p>Yours faithfully,</p><p>Advocate for {{client}}</p>"},
]
```

- [ ] **Step 5: Register the models** — in `backend/app/main.py`, after `from app.models.task import Task`, add:
```python
        from app.models.writing import Template, Draft  # ensure writing tables are created
```

- [ ] **Step 6: RBAC** — in `backend/app/rbac/permissions.py`:
- In `MODULES`, after the `tasks` line add: `{"key": "templates", "label": "Templates", "actions": CRUD},` and `{"key": "drafts", "label": "Drafts", "actions": CRUD},`
- Partner `_perms(...)`: append `("templates", CRUD), ("drafts", CRUD),`
- Associate `_perms(...)`: append `("templates", ["read"]), ("drafts", CRUD),`
- Staff `_perms(...)`: append `("templates", ["read"]), ("drafts", CRUD),`

- [ ] **Step 7: Run model+perm tests — expect pass.**

- [ ] **Step 8: Migration** — `backend/migrations/019_writing.sql`:
```sql
-- 019_writing.sql — Writing module: templates + drafts. Additive. Apply in Supabase.
BEGIN;

CREATE TABLE IF NOT EXISTS public.templates (
  id SERIAL PRIMARY KEY,
  firm_id INTEGER REFERENCES public.firms(id),
  created_by_user_id INTEGER REFERENCES public.users(id),
  name VARCHAR(200) NOT NULL,
  category VARCHAR(40) DEFAULT 'other',
  body TEXT,
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_templates_firm_id ON public.templates (firm_id);

CREATE TABLE IF NOT EXISTS public.drafts (
  id SERIAL PRIMARY KEY,
  firm_id INTEGER REFERENCES public.firms(id),
  created_by_user_id INTEGER REFERENCES public.users(id),
  title VARCHAR(300) NOT NULL,
  body TEXT,
  case_file_id INTEGER REFERENCES public.case_files(id),
  template_id INTEGER REFERENCES public.templates(id),
  created_at TIMESTAMP DEFAULT NOW(),
  updated_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_drafts_firm_id ON public.drafts (firm_id);

COMMIT;
```

- [ ] **Step 9: Full suite + stage.** `cd backend && python -m pytest -q` → expect PASS (302).
```bash
git add backend/app/models/writing.py backend/app/writing/ backend/app/main.py backend/app/rbac/permissions.py backend/migrations/019_writing.sql backend/tests/test_writing_models.py backend/tests/test_writing_permissions.py
```

---

### Task 2: Writing API (templates + drafts + meta)

**Files:**
- Create: `backend/app/api/writing.py`
- Modify: `backend/app/main.py` (import + register)
- Test: `backend/tests/test_writing_api.py`

**Interfaces:**
- Produces: blueprint `writing` — `GET /writing/meta`; `GET/POST /templates`, `GET/PATCH/DELETE /templates/<id>`; `GET/POST /drafts` (`?case_file_id=`), `GET/PATCH/DELETE /drafts/<id>`.

- [ ] **Step 1: Failing test** — `backend/tests/test_writing_api.py`:
```python
def test_writing_meta(client, make_owner):
    headers, _ = make_owner()
    m = client.get('/api/v1/writing/meta', headers=headers).get_json()
    assert any(f['source'] == 'petitioner' for f in m['merge_fields'])
    assert any(t['key'] == 'wakalatnama' for t in m['builtin_templates'])
    assert any(c['key'] == 'notice' for c in m['template_categories'])


def test_template_crud(client, make_owner):
    headers, _ = make_owner()
    t = client.post('/api/v1/templates', headers=headers, json={'name': 'My notice', 'category': 'notice', 'body': '<p>{{court}}</p>'}).get_json()
    assert t['name'] == 'My notice'
    assert len(client.get('/api/v1/templates', headers=headers).get_json()) == 1
    client.patch(f"/api/v1/templates/{t['id']}", headers=headers, json={'name': 'Renamed'})
    assert client.get(f"/api/v1/templates/{t['id']}", headers=headers).get_json()['name'] == 'Renamed'
    assert client.delete(f"/api/v1/templates/{t['id']}", headers=headers).status_code == 200


def test_draft_crud_and_case_filter(client, make_owner):
    headers, firm_id = make_owner()
    from app.models.models import db, Client
    from app.models.auth import User
    with client.application.app_context():
        c = Client(firm_id=firm_id, created_by_user_id=User.query.filter_by(email='owner@firm.com').first().id, name='X')
        db.session.add(c); db.session.commit(); cid = c.id
    case_id = client.post('/api/v1/case-files', headers=headers, json={'title': 'M', 'client_id': cid}).get_json()['id']
    d = client.post('/api/v1/drafts', headers=headers, json={'title': 'Reply', 'body': '<p>hi</p>', 'case_file_id': case_id}).get_json()
    assert d['case_number'].startswith('CF/')
    client.post('/api/v1/drafts', headers=headers, json={'title': 'Unlinked', 'body': '<p>x</p>'})
    assert len(client.get(f'/api/v1/drafts?case_file_id={case_id}', headers=headers).get_json()) == 1
    assert len(client.get('/api/v1/drafts', headers=headers).get_json()) == 2
    client.patch(f"/api/v1/drafts/{d['id']}", headers=headers, json={'body': '<p>edited</p>'})
    assert client.get(f"/api/v1/drafts/{d['id']}", headers=headers).get_json()['body'] == '<p>edited</p>'


def test_writing_firm_isolation(client, make_owner):
    headers, _ = make_owner()
    headers_b, _ = make_owner(supabase_id='sb-b', email='b@firm.com', firm_name='B')
    d = client.post('/api/v1/drafts', headers=headers, json={'title': 'x', 'body': '<p/>'}).get_json()
    assert client.get(f"/api/v1/drafts/{d['id']}", headers=headers_b).status_code == 404
    assert client.get('/api/v1/drafts', headers=headers_b).get_json() == []


def test_draft_requires_title(client, make_owner):
    headers, _ = make_owner()
    assert client.post('/api/v1/drafts', headers=headers, json={'body': '<p/>'}).status_code == 400
```

- [ ] **Step 2: Run — expect fail (404s).**

- [ ] **Step 3: Blueprint** — `backend/app/api/writing.py`:
```python
"""Writing API — templates + drafts + meta. Firm-scoped."""
from flask import Blueprint, request, jsonify, g
from app.models.models import db
from app.models.writing import Template, Draft
from app.middleware.jwt_auth import jwt_required
from app.middleware.firm_context import require_permission
from app.writing.merge import MERGE_FIELDS, TEMPLATE_CATEGORIES
from app.writing.builtin import BUILTIN_TEMPLATES

bp = Blueprint('writing', __name__)


@bp.route('/writing/meta', methods=['GET'])
@jwt_required
@require_permission('drafts.read')
def writing_meta():
    return jsonify({'merge_fields': MERGE_FIELDS, 'template_categories': TEMPLATE_CATEGORIES,
                    'builtin_templates': BUILTIN_TEMPLATES})


# ---- Templates ----
@bp.route('/templates', methods=['GET'])
@jwt_required
@require_permission('templates.read')
def list_templates():
    rows = Template.query.filter_by(firm_id=g.firm_id).order_by(Template.id.desc()).all()
    return jsonify([t.to_dict() for t in rows])


@bp.route('/templates', methods=['POST'])
@jwt_required
@require_permission('templates.create')
def create_template():
    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'Name is required'}), 400
    t = Template(firm_id=g.firm_id, created_by_user_id=g.user.id, name=name,
                 category=data.get('category', 'other'), body=data.get('body', ''))
    db.session.add(t); db.session.commit()
    return jsonify(t.to_dict()), 201


@bp.route('/templates/<int:tid>', methods=['GET'])
@jwt_required
@require_permission('templates.read')
def get_template(tid):
    t = Template.query.filter_by(id=tid, firm_id=g.firm_id).first()
    return (jsonify(t.to_dict()) if t else (jsonify({'error': 'Not found'}), 404))


@bp.route('/templates/<int:tid>', methods=['PATCH'])
@jwt_required
@require_permission('templates.update')
def update_template(tid):
    t = Template.query.filter_by(id=tid, firm_id=g.firm_id).first()
    if not t:
        return jsonify({'error': 'Not found'}), 404
    data = request.get_json() or {}
    for f in ('name', 'category', 'body'):
        if f in data:
            setattr(t, f, data[f])
    db.session.commit()
    return jsonify(t.to_dict())


@bp.route('/templates/<int:tid>', methods=['DELETE'])
@jwt_required
@require_permission('templates.delete')
def delete_template(tid):
    t = Template.query.filter_by(id=tid, firm_id=g.firm_id).first()
    if not t:
        return jsonify({'error': 'Not found'}), 404
    db.session.delete(t); db.session.commit()
    return jsonify({'message': 'Template deleted'})


# ---- Drafts ----
@bp.route('/drafts', methods=['GET'])
@jwt_required
@require_permission('drafts.read')
def list_drafts():
    q = Draft.query.filter_by(firm_id=g.firm_id)
    case_file_id = request.args.get('case_file_id', type=int)
    if case_file_id:
        q = q.filter_by(case_file_id=case_file_id)
    return jsonify([d.to_dict() for d in q.order_by(Draft.id.desc()).all()])


@bp.route('/drafts', methods=['POST'])
@jwt_required
@require_permission('drafts.create')
def create_draft():
    data = request.get_json() or {}
    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({'error': 'Title is required'}), 400
    d = Draft(firm_id=g.firm_id, created_by_user_id=g.user.id, title=title,
              body=data.get('body', ''), case_file_id=data.get('case_file_id'),
              template_id=data.get('template_id'))
    db.session.add(d); db.session.commit()
    return jsonify(d.to_dict()), 201


@bp.route('/drafts/<int:did>', methods=['GET'])
@jwt_required
@require_permission('drafts.read')
def get_draft(did):
    d = Draft.query.filter_by(id=did, firm_id=g.firm_id).first()
    return (jsonify(d.to_dict()) if d else (jsonify({'error': 'Not found'}), 404))


@bp.route('/drafts/<int:did>', methods=['PATCH'])
@jwt_required
@require_permission('drafts.update')
def update_draft(did):
    d = Draft.query.filter_by(id=did, firm_id=g.firm_id).first()
    if not d:
        return jsonify({'error': 'Not found'}), 404
    data = request.get_json() or {}
    for f in ('title', 'body', 'case_file_id'):
        if f in data:
            setattr(d, f, data[f])
    db.session.commit()
    return jsonify(d.to_dict())


@bp.route('/drafts/<int:did>', methods=['DELETE'])
@jwt_required
@require_permission('drafts.delete')
def delete_draft(did):
    d = Draft.query.filter_by(id=did, firm_id=g.firm_id).first()
    if not d:
        return jsonify({'error': 'Not found'}), 404
    db.session.delete(d); db.session.commit()
    return jsonify({'message': 'Draft deleted'})
```

- [ ] **Step 4: Register** — `main.py:12` append `, writing`; after `tasks` blueprint add `app.register_blueprint(writing.bp, url_prefix='/api/v1')`.

- [ ] **Step 5: Run tests + full suite + stage.** Expect PASS (307).
```bash
git add backend/app/api/writing.py backend/app/main.py backend/tests/test_writing_api.py
```

---

### Task 3: Frontend — install TipTap + `Editor` component

**Files:**
- Modify: `frontend/package.json` (deps via install)
- Create: `frontend/src/components/Editor.tsx`

- [ ] **Step 1: Install TipTap**

Run: `cd frontend && npm install @tiptap/react@^2 @tiptap/pm@^2 @tiptap/starter-kit@^2 @tiptap/extension-underline@^2 @tiptap/extension-link@^2 @tiptap/extension-text-align@^2 @tiptap/extension-highlight@^2 @tiptap/extension-table@^2 @tiptap/extension-table-row@^2 @tiptap/extension-table-cell@^2 @tiptap/extension-table-header@^2`
Expected: installs cleanly.

- [ ] **Step 2: Create `Editor.tsx`**

```tsx
import { useEffect } from 'react';
import { useEditor, EditorContent } from '@tiptap/react';
import StarterKit from '@tiptap/starter-kit';
import Underline from '@tiptap/extension-underline';
import Link from '@tiptap/extension-link';
import TextAlign from '@tiptap/extension-text-align';
import Highlight from '@tiptap/extension-highlight';
import Table from '@tiptap/extension-table';
import TableRow from '@tiptap/extension-table-row';
import TableCell from '@tiptap/extension-table-cell';
import TableHeader from '@tiptap/extension-table-header';
import {
  Bold, Italic, Underline as U, List, ListOrdered, Heading1, Heading2,
  AlignLeft, AlignCenter, AlignRight, Link as LinkIcon, Highlighter, Table as TableIcon,
} from 'lucide-react';

interface MergeField { token: string; label: string; source: string }

export default function Editor({ content, onChange, mergeFields = [], onInsertField }: {
  content: string;
  onChange: (html: string) => void;
  mergeFields?: MergeField[];
  onInsertField?: (insert: (token: string) => void) => void;
}) {
  const editor = useEditor({
    extensions: [
      StarterKit, Underline, Highlight,
      Link.configure({ openOnClick: false }),
      TextAlign.configure({ types: ['heading', 'paragraph'] }),
      Table.configure({ resizable: true }), TableRow, TableCell, TableHeader,
    ],
    content,
    onUpdate: ({ editor }) => onChange(editor.getHTML()),
  });

  // Keep external content in sync when it changes from outside (e.g. fill-from-case).
  useEffect(() => {
    if (editor && content !== editor.getHTML()) editor.commands.setContent(content, false);
  }, [content]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (editor && onInsertField) onInsertField((token: string) => editor.chain().focus().insertContent(token).run());
  }, [editor, onInsertField]);

  if (!editor) return null;
  const btn = (active: boolean) => `p-1.5 rounded-sm ${active ? 'bg-oxblood-wash text-oxblood' : 'text-ink-muted hover:text-ink'}`;

  return (
    <div className="border border-rule rounded-DEFAULT bg-surface">
      <div className="flex flex-wrap items-center gap-0.5 border-b border-rule p-1.5">
        <button onClick={() => editor.chain().focus().toggleHeading({ level: 1 }).run()} className={btn(editor.isActive('heading', { level: 1 }))}><Heading1 size={15} /></button>
        <button onClick={() => editor.chain().focus().toggleHeading({ level: 2 }).run()} className={btn(editor.isActive('heading', { level: 2 }))}><Heading2 size={15} /></button>
        <span className="w-px h-4 bg-rule mx-1" />
        <button onClick={() => editor.chain().focus().toggleBold().run()} className={btn(editor.isActive('bold'))}><Bold size={15} /></button>
        <button onClick={() => editor.chain().focus().toggleItalic().run()} className={btn(editor.isActive('italic'))}><Italic size={15} /></button>
        <button onClick={() => editor.chain().focus().toggleUnderline().run()} className={btn(editor.isActive('underline'))}><U size={15} /></button>
        <button onClick={() => editor.chain().focus().toggleHighlight().run()} className={btn(editor.isActive('highlight'))}><Highlighter size={15} /></button>
        <span className="w-px h-4 bg-rule mx-1" />
        <button onClick={() => editor.chain().focus().toggleBulletList().run()} className={btn(editor.isActive('bulletList'))}><List size={15} /></button>
        <button onClick={() => editor.chain().focus().toggleOrderedList().run()} className={btn(editor.isActive('orderedList'))}><ListOrdered size={15} /></button>
        <span className="w-px h-4 bg-rule mx-1" />
        <button onClick={() => editor.chain().focus().setTextAlign('left').run()} className={btn(editor.isActive({ textAlign: 'left' }))}><AlignLeft size={15} /></button>
        <button onClick={() => editor.chain().focus().setTextAlign('center').run()} className={btn(editor.isActive({ textAlign: 'center' }))}><AlignCenter size={15} /></button>
        <button onClick={() => editor.chain().focus().setTextAlign('right').run()} className={btn(editor.isActive({ textAlign: 'right' }))}><AlignRight size={15} /></button>
        <span className="w-px h-4 bg-rule mx-1" />
        <button onClick={() => { const url = prompt('Link URL'); if (url) editor.chain().focus().setLink({ href: url }).run(); }} className={btn(editor.isActive('link'))}><LinkIcon size={15} /></button>
        <button onClick={() => editor.chain().focus().insertTable({ rows: 3, cols: 3, withHeaderRow: true }).run()} className={btn(false)}><TableIcon size={15} /></button>
        {mergeFields.length > 0 && (
          <select onChange={(e) => { if (e.target.value) { editor.chain().focus().insertContent(e.target.value).run(); e.target.value = ''; } }}
            className="ml-2 text-xs border border-rule rounded-sm px-1.5 py-1 text-ink-muted bg-surface">
            <option value="">Insert field…</option>
            {mergeFields.map((f) => <option key={f.token} value={f.token}>{f.label}</option>)}
          </select>
        )}
      </div>
      <EditorContent editor={editor} className="prose prose-sm max-w-none p-5 min-h-[420px] focus:outline-none [&_.ProseMirror]:outline-none [&_.ProseMirror]:min-h-[400px] [&_table]:border-collapse [&_td]:border [&_td]:border-rule [&_td]:p-1 [&_th]:border [&_th]:border-rule [&_th]:p-1 [&_th]:bg-paper-deep" />
    </div>
  );
}
```

- [ ] **Step 3: Build + stage.** `cd frontend && npm run build` → expect clean.
```bash
git add frontend/package.json frontend/package-lock.json frontend/src/components/Editor.tsx
```

---

### Task 4: Frontend — `api.ts` + Writing page (lists) + routes

**Files:**
- Modify: `frontend/src/api.ts`, `frontend/src/pages/Writing.tsx`, `frontend/src/App.tsx`

- [ ] **Step 1: `api.ts` types + methods**
```ts
export interface Template { id: number; name: string; category: string; body: string; created_at: string | null; updated_at: string | null }
export interface Draft { id: number; title: string; body: string; case_file_id: number | null; case_number: string | null; case_title: string | null; template_id: number | null; created_at: string | null; updated_at: string | null }
export interface MergeField { token: string; label: string; source: string }
export interface WritingMeta { merge_fields: MergeField[]; template_categories: { key: string; label: string }[]; builtin_templates: { key: string; name: string; category: string; body: string }[] }
```
Add to `api`:
```ts
  getWritingMeta: () => fetchAPI<WritingMeta>(`${API_BASE_URL}/writing/meta`),
  getTemplates: () => fetchAPI<Template[]>(`${API_BASE_URL}/templates`),
  getTemplate: (id: number) => fetchAPI<Template>(`${API_BASE_URL}/templates/${id}`),
  createTemplate: (d: Partial<Template>) => fetchAPI<Template>(`${API_BASE_URL}/templates`, { method: 'POST', body: JSON.stringify(d) }),
  updateTemplate: (id: number, d: Partial<Template>) => fetchAPI<Template>(`${API_BASE_URL}/templates/${id}`, { method: 'PATCH', body: JSON.stringify(d) }),
  deleteTemplate: (id: number) => fetchAPI<{ message: string }>(`${API_BASE_URL}/templates/${id}`, { method: 'DELETE' }),
  getDrafts: (caseFileId?: number) => fetchAPI<Draft[]>(`${API_BASE_URL}/drafts${caseFileId ? `?case_file_id=${caseFileId}` : ''}`),
  getDraft: (id: number) => fetchAPI<Draft>(`${API_BASE_URL}/drafts/${id}`),
  createDraft: (d: Partial<Draft>) => fetchAPI<Draft>(`${API_BASE_URL}/drafts`, { method: 'POST', body: JSON.stringify(d) }),
  updateDraft: (id: number, d: Partial<Draft>) => fetchAPI<Draft>(`${API_BASE_URL}/drafts/${id}`, { method: 'PATCH', body: JSON.stringify(d) }),
  deleteDraft: (id: number) => fetchAPI<{ message: string }>(`${API_BASE_URL}/drafts/${id}`, { method: 'DELETE' }),
```

- [ ] **Step 2: Rewrite `pages/Writing.tsx`** (Templates/Drafts subtabs + lists + new-from-template)
```tsx
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';
import { usePermissions } from '../hooks/usePermissions';
import { Plus, FileText, Trash2 } from 'lucide-react';

export default function Writing() {
  const nav = useNavigate();
  const qc = useQueryClient();
  const { has } = usePermissions();
  const [tab, setTab] = useState<'drafts' | 'templates'>('drafts');
  const { data: drafts = [] } = useQuery({ queryKey: ['drafts'], queryFn: () => api.getDrafts() });
  const { data: templates = [] } = useQuery({ queryKey: ['templates'], queryFn: () => api.getTemplates() });
  const { data: meta } = useQuery({ queryKey: ['writing-meta'], queryFn: api.getWritingMeta });

  const newFromTemplate = useMutation({
    mutationFn: (body: string) => api.createDraft({ title: 'Untitled draft', body }),
    onSuccess: (d) => { qc.invalidateQueries({ queryKey: ['drafts'] }); nav(`/writing/draft/${d.id}`); },
  });
  const delDraft = useMutation({ mutationFn: (id: number) => api.deleteDraft(id), onSuccess: () => qc.invalidateQueries({ queryKey: ['drafts'] }) });
  const delTemplate = useMutation({ mutationFn: (id: number) => api.deleteTemplate(id), onSuccess: () => qc.invalidateQueries({ queryKey: ['templates'] }) });

  const canTemplates = has('templates.create');

  return (
    <div className="max-w-page mx-auto px-8 lg:px-12 py-10">
      <header className="mb-6"><div className="page-eyebrow">Folio VI · Writing</div><h1 className="page-title">Drafting</h1></header>
      <nav className="flex gap-6 border-b border-rule mb-8">
        {(['drafts', 'templates'] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)} className={`px-1 pb-2 -mb-px text-sm font-medium border-b-2 capitalize ${tab === t ? 'border-oxblood text-ink' : 'border-transparent text-ink-muted hover:text-ink'}`}>{t}</button>
        ))}
      </nav>

      {tab === 'drafts' && (
        <div className="space-y-4">
          <div className="flex items-center gap-3">
            <button onClick={() => newFromTemplate.mutate('<p></p>')} className="btn-primary"><Plus size={14} /> New draft</button>
            <select onChange={(e) => { if (e.target.value) newFromTemplate.mutate(e.target.value); e.target.value = ''; }} className="field-select w-64">
              <option value="">New from template…</option>
              {(meta?.builtin_templates ?? []).map((t) => <option key={t.key} value={t.body}>{t.name}</option>)}
              {templates.map((t) => <option key={t.id} value={t.body}>{t.name}</option>)}
            </select>
          </div>
          <div className="border border-rule divide-y divide-rule">
            {drafts.map((d) => (
              <div key={d.id} className="bg-surface flex items-center gap-3 px-5 py-3 group">
                <FileText size={14} className="text-ink-faint" />
                <button onClick={() => nav(`/writing/draft/${d.id}`)} className="text-sm text-ink flex-1 text-left hover:text-oxblood truncate">{d.title}</button>
                {d.case_number && <span className="text-2xs font-mono text-ink-muted">{d.case_number}</span>}
                <button onClick={() => delDraft.mutate(d.id)} className="p-1 text-ink-muted hover:text-oxblood opacity-0 group-hover:opacity-100"><Trash2 size={13} /></button>
              </div>
            ))}
            {drafts.length === 0 && <div className="bg-surface px-5 py-10 text-center text-sm text-ink-muted">No drafts yet.</div>}
          </div>
        </div>
      )}

      {tab === 'templates' && (
        <div className="space-y-4">
          {canTemplates && <button onClick={() => nav('/writing/template/new')} className="btn-primary"><Plus size={14} /> New template</button>}
          <div className="border border-rule divide-y divide-rule">
            {templates.map((t) => (
              <div key={t.id} className="bg-surface flex items-center gap-3 px-5 py-3 group">
                <button onClick={() => nav(`/writing/template/${t.id}`)} className="text-sm text-ink flex-1 text-left hover:text-oxblood truncate">{t.name}</button>
                <span className="text-2xs uppercase tracking-eyebrow text-ink-muted">{t.category}</span>
                {canTemplates && <button onClick={() => delTemplate.mutate(t.id)} className="p-1 text-ink-muted hover:text-oxblood opacity-0 group-hover:opacity-100"><Trash2 size={13} /></button>}
              </div>
            ))}
            {templates.length === 0 && <div className="bg-surface px-5 py-10 text-center text-sm text-ink-muted">No firm templates. Built-in starters are available when creating a draft.</div>}
          </div>
        </div>
      )}
    </div>
  );
}
```

- [ ] **Step 3: Routes in `App.tsx`** — add imports `DraftEditor`, `TemplateEditor` (Task 5) and routes inside the Layout block:
```tsx
            <Route path="writing/draft/:id" element={<DraftEditor />} />
            <Route path="writing/template/:id" element={<TemplateEditor />} />
```
and a chrome-free sibling (outside Layout, like the cause-list): `<Route path="/print/draft/:id" element={<ProtectedRoute requireOnboarding><DraftPrint /></ProtectedRoute>} />` (also Task 5).

- [ ] **Step 4: Build + stage** (will fail to build until Task 5 files exist — do Task 5 then build).

---

### Task 5: Frontend — Draft editor, Template editor, print route

**Files:**
- Create: `frontend/src/pages/DraftEditor.tsx`, `frontend/src/pages/TemplateEditor.tsx`, `frontend/src/pages/DraftPrint.tsx`
- Modify: `frontend/src/App.tsx` (imports)

- [ ] **Step 1: `DraftEditor.tsx`** (title, case link, editor, fill-from-case, save, export PDF)
```tsx
import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, CaseFile } from '../api';
import { useToast } from '../contexts/ToastContext';
import Editor from '../components/Editor';
import { ArrowLeft, Save, Printer, Wand2 } from 'lucide-react';

const errMsg = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong');

function resolveField(source: string, c?: CaseFile): string {
  if (!c) return '';
  const party = (re: RegExp) => (c.parties?.find((p) => re.test(p.role || ''))?.name) || '';
  switch (source) {
    case 'petitioner': return party(/petition|plaintiff|appellant|applicant/i);
    case 'respondent': return party(/respond|defendant/i);
    case 'court': return c.court || '';
    case 'court_case_number': return c.court_case_number || '';
    case 'case_number': return c.case_number || '';
    case 'client_name': return c.client_name || '';
    case 'title': return c.title || '';
    case 'today': return new Date().toLocaleDateString('en-IN', { day: 'numeric', month: 'long', year: 'numeric' });
    default: return '';
  }
}

export default function DraftEditor() {
  const { id } = useParams();
  const draftId = Number(id);
  const nav = useNavigate();
  const qc = useQueryClient();
  const { showToast } = useToast();
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [caseId, setCaseId] = useState<number | ''>('');

  const { data: draft } = useQuery({ queryKey: ['draft', draftId], queryFn: () => api.getDraft(draftId), enabled: !!draftId });
  const { data: meta } = useQuery({ queryKey: ['writing-meta'], queryFn: api.getWritingMeta });
  const { data: cases = [] } = useQuery({ queryKey: ['case-files'], queryFn: () => api.getCaseFiles() });
  const { data: linkedCase } = useQuery({ queryKey: ['case-file', caseId], queryFn: () => api.getCaseFile(Number(caseId)), enabled: !!caseId });

  useEffect(() => { if (draft) { setTitle(draft.title); setBody(draft.body); setCaseId(draft.case_file_id ?? ''); } }, [draft]);

  const save = useMutation({
    mutationFn: () => api.updateDraft(draftId, { title, body, case_file_id: caseId ? Number(caseId) : null }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['drafts'] }); qc.invalidateQueries({ queryKey: ['draft', draftId] }); showToast('Draft saved'); },
    onError: (e) => showToast(errMsg(e), 'error'),
  });

  const fillFromCase = () => {
    if (!linkedCase || !meta) { showToast('Link a case first', 'error'); return; }
    let filled = body;
    meta.merge_fields.forEach((f) => { filled = filled.split(f.token).join(resolveField(f.source, linkedCase)); });
    setBody(filled);
    showToast('Merge fields filled');
  };

  const exportPdf = async () => { await save.mutateAsync(); window.open(`/print/draft/${draftId}`, '_blank'); };

  return (
    <div className="max-w-4xl mx-auto px-8 py-8">
      <Link to="/writing" className="inline-flex items-center gap-1.5 text-xs text-ink-muted hover:text-oxblood mb-5"><ArrowLeft size={13} /> Back to writing</Link>
      <div className="flex items-center gap-3 mb-4 flex-wrap">
        <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Draft title" className="field-input flex-1 min-w-[200px] !text-lg font-medium" />
        <select value={caseId} onChange={(e) => setCaseId(e.target.value ? Number(e.target.value) : '')} className="field-select w-56">
          <option value="">— Link a case —</option>
          {cases.map((c) => <option key={c.id} value={c.id}>{c.case_number} · {c.title}</option>)}
        </select>
        <button onClick={fillFromCase} disabled={!caseId} className="btn-ghost disabled:opacity-40"><Wand2 size={14} /> Fill from case</button>
        <button onClick={exportPdf} className="btn-ghost"><Printer size={14} /> Export PDF</button>
        <button onClick={() => save.mutate()} className="btn-primary" disabled={save.isPending}><Save size={14} /> Save</button>
      </div>
      <Editor content={body} onChange={setBody} mergeFields={meta?.merge_fields ?? []} />
    </div>
  );
}
```

- [ ] **Step 2: `TemplateEditor.tsx`**
```tsx
import { useEffect, useState } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';
import { useToast } from '../contexts/ToastContext';
import Editor from '../components/Editor';
import { ArrowLeft, Save } from 'lucide-react';

const errMsg = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong');

export default function TemplateEditor() {
  const { id } = useParams();
  const isNew = id === 'new';
  const tid = Number(id);
  const nav = useNavigate();
  const qc = useQueryClient();
  const { showToast } = useToast();
  const [name, setName] = useState('');
  const [category, setCategory] = useState('other');
  const [body, setBody] = useState('');

  const { data: tpl } = useQuery({ queryKey: ['template', tid], queryFn: () => api.getTemplate(tid), enabled: !isNew && !!tid });
  const { data: meta } = useQuery({ queryKey: ['writing-meta'], queryFn: api.getWritingMeta });
  useEffect(() => { if (tpl) { setName(tpl.name); setCategory(tpl.category); setBody(tpl.body); } }, [tpl]);

  const save = useMutation({
    mutationFn: () => isNew ? api.createTemplate({ name, category, body }) : api.updateTemplate(tid, { name, category, body }),
    onSuccess: (t) => { qc.invalidateQueries({ queryKey: ['templates'] }); showToast('Template saved'); if (isNew) nav(`/writing/template/${t.id}`); },
    onError: (e) => showToast(errMsg(e), 'error'),
  });

  return (
    <div className="max-w-4xl mx-auto px-8 py-8">
      <Link to="/writing" className="inline-flex items-center gap-1.5 text-xs text-ink-muted hover:text-oxblood mb-5"><ArrowLeft size={13} /> Back to writing</Link>
      <div className="flex items-center gap-3 mb-4 flex-wrap">
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Template name" className="field-input flex-1 min-w-[200px] !text-lg font-medium" />
        <select value={category} onChange={(e) => setCategory(e.target.value)} className="field-select w-48">
          {(meta?.template_categories ?? [{ key: 'other', label: 'Other' }]).map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
        </select>
        <button onClick={() => save.mutate()} className="btn-primary" disabled={!name.trim() || save.isPending}><Save size={14} /> Save</button>
      </div>
      <Editor content={body} onChange={setBody} mergeFields={meta?.merge_fields ?? []} />
    </div>
  );
}
```

- [ ] **Step 3: `DraftPrint.tsx`** (chrome-free, auto-print)
```tsx
import { useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api';

export default function DraftPrint() {
  const { id } = useParams();
  const { data: draft, isLoading } = useQuery({ queryKey: ['draft', Number(id)], queryFn: () => api.getDraft(Number(id)), enabled: !!id });
  useEffect(() => { if (!isLoading && draft) { const t = setTimeout(() => window.print(), 400); return () => clearTimeout(t); } }, [isLoading, draft]);
  if (!draft) return null;
  return (
    <div className="max-w-3xl mx-auto p-12 bg-white text-ink min-h-screen">
      <button onClick={() => window.print()} className="btn-primary print:hidden mb-6">Print</button>
      <h1 className="text-xl font-display mb-6">{draft.title}</h1>
      <div className="prose prose-sm max-w-none [&_table]:border-collapse [&_td]:border [&_td]:border-ink/30 [&_td]:p-1 [&_th]:border [&_th]:border-ink/30 [&_th]:p-1" dangerouslySetInnerHTML={{ __html: draft.body }} />
    </div>
  );
}
```

- [ ] **Step 4: Wire imports in `App.tsx`**

Add: `import DraftEditor from './pages/DraftEditor';`, `import TemplateEditor from './pages/TemplateEditor';`, `import DraftPrint from './pages/DraftPrint';`. (Routes were added in Task 4 Step 3.)

- [ ] **Step 5: Build + stage.** `cd frontend && npm run build` → expect clean.
```bash
git add frontend/src/pages/DraftEditor.tsx frontend/src/pages/TemplateEditor.tsx frontend/src/pages/DraftPrint.tsx frontend/src/App.tsx
```

---

## Self-Review

**Spec coverage:** TipTap editor + toolbar (Task 3) ✓ · Templates + Drafts CRUD + migration + RBAC (Tasks 1–2) ✓ · load-template-as-draft (Task 4 new-from-template) ✓ · merge-fields insert + fill-from-case (Tasks 3,5) ✓ · PDF export via print route (Task 5) ✓ · Writing IA (Templates/Drafts subtabs) (Task 4) ✓. AI/DOCX/save-to-vault = C2 (out of scope) ✓.

**Placeholder scan:** none. Built-in templates are real starter HTML.

**Type consistency:** `Template`/`Draft`/`MergeField`/`WritingMeta` match backend `to_dict`/meta. `Editor` props (`content`/`onChange`/`mergeFields`) consistent across both editor pages. Draft body is HTML round-tripped through TipTap `getHTML`/`setContent`. Print route is a Layout sibling (chrome-free), like `/print/cause-list`.
