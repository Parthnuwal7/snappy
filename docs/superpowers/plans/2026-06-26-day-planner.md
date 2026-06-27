# Day Planner Implementation Plan (Sub-project B)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Tasks (day/week/month) + a Day/Week/Month planner inside the Calendar subtab + one-click printable cause-list.

**Architecture:** A firm-scoped `Task` model (due-date, optional case link, done, priority) with a `tasks` RBAC module and CRUD API. The Calendar page gains a Day/Week/Month toggle; Day view composes hearings (existing `/calendar`) + tasks (`/tasks`). A bare `/print/cause-list` route renders the day's cause-list outside the app shell and auto-prints.

**Tech Stack:** Flask + SQLAlchemy (SQLite tests), pytest; React + TS + Vite, React Router v6, TanStack Query, Tailwind.

## Global Constraints

- Never run git commits/pushes — Parth does git. Stage only; report.
- Migration as SQL file for Parth: `018_tasks.sql`. No notifications/digest.
- Tasks gated by the new `tasks` RBAC module. Priority reuses `app.case.stages` PRIORITIES.
- Backend green (`pytest`); frontend builds clean (`npm run build`).

---

### Task 1: `Task` model + `tasks` RBAC + migration 018

**Files:**
- Create: `backend/app/models/task.py`
- Modify: `backend/app/main.py` (model import line)
- Modify: `backend/app/rbac/permissions.py` (module + grants)
- Create: `backend/migrations/018_tasks.sql`
- Test: `backend/tests/test_task_models.py`, `backend/tests/test_task_permissions.py`

**Interfaces:**
- Produces: `Task(firm_id, created_by_user_id, title, due_date, case_file_id?, done, priority, created_at)` + `to_dict()` (incl `case_number`/`case_title` when linked). Permission keys `tasks.create|read|update|delete`.

- [ ] **Step 1: Failing model + permission tests**

`backend/tests/test_task_models.py`:

```python
from datetime import date
from app.models.models import db, Client
from app.models.case import CaseFile
from app.models.task import Task


def _case(app):
    with app.app_context():
        c = Client(firm_id=1, created_by_user_id=1, name='X')
        db.session.add(c); db.session.flush()
        cf = CaseFile(firm_id=1, created_by_user_id=1, case_number='CF/2026/0001', title='Sharma', client_id=c.id)
        db.session.add(cf); db.session.commit()
        return cf.id


def test_task_defaults_and_to_dict(app):
    cf_id = _case(app)
    with app.app_context():
        t = Task(firm_id=1, created_by_user_id=1, title='File reply',
                 due_date=date(2026, 7, 1), case_file_id=cf_id)
        db.session.add(t); db.session.commit()
        d = t.to_dict()
        assert d['title'] == 'File reply'
        assert d['done'] is False
        assert d['priority'] == 'normal'
        assert d['due_date'] == '2026-07-01'
        assert d['case_number'] == 'CF/2026/0001'
        assert d['case_title'] == 'Sharma'


def test_task_without_case(app):
    with app.app_context():
        t = Task(firm_id=1, created_by_user_id=1, title='Call client', due_date=date(2026, 7, 2))
        db.session.add(t); db.session.commit()
        d = t.to_dict()
        assert d['case_file_id'] is None and d['case_number'] is None
```

`backend/tests/test_task_permissions.py`:

```python
from app.rbac.permissions import ALL_PERMISSIONS, DEFAULT_ROLES


def test_tasks_module_present():
    for a in ('create', 'read', 'update', 'delete'):
        assert f'tasks.{a}' in ALL_PERMISSIONS


def test_tasks_granted_to_working_roles():
    assert 'tasks.delete' in DEFAULT_ROLES['Owner']
    for role in ('Partner', 'Associate', 'Staff'):
        assert {'tasks.create', 'tasks.read', 'tasks.update', 'tasks.delete'} <= set(DEFAULT_ROLES[role])
```

- [ ] **Step 2: Run — expect fail**

Run: `cd backend && python -m pytest tests/test_task_models.py tests/test_task_permissions.py -q`
Expected: FAIL (no `Task`, no `tasks` perms).

