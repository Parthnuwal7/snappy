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

  useEffect(() => {
    if (!lh && !lt) { const t = setTimeout(() => window.print(), 400); return () => clearTimeout(t); }
  }, [lh, lt]);

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
              <td className="py-1.5 pr-3">{h.court || ''}</td>
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
