import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { api, Client, RecurringSchedule } from '../api';
import { ArrowLeft, Plus, Trash2, Pause, Play } from 'lucide-react';

const formatINR = (v: number) =>
  '₹' + v.toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 });

const lineTotal = (items: RecurringSchedule['items']) =>
  items.reduce((s, i) => s + (Number(i.quantity) || 0) * (Number(i.rate) || 0), 0);

export default function Recurring() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [showForm, setShowForm] = useState(false);
  const [clientId, setClientId] = useState<number | 0>(0);
  const [frequency, setFrequency] = useState<'weekly' | 'monthly'>('monthly');
  const [startDate, setStartDate] = useState(new Date().toISOString().split('T')[0]);
  const [endDate, setEndDate] = useState('');
  const [shortDesc, setShortDesc] = useState('');
  const [items, setItems] = useState([{ description: '', quantity: 1, rate: 0 }]);

  const { data: schedules } = useQuery({
    queryKey: ['recurring'],
    queryFn: () => api.getRecurring(),
  });
  const { data: clients } = useQuery({
    queryKey: ['clients'],
    queryFn: () => api.getClients(),
  });

  const createMutation = useMutation({
    mutationFn: () => api.createRecurring({
      client_id: clientId as number,
      frequency,
      start_date: startDate,
      end_date: endDate || undefined,
      short_desc: shortDesc,
      items,
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['recurring'] });
      setShowForm(false);
      setItems([{ description: '', quantity: 1, rate: 0 }]);
      setClientId(0); setShortDesc(''); setEndDate('');
    },
  });

  const toggleMutation = useMutation({
    mutationFn: (s: RecurringSchedule) => api.updateRecurring(s.id, { active: !s.active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['recurring'] }),
  });
  const deleteMutation = useMutation({
    mutationFn: (id: number) => api.deleteRecurring(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['recurring'] }),
  });

  const canSave = clientId !== 0 && items.some((i) => i.description && i.rate > 0);

  return (
    <div className="max-w-page mx-auto px-8 lg:px-12 py-10">
      <button onClick={() => navigate('/invoices')}
              className="inline-flex items-center gap-1.5 text-sm text-ink-muted hover:text-oxblood mb-3">
        <ArrowLeft size={14} strokeWidth={2} /><span>Back to invoices</span>
      </button>

      <header className="flex items-end justify-between flex-wrap gap-6 mb-8">
        <div>
          <div className="page-eyebrow">Automation</div>
          <h1 className="page-title">Recurring invoices</h1>
          <p className="page-subtitle">Auto-create a draft on a schedule. Review it before it goes out.</p>
        </div>
        <button onClick={() => setShowForm((v) => !v)} className="btn-primary">
          <Plus size={14} strokeWidth={2} /><span>Set up recurring</span>
        </button>
      </header>

      {showForm && (
        <section className="card p-8 mb-8 space-y-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="field-label">Client *</label>
              <select className="field-select" value={clientId}
                      onChange={(e) => setClientId(Number(e.target.value))}>
                <option value={0}>Select a client…</option>
                {clients?.map((c: Client) => <option key={c.id} value={c.id}>{c.name}</option>)}
              </select>
            </div>
            <div>
              <label className="field-label">Frequency *</label>
              <select className="field-select" value={frequency}
                      onChange={(e) => setFrequency(e.target.value as 'weekly' | 'monthly')}>
                <option value="monthly">Monthly</option>
                <option value="weekly">Weekly</option>
              </select>
            </div>
            <div>
              <label className="field-label">Start date *</label>
              <input type="date" className="field-input font-mono" value={startDate}
                     onChange={(e) => setStartDate(e.target.value)} />
            </div>
            <div>
              <label className="field-label">End date (optional)</label>
              <input type="date" className="field-input font-mono" value={endDate}
                     onChange={(e) => setEndDate(e.target.value)} />
            </div>
          </div>

          <div>
            <label className="field-label">Short description</label>
            <input className="field-input" value={shortDesc}
                   onChange={(e) => setShortDesc(e.target.value)} placeholder="e.g. Monthly retainer" />
          </div>

          <div>
            <label className="field-label">Line items *</label>
            {items.map((it, idx) => (
              <div key={idx} className="grid grid-cols-[1fr_5rem_8rem_2rem] gap-3 mb-2 items-center">
                <input className="field-input" placeholder="Description" value={it.description}
                       onChange={(e) => setItems(items.map((x, i) => i === idx ? { ...x, description: e.target.value } : x))} />
                <input type="number" className="field-input text-center font-mono" value={it.quantity}
                       onChange={(e) => setItems(items.map((x, i) => i === idx ? { ...x, quantity: Number(e.target.value) } : x))} />
                <input type="number" className="field-input text-right font-mono" value={it.rate}
                       onChange={(e) => setItems(items.map((x, i) => i === idx ? { ...x, rate: Number(e.target.value) } : x))} />
                <button type="button" className="text-ink-muted hover:text-oxblood disabled:opacity-30"
                        disabled={items.length === 1}
                        onClick={() => setItems(items.filter((_, i) => i !== idx))}>
                  <Trash2 size={14} strokeWidth={1.5} />
                </button>
              </div>
            ))}
            <button type="button" className="btn-secondary mt-2"
                    onClick={() => setItems([...items, { description: '', quantity: 1, rate: 0 }])}>
              <Plus size={14} strokeWidth={2} /><span>Add line</span>
            </button>
          </div>

          <div className="flex justify-end gap-3 pt-2">
            <button className="btn-ghost" onClick={() => setShowForm(false)}>Cancel</button>
            <button className="btn-primary" disabled={!canSave || createMutation.isPending}
                    onClick={() => createMutation.mutate()}>
              {createMutation.isPending ? 'Saving…' : 'Create schedule'}
            </button>
          </div>
        </section>
      )}

      <div className="card overflow-hidden">
        {schedules && schedules.length > 0 ? (
          <table className="table-editorial">
            <thead>
              <tr>
                <th>Client</th><th>Every</th><th>Next draft</th>
                <th className="!text-right">Amount</th><th>Status</th><th className="!text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {schedules.map((s) => (
                <tr key={s.id}>
                  <td className="text-ink">{s.client_name}</td>
                  <td className="text-ink-muted capitalize">{s.frequency}</td>
                  <td className="font-mono text-ink-muted tabular">{s.next_run_date}</td>
                  <td className="text-right font-mono text-ink tabular">{formatINR(lineTotal(s.items))}</td>
                  <td><span className={s.active ? 'pill-paid' : 'pill-draft'}>{s.active ? 'active' : 'paused'}</span></td>
                  <td>
                    <div className="flex items-center justify-end gap-0.5">
                      <button onClick={() => toggleMutation.mutate(s)} title={s.active ? 'Pause' : 'Resume'}
                              className="p-1.5 text-ink-muted hover:text-ink hover:bg-paper-deep rounded-sm">
                        {s.active ? <Pause size={14} strokeWidth={1.5} /> : <Play size={14} strokeWidth={1.5} />}
                      </button>
                      <button onClick={() => { if (confirm('Delete this recurring schedule?')) deleteMutation.mutate(s.id); }}
                              title="Delete"
                              className="p-1.5 text-ink-muted hover:text-oxblood hover:bg-oxblood-wash rounded-sm">
                        <Trash2 size={14} strokeWidth={1.5} />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <div className="p-16 text-center">
            <div className="page-eyebrow">Nothing scheduled</div>
            <h2 className="section-title mt-2">No recurring invoices yet</h2>
            <p className="text-base text-ink-muted mt-3">Set one up to auto-draft repeat bills.</p>
          </div>
        )}
      </div>
    </div>
  );
}