- [ ] **Step 3: Create the model**

`backend/app/models/task.py`:

```python
"""Task: a firm-scoped, date-scheduled to-do, optionally linked to a case."""
from datetime import datetime
from app.models.models import db


class Task(db.Model):
    __tablename__ = 'tasks'

    id = db.Column(db.Integer, primary_key=True)
    firm_id = db.Column(db.Integer, db.ForeignKey('firms.id'), index=True)
    created_by_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    title = db.Column(db.String(300), nullable=False)
    due_date = db.Column(db.Date, index=True)
    case_file_id = db.Column(db.Integer, db.ForeignKey('case_files.id'))
    done = db.Column(db.Boolean, nullable=False, default=False)
    priority = db.Column(db.String(20), nullable=False, default='normal')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    case_file = db.relationship('CaseFile')

    def to_dict(self):
        return {
            'id': self.id,
            'firm_id': self.firm_id,
            'created_by_user_id': self.created_by_user_id,
            'title': self.title,
            'due_date': self.due_date.isoformat() if self.due_date else None,
            'case_file_id': self.case_file_id,
            'case_number': self.case_file.case_number if self.case_file else None,
            'case_title': self.case_file.title if self.case_file else None,
            'done': self.done,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }
```

- [ ] **Step 4: Register the model**

In `backend/app/main.py`, after the `from app.models.lead import Lead` line, add:

```python
        from app.models.task import Task  # ensure tasks table is created
```

- [ ] **Step 5: Add the RBAC module + grants**

In `backend/app/rbac/permissions.py`:
- In `MODULES`, after the `leads` line add: `{"key": "tasks", "label": "Tasks", "actions": CRUD},`
- In `DEFAULT_ROLES`, append `("tasks", CRUD),` to each of Partner, Associate, and Staff `_perms(...)` calls.

- [ ] **Step 6: Run model+perm tests — expect pass**

Run: `cd backend && python -m pytest tests/test_task_models.py tests/test_task_permissions.py -q`
Expected: PASS.

- [ ] **Step 7: Migration 018**

`backend/migrations/018_tasks.sql`:

```sql
-- 018_tasks.sql — firm-scoped, date-scheduled tasks (day planner).
-- Additive/non-destructive. Apply in the Supabase SQL editor.
BEGIN;

CREATE TABLE IF NOT EXISTS public.tasks (
  id SERIAL PRIMARY KEY,
  firm_id INTEGER REFERENCES public.firms(id),
  created_by_user_id INTEGER REFERENCES public.users(id),
  title VARCHAR(300) NOT NULL,
  due_date DATE,
  case_file_id INTEGER REFERENCES public.case_files(id),
  done BOOLEAN NOT NULL DEFAULT FALSE,
  priority VARCHAR(20) NOT NULL DEFAULT 'normal',
  created_at TIMESTAMP DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS ix_tasks_firm_id ON public.tasks (firm_id);
CREATE INDEX IF NOT EXISTS ix_tasks_due_date ON public.tasks (due_date);

COMMIT;
```

- [ ] **Step 8: Full suite + stage**

Run: `cd backend && python -m pytest -q` → expect PASS (291).
```bash
git add backend/app/models/task.py backend/app/main.py backend/app/rbac/permissions.py backend/migrations/018_tasks.sql backend/tests/test_task_models.py backend/tests/test_task_permissions.py
```

---

### Task 2: Tasks CRUD API

**Files:**
- Create: `backend/app/api/tasks.py`
- Modify: `backend/app/main.py` (import + register blueprint)
- Test: `backend/tests/test_tasks_api.py`

**Interfaces:**
- Produces: blueprint `tasks` — `GET /tasks?from=&to=&status=&case_file_id=`, `POST /tasks`, `PATCH /tasks/<id>`, `DELETE /tasks/<id>`. `status` ∈ {open, done}. Ordered by `due_date, id`.

- [ ] **Step 1: Failing API test**

`backend/tests/test_tasks_api.py`:

