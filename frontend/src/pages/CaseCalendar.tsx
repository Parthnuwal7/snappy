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

  const hearingsByDay = useMemo(() => { const m: Record<string, typeof hearings> = {}; hearings.forEach((h) => { (m[h.event_date] = m[h.event_date] || []).push(h); }); return m; }, [hearings]);
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
          <div className="flex gap-1 items-center">
            <button onClick={() => shift(-1)} className="btn-ghost p-2"><ChevronLeft size={15} /></button>
            <button onClick={() => setFocus(new Date())} className="btn-ghost text-xs">Today</button>
            <button onClick={() => shift(1)} className="btn-ghost p-2"><ChevronRight size={15} /></button>
          </div>
        </div>
      </div>

      {view === 'month' && <MonthGrid focus={focus} hearingsByDay={hearingsByDay} tasksByDay={tasksByDay} onPick={(d: Date) => { setFocus(d); setView('day'); }} />}
      {view === 'week' && <WeekAgenda start={startOfWeek(focus)} hearingsByDay={hearingsByDay} tasksByDay={tasksByDay} onPick={(d: Date) => { setFocus(d); setView('day'); }} />}
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