```python
def test_task_crud_and_filters(client, make_owner):
    headers, _ = make_owner()
    a = client.post('/api/v1/tasks', headers=headers,
                    json={'title': 'File reply', 'due_date': '2026-07-01', 'priority': 'high'}).get_json()
    assert a['done'] is False and a['priority'] == 'high'
    client.post('/api/v1/tasks', headers=headers, json={'title': 'Call', 'due_date': '2026-07-10'})

    # range filter
    win = client.get('/api/v1/tasks?from=2026-07-01&to=2026-07-05', headers=headers).get_json()
    assert [t['title'] for t in win] == ['File reply']

    # mark done + status filter
    client.patch(f"/api/v1/tasks/{a['id']}", headers=headers, json={'done': True})
    assert len(client.get('/api/v1/tasks?status=open', headers=headers).get_json()) == 1
    assert len(client.get('/api/v1/tasks?status=done', headers=headers).get_json()) == 1

    assert client.delete(f"/api/v1/tasks/{a['id']}", headers=headers).status_code == 200


def test_task_requires_title(client, make_owner):
    headers, _ = make_owner()
    assert client.post('/api/v1/tasks', headers=headers, json={'due_date': '2026-07-01'}).status_code == 400


def test_tasks_firm_isolation(client, make_owner):
    headers, _ = make_owner()
    headers_b, _ = make_owner(supabase_id='sb-b', email='b@firm.com', firm_name='B')
    t = client.post('/api/v1/tasks', headers=headers, json={'title': 'x', 'due_date': '2026-07-01'}).get_json()
    assert client.patch(f"/api/v1/tasks/{t['id']}", headers=headers_b, json={'done': True}).status_code == 404
    assert client.get('/api/v1/tasks', headers=headers_b).get_json() == []
```

- [ ] **Step 2: Run — expect fail (404s)**

Run: `cd backend && python -m pytest tests/test_tasks_api.py -q`

- [ ] **Step 3: Create the blueprint**

`backend/app/api/tasks.py`:

```python
"""Task API — firm-scoped day-planner to-dos. Gated by the tasks RBAC module."""
from datetime import datetime
from flask import Blueprint, request, jsonify, g
from app.models.models import db
from app.models.task import Task
from app.middleware.jwt_auth import jwt_required
from app.middleware.firm_context import require_permission
from app.case.stages import is_valid_priority

bp = Blueprint('tasks', __name__)


def _date(value):
    return datetime.fromisoformat(value).date() if value else None


def _owned(task_id):
    return Task.query.filter_by(id=task_id, firm_id=g.firm_id).first()


@bp.route('/tasks', methods=['GET'])
@jwt_required
@require_permission('tasks.read')
def list_tasks():
    q = Task.query.filter_by(firm_id=g.firm_id)
    frm, to = _date(request.args.get('from')), _date(request.args.get('to'))
    if frm:
        q = q.filter(Task.due_date >= frm)
    if to:
        q = q.filter(Task.due_date <= to)
    status = request.args.get('status')
    if status == 'open':
        q = q.filter(Task.done.is_(False))
    elif status == 'done':
        q = q.filter(Task.done.is_(True))
    case_file_id = request.args.get('case_file_id', type=int)
    if case_file_id:
        q = q.filter_by(case_file_id=case_file_id)
    rows = q.order_by(Task.due_date.asc(), Task.id.asc()).all()
    return jsonify([t.to_dict() for t in rows])


@bp.route('/tasks', methods=['POST'])
@jwt_required
@require_permission('tasks.create')
def create_task():
    data = request.get_json() or {}
    title = (data.get('title') or '').strip()
    if not title:
        return jsonify({'error': 'Title is required'}), 400
    priority = data.get('priority', 'normal')
    if not is_valid_priority(priority):
        return jsonify({'error': 'Invalid priority'}), 400
    task = Task(firm_id=g.firm_id, created_by_user_id=g.user.id, title=title,
                due_date=_date(data.get('due_date')), case_file_id=data.get('case_file_id'),
                priority=priority)
    db.session.add(task)
    db.session.commit()
    return jsonify(task.to_dict()), 201


@bp.route('/tasks/<int:task_id>', methods=['PATCH'])
@jwt_required
@require_permission('tasks.update')
def update_task(task_id):
    task = _owned(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    data = request.get_json() or {}
    if 'title' in data:
        task.title = (data['title'] or '').strip() or task.title
    if 'due_date' in data:
        task.due_date = _date(data['due_date'])
    if 'done' in data:
        task.done = bool(data['done'])
    if 'priority' in data:
        if not is_valid_priority(data['priority']):
            return jsonify({'error': 'Invalid priority'}), 400
        task.priority = data['priority']
    if 'case_file_id' in data:
        task.case_file_id = data['case_file_id']
    db.session.commit()
    return jsonify(task.to_dict())


@bp.route('/tasks/<int:task_id>', methods=['DELETE'])
@jwt_required
@require_permission('tasks.delete')
def delete_task(task_id):
    task = _owned(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404
    db.session.delete(task)
    db.session.commit()
    return jsonify({'message': 'Task deleted'})
```

- [ ] **Step 4: Register**

`backend/app/main.py:12` — append `, tasks` to the `from app.api import ...` line.
After the `calendar` blueprint registration, add: `app.register_blueprint(tasks.bp, url_prefix='/api/v1')`.

- [ ] **Step 5: Run tests + full suite + stage**

Run: `cd backend && python -m pytest tests/test_tasks_api.py -q && python -m pytest -q` → expect PASS (294).
```bash
git add backend/app/api/tasks.py backend/app/main.py backend/tests/test_tasks_api.py
```

---

### Task 3: Frontend — Task API + planner (Day/Week/Month) in Calendar

**Files:**
- Modify: `frontend/src/api.ts` (`Task` type + methods)
- Modify (rewrite): `frontend/src/pages/CaseCalendar.tsx`
- Gate: `npm run build`.

- [ ] **Step 1: `api.ts` — Task type + methods**

Add the interface:

```ts
export interface Task {
  id: number;
  title: string;
  due_date: string | null;
  case_file_id: number | null;
  case_number: string | null;
  case_title: string | null;
  done: boolean;
  priority: string;
  created_at: string | null;
}
```

Add to the `api` object (after `getCalendar`):

```ts
  getTasks: (params?: { from?: string; to?: string; status?: string; case_file_id?: number }) => {
    const q = new URLSearchParams();
    if (params?.from) q.append('from', params.from);
    if (params?.to) q.append('to', params.to);
    if (params?.status) q.append('status', params.status);
    if (params?.case_file_id) q.append('case_file_id', String(params.case_file_id));
    const qs = q.toString();
    return fetchAPI<Task[]>(`${API_BASE_URL}/tasks${qs ? `?${qs}` : ''}`);
  },
  addTask: (data: { title: string; due_date?: string; case_file_id?: number; priority?: string }) =>
    fetchAPI<Task>(`${API_BASE_URL}/tasks`, { method: 'POST', body: JSON.stringify(data) }),
  updateTask: (id: number, data: Partial<Task>) =>
    fetchAPI<Task>(`${API_BASE_URL}/tasks/${id}`, { method: 'PATCH', body: JSON.stringify(data) }),
  deleteTask: (id: number) =>
    fetchAPI<{ message: string }>(`${API_BASE_URL}/tasks/${id}`, { method: 'DELETE' }),
```

- [ ] **Step 2: Rewrite `CaseCalendar.tsx`** with a Day/Week/Month toggle

Replace the entire file with:

```tsx
import { useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, Task } from '../api';
import { useToast } from '../contexts/ToastContext';
import { ChevronLeft, ChevronRight, Plus, Trash2, Printer, Check } from 'lucide-react';

const errMsg = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong');
const iso = (d: Date) => `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
const addDays = (d: Date, n: number) => { const x = new Date(d); x.setDate(x.getDate() + n); return x; };
const startOfWeek = (d: Date) => addDays(d, -((d.getDay() + 6) % 7)); // Monday
const MONTHS = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];
type View = 'day' | 'week' | 'month';

export default function CaseCalendar() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [view, setView] = useState<View>('month');
  const [focus, setFocus] = useState(() => new Date());

  // Visible range by view.
  const [rangeStart, rangeEnd] = useMemo((): [Date, Date] => {
    if (view === 'day') return [focus, focus];
    if (view === 'week') { const s = startOfWeek(focus); return [s, addDays(s, 6)]; }
    return [new Date(focus.getFullYear(), focus.getMonth(), 1), new Date(focus.getFullYear(), focus.getMonth() + 1, 0)];
  }, [view, focus]);

  const from = iso(rangeStart), to = iso(rangeEnd);
  const { data: hearings = [] } = useQuery({ queryKey: ['calendar', from, to], queryFn: () => api.getCalendar(from, to) });
  const { data: tasks = [] } = useQuery({ queryKey: ['tasks', from, to], queryFn: () => api.getTasks({ from, to }) });
  const { data: cases = [] } = useQuery({ queryKey: ['case-files'], queryFn: () => api.getCaseFiles() });

  const invalidateTasks = () => queryClient.invalidateQueries({ queryKey: ['tasks'] });
  const toggleTask = useMutation({ mutationFn: (t: Task) => api.updateTask(t.id, { done: !t.done }), onSuccess: invalidateTasks, onError: (e) => showToast(errMsg(e), 'error') });
  const delTask = useMutation({ mutationFn: (id: number) => api.deleteTask(id), onSuccess: invalidateTasks, onError: (e) => showToast(errMsg(e), 'error') });
  const [tForm, setTForm] = useState({ title: '', case_file_id: '', priority: 'normal' });
  const addTask = useMutation({
    mutationFn: () => api.addTask({ title: tForm.title, due_date: iso(focus), case_file_id: tForm.case_file_id ? Number(tForm.case_file_id) : undefined, priority: tForm.priority }),
    onSuccess: () => { invalidateTasks(); setTForm({ title: '', case_file_id: '', priority: 'normal' }); showToast('Task added'); },
    onError: (e) => showToast(errMsg(e), 'error'),
  });

  const hearingsByDay = useMemo(() => { const m: Record<string, typeof hearings> = {}; hearings.forEach((h) => (m[h.event_date] = m[h.event_date] || []).push(h)); return m; }, [hearings]);
  const tasksByDay = useMemo(() => { const m: Record<string, Task[]> = {}; tasks.forEach((t) => { if (t.due_date) (m[t.due_date] = m[t.due_date] || []).push(t); }); return m; }, [tasks]);

  const shift = (n: number) => setFocus((f) => view === 'day' ? addDays(f, n) : view === 'week' ? addDays(f, n * 7) : new Date(f.getFullYear(), f.getMonth() + n, 1));

  const heading = view === 'month'
    ? `${MONTHS[focus.getMonth()]} ${focus.getFullYear()}`
    : view === 'week'
      ? `Week of ${startOfWeek(focus).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}`
      : focus.toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <h2 className="font-display text-xl text-ink">{heading}</h2>
        <div className="flex items-center gap-3">
          <div className="flex border border-rule rounded-DEFAULT overflow-hidden">
            {(['day', 'week', 'month'] as const).map((v) => (
              <button key={v} onClick={() => setView(v)}
                className={`px-3 py-1.5 text-xs capitalize ${view === v ? 'bg-paper-deep text-ink' : 'text-ink-muted'}`}>{v}</button>
            ))}
          </div>
          <div className="flex gap-1">
            <button onClick={() => shift(-1)} className="btn-ghost p-2"><ChevronLeft size={15} /></button>
            <button onClick={() => setFocus(new Date())} className="btn-ghost text-xs">Today</button>
            <button onClick={() => shift(1)} className="btn-ghost p-2"><ChevronRight size={15} /></button>
          </div>
        </div>
      </div>

      {view === 'month' && <MonthGrid focus={focus} hearingsByDay={hearingsByDay} tasksByDay={tasksByDay} onPick={(d) => { setFocus(d); setView('day'); }} />}
      {view === 'week' && <WeekAgenda start={startOfWeek(focus)} hearingsByDay={hearingsByDay} tasksByDay={tasksByDay} onPick={(d) => { setFocus(d); setView('day'); }} />}
      {view === 'day' && (
        <DayView dateKey={iso(focus)} hearings={hearingsByDay[iso(focus)] ?? []} tasks={tasksByDay[iso(focus)] ?? []}
          cases={cases} tForm={tForm} setTForm={setTForm} addTask={addTask} toggleTask={toggleTask} delTask={delTask} />
      )}
    </div>
  );
}

function MonthGrid({ focus, hearingsByDay, tasksByDay, onPick }: any) {
  const year = focus.getFullYear(), month = focus.getMonth();
  const cells = useMemo(() => {
    const first = new Date(year, month, 1);
    const lead = (first.getDay() + 6) % 7;
    const days = new Date(year, month + 1, 0).getDate();
    const out: (Date | null)[] = [];
    for (let i = 0; i < lead; i++) out.push(null);
    for (let d = 1; d <= days; d++) out.push(new Date(year, month, d));
    while (out.length % 7 !== 0) out.push(null);
    return out;
  }, [year, month]);
  return (
    <div className="grid grid-cols-7 border-l border-t border-rule">
      {['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'].map((d) => (
        <div key={d} className="eyebrow text-center py-1.5 border-r border-b border-rule bg-paper-deep">{d}</div>
      ))}
      {cells.map((d: Date | null, i: number) => {
        const key = d ? iso(d) : `e${i}`;
        const hs = d ? (hearingsByDay[iso(d)] ?? []) : [];
        const ts = d ? (tasksByDay[iso(d)] ?? []) : [];
        return (
          <button key={key} disabled={!d} onClick={() => d && onPick(d)}
            className="min-h-[88px] text-left border-r border-b border-rule p-1.5 bg-surface hover:bg-paper-deep/40 disabled:hover:bg-surface">
            {d && <div className="text-2xs text-ink-faint">{d.getDate()}</div>}
            <div className="space-y-1 mt-1">
              {hs.map((it: any) => <div key={`h${it.event_id}`} className="text-2xs px-1 py-0.5 bg-oxblood-wash text-oxblood rounded-sm truncate">{it.case_title}</div>)}
              {ts.map((t: Task) => <div key={`t${t.id}`} className={`text-2xs px-1 py-0.5 rounded-sm truncate ${t.done ? 'text-ink-faint line-through' : 'text-ink-muted bg-paper-deep'}`}>{t.title}</div>)}
            </div>
          </button>
        );
      })}
    </div>
  );
}

function WeekAgenda({ start, hearingsByDay, tasksByDay, onPick }: any) {
  const days = Array.from({ length: 7 }, (_, i) => addDays(start, i));
  return (
    <div className="space-y-3">
      {days.map((d) => {
        const hs = hearingsByDay[iso(d)] ?? []; const ts = tasksByDay[iso(d)] ?? [];
        return (
          <div key={iso(d)} className="border border-rule">
            <button onClick={() => onPick(d)} className="w-full text-left bg-paper-deep px-4 py-1.5 eyebrow hover:text-oxblood">
              {d.toLocaleDateString('en-IN', { weekday: 'short', day: 'numeric', month: 'short' })}
            </button>
            <div className="divide-y divide-rule">
              {hs.map((it: any) => <div key={`h${it.event_id}`} className="px-4 py-2 text-sm flex gap-3"><span className="text-oxblood text-2xs uppercase tracking-eyebrow w-16">Hearing</span><span className="text-ink">{it.case_title}</span><span className="text-ink-muted text-2xs">{it.purpose}</span></div>)}
              {ts.map((t: Task) => <div key={`t${t.id}`} className="px-4 py-2 text-sm flex gap-3"><span className="text-ink-muted text-2xs uppercase tracking-eyebrow w-16">Task</span><span className={t.done ? 'line-through text-ink-faint' : 'text-ink'}>{t.title}</span></div>)}
              {hs.length === 0 && ts.length === 0 && <div className="px-4 py-2 text-2xs text-ink-faint">—</div>}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function DayView({ dateKey, hearings, tasks, cases, tForm, setTForm, addTask, toggleTask, delTask }: any) {
  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
      <div>
        <div className="flex items-center justify-between mb-3">
          <div className="eyebrow">Hearings</div>
          <a href={`/print/cause-list?date=${dateKey}`} target="_blank" rel="noreferrer" className="btn-ghost text-2xs"><Printer size={13} /> Print cause-list</a>
        </div>
        <div className="border border-rule divide-y divide-rule">
          {hearings.map((h: any) => (
            <Link key={h.event_id} to={`/cases/${h.case_file_id}`} className="bg-surface flex items-center gap-3 px-4 py-2.5 hover:bg-paper-deep/40">
              <span className="text-2xs font-mono text-oxblood w-24 shrink-0">{h.case_number}</span>
              <span className="text-sm text-ink flex-1 truncate">{h.case_title}</span>
              <span className="text-2xs uppercase tracking-eyebrow text-ink-muted">{h.purpose}</span>
            </Link>
          ))}
          {hearings.length === 0 && <div className="bg-surface px-4 py-3 text-sm text-ink-muted">No hearings.</div>}
        </div>
      </div>
      <div>
        <div className="eyebrow mb-3">Tasks</div>
        <form onSubmit={(e) => { e.preventDefault(); if (tForm.title.trim()) addTask.mutate(); }} className="card p-3 mb-3 space-y-2">
          <input value={tForm.title} placeholder="Add a task for this day…" onChange={(e) => setTForm({ ...tForm, title: e.target.value })} className="field-input" />
          <div className="flex gap-2">
            <select value={tForm.case_file_id} onChange={(e) => setTForm({ ...tForm, case_file_id: e.target.value })} className="field-select flex-1">
              <option value="">— No case —</option>
              {cases.map((c: any) => <option key={c.id} value={c.id}>{c.title}</option>)}
            </select>
            <select value={tForm.priority} onChange={(e) => setTForm({ ...tForm, priority: e.target.value })} className="field-select w-28">
              {['low', 'normal', 'high', 'urgent'].map((p) => <option key={p} value={p}>{p}</option>)}
            </select>
            <button type="submit" className="btn-primary" disabled={!tForm.title.trim() || addTask.isPending}><Plus size={14} /></button>
          </div>
        </form>
        <div className="border border-rule divide-y divide-rule">
          {tasks.map((t: Task) => (
            <div key={t.id} className="bg-surface flex items-center gap-3 px-4 py-2.5 group">
              <button onClick={() => toggleTask.mutate(t)} className={`h-4 w-4 rounded-sm border flex items-center justify-center ${t.done ? 'bg-oxblood border-oxblood text-paper' : 'border-rule'}`}>{t.done && <Check size={11} />}</button>
              <span className={`text-sm flex-1 ${t.done ? 'line-through text-ink-faint' : 'text-ink'}`}>{t.title}</span>
              {t.case_title && <span className="text-2xs text-ink-muted truncate max-w-[120px]">{t.case_title}</span>}
              <button onClick={() => delTask.mutate(t.id)} className="p-1 text-ink-muted hover:text-oxblood opacity-0 group-hover:opacity-100"><Trash2 size={13} /></button>
            </div>
          ))}
          {tasks.length === 0 && <div className="bg-surface px-4 py-3 text-sm text-ink-muted">No tasks for this day.</div>}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **Step 3: Build + stage**

Run: `cd frontend && npm run build` → expect clean.
```bash
git add frontend/src/api.ts frontend/src/pages/CaseCalendar.tsx
```

---

### Task 4: Printable cause-list route

**Files:**
- Create: `frontend/src/pages/CauseListPrint.tsx`
- Modify: `frontend/src/App.tsx` (route, outside Layout, under ProtectedRoute)
- Gate: `npm run build`.

- [ ] **Step 1: Create the printable page**

`frontend/src/pages/CauseListPrint.tsx`:

```tsx
import { useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import { api } from '../api';
import { useAuth } from '../contexts/AuthContext';

export default function CauseListPrint() {
  const [params] = useSearchParams();
  const date = params.get('date') || new Date().toISOString().slice(0, 10);
  const { firm } = useAuth();
  const { data: hearings = [], isLoading: lh } = useQuery({ queryKey: ['calendar', date, date], queryFn: () => api.getCalendar(date, date) });
  const { data: tasks = [], isLoading: lt } = useQuery({ queryKey: ['tasks', date, date], queryFn: () => api.getTasks({ from: date, to: date }) });

  useEffect(() => { if (!lh && !lt) { const t = setTimeout(() => window.print(), 400); return () => clearTimeout(t); } }, [lh, lt]);

  const pretty = new Date(date + 'T00:00:00').toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long', year: 'numeric' });

  return (
    <div className="max-w-3xl mx-auto p-10 text-ink bg-white min-h-screen">
      <div className="flex items-center justify-between border-b-2 border-ink pb-3 mb-6">
        <div>
          <div className="font-display text-2xl">{firm?.firm_name || 'Cause list'}</div>
          <div className="text-sm text-ink-muted">Cause list — {pretty}</div>
        </div>
        <button onClick={() => window.print()} className="btn-primary print:hidden">Print</button>
      </div>

      <h2 className="text-sm uppercase tracking-eyebrow text-ink-muted mb-2">Hearings</h2>
      <table className="w-full text-sm mb-8 border-collapse">
        <thead><tr className="border-b border-ink text-left">
          <th className="py-1.5 pr-3 w-28">Case no.</th><th className="py-1.5 pr-3">Title</th><th className="py-1.5 pr-3">Court</th><th className="py-1.5">Purpose</th>
        </tr></thead>
        <tbody>
          {hearings.map((h) => (
            <tr key={h.event_id} className="border-b border-rule">
              <td className="py-1.5 pr-3 font-mono text-xs">{h.case_number}</td>
              <td className="py-1.5 pr-3">{h.case_title}</td>
              <td className="py-1.5 pr-3">{/* court not in calendar payload */}</td>
              <td className="py-1.5">{h.purpose || ''}</td>
            </tr>
          ))}
          {hearings.length === 0 && <tr><td colSpan={4} className="py-3 text-ink-muted">No hearings.</td></tr>}
        </tbody>
      </table>

      <h2 className="text-sm uppercase tracking-eyebrow text-ink-muted mb-2">Tasks</h2>
      <ul className="text-sm space-y-1">
        {tasks.map((t) => <li key={t.id} className="border-b border-rule py-1.5">{t.done ? '☑' : '☐'} {t.title}{t.case_title ? ` — ${t.case_title}` : ''}</li>)}
        {tasks.length === 0 && <li className="py-1.5 text-ink-muted">No tasks.</li>}
      </ul>
    </div>
  );
}
```

> Note: the `/calendar` payload has no `court` field, so the Court column renders blank. If the printout needs court, add `court: cf.court` to the calendar endpoint dict in `app/api/calendar.py` and to `CalendarItem` — a one-line follow-up; left out here to avoid backend churn.

- [ ] **Step 2: Add the route (outside Layout, under ProtectedRoute)**

In `frontend/src/App.tsx`, add the import `import CauseListPrint from './pages/CauseListPrint';`, and add a route **as a sibling of the `/` Layout route** (not nested in it), e.g. right after the `/onboarding` route:

```tsx
          <Route path="/print/cause-list" element={<ProtectedRoute requireOnboarding><CauseListPrint /></ProtectedRoute>} />
```

- [ ] **Step 3: Build + stage**

Run: `cd frontend && npm run build` → expect clean.
```bash
git add frontend/src/pages/CauseListPrint.tsx frontend/src/App.tsx
```

---

## Self-Review

**Spec coverage:** Tasks entity + CRUD + RBAC + migration (Tasks 1–2) ✓ · Day/Week/Month planner in Calendar subtab (Task 3) ✓ · open-a-day shows hearings+tasks (Task 3 DayView) ✓ · one-click printable cause-list (Task 4) ✓ · schedule day/week/month (Task 3 view toggle + per-day add) ✓. No notifications (out of scope) ✓.

**Placeholder scan:** none. The Court-column blank is a documented, intentional minor gap with a one-line fix path.

**Type consistency:** `Task` fields match model `to_dict` ↔ API ↔ FE interface. `getTasks/addTask/updateTask/deleteTask` and `getCalendar` signatures consistent. Priority validated via `is_valid_priority` (low/normal/high/urgent). Print route is a sibling of Layout so it renders chrome-free.
