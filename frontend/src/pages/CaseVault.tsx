import { useState, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, CaseParty, Lead } from '../api';
import { usePermissions } from '../hooks/usePermissions';
import { useToast } from '../contexts/ToastContext';
import { Plus, X, Search } from 'lucide-react';

const errMsg = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong');

const EMPTY = {
  title: '', client_id: 0, matter_type: '', court: '', court_case_number: '',
  priority: 'normal', parties: [] as CaseParty[],
};

export default function CaseVault() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const { has } = usePermissions();
  const canCreate = has('case_files.create');

  const [modalOpen, setModalOpen] = useState(false);
  const [form, setForm] = useState(EMPTY);

  const [search, setSearch] = useState('');
  const [debounced, setDebounced] = useState('');
  useEffect(() => { const t = setTimeout(() => setDebounced(search), 250); return () => clearTimeout(t); }, [search]);

  const { data: meta } = useQuery({ queryKey: ['case-meta'], queryFn: api.getCaseMeta });
  const { data: cases = [], isLoading } = useQuery({
    queryKey: ['case-files', debounced], queryFn: () => api.getCaseFiles(debounced ? { search: debounced } : undefined),
  });
  const { data: clients = [] } = useQuery({ queryKey: ['clients'], queryFn: () => api.getClients() });

  const stages = meta?.stages ?? [];

  const createMutation = useMutation({
    mutationFn: () => api.createCaseFile({
      ...form,
      client_id: Number(form.client_id),
      parties: form.parties.filter((p) => p.name.trim()),
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['case-files'] });
      setModalOpen(false); setForm(EMPTY); showToast('Case file opened');
    },
    onError: (e) => showToast(errMsg(e), 'error'),
  });

  const navigate = useNavigate();
  const [leadModalOpen, setLeadModalOpen] = useState(false);
  const [leadForm, setLeadForm] = useState({ contact_name: '', phone: '', email: '', matter_summary: '', intake_notes: '' });

  const { data: leads = [] } = useQuery({
    queryKey: ['leads', 'open'], queryFn: () => api.getLeads('open'),
  });

  const createLead = useMutation({
    mutationFn: () => api.createLead(leadForm),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      setLeadModalOpen(false);
      setLeadForm({ contact_name: '', phone: '', email: '', matter_summary: '', intake_notes: '' });
      showToast('Enquiry logged');
    },
    onError: (e) => showToast(errMsg(e), 'error'),
  });

  const declineLead = useMutation({
    mutationFn: (id: number) => api.updateLead(id, { status: 'declined' }),
    onSuccess: () => { queryClient.invalidateQueries({ queryKey: ['leads'] }); showToast('Enquiry declined'); },
    onError: (e) => showToast(errMsg(e), 'error'),
  });

  const acceptLead = useMutation({
    mutationFn: (lead: Lead) => api.convertLead(lead.id, { title: lead.matter_summary || lead.contact_name }),
    onSuccess: (caseFile) => {
      queryClient.invalidateQueries({ queryKey: ['leads'] });
      queryClient.invalidateQueries({ queryKey: ['case-files'] });
      showToast('Case file opened');
      navigate(`/cases/${caseFile.id}`);
    },
    onError: (e) => showToast(errMsg(e), 'error'),
  });

  const [viewLead, setViewLead] = useState<Lead | null>(null);
  const [leadEdit, setLeadEdit] = useState(false);
  const [leadDraft, setLeadDraft] = useState<Partial<Lead>>({});
  const openLead = (l: Lead) => { setViewLead(l); setLeadEdit(false); setLeadDraft(l); };
  const saveLead = useMutation({
    mutationFn: () => api.updateLead(viewLead!.id, {
      contact_name: leadDraft.contact_name, phone: leadDraft.phone, email: leadDraft.email,
      matter_summary: leadDraft.matter_summary, intake_notes: leadDraft.intake_notes,
    }),
    onSuccess: (updated) => { queryClient.invalidateQueries({ queryKey: ['leads'] }); setViewLead(updated); setLeadEdit(false); showToast('Enquiry updated'); },
    onError: (e) => showToast(errMsg(e), 'error'),
  });

  return (
    <div className="space-y-10">
      {/* Enquiries — prospective matters, before they become case files */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="eyebrow">Enquiries</h2>
          {canCreate && (
            <button onClick={() => setLeadModalOpen(true)} className="btn-ghost">
              <Plus size={14} strokeWidth={2} /><span>New enquiry</span>
            </button>
          )}
        </div>
        {leads.length === 0 ? (
          <div className="border border-dashed border-rule bg-surface p-8 text-center text-sm text-ink-muted">
            No open enquiries. Log a prospective matter before you decide to take it on.
          </div>
        ) : (
          <div className="border border-rule divide-y divide-rule">
            {leads.map((l) => (
              <div key={l.id} className="bg-surface flex items-center gap-4 px-5 py-3">
                <button onClick={() => openLead(l)} className="flex-1 min-w-0 text-left">
                  <div className="text-sm text-ink font-medium truncate hover:text-oxblood">{l.contact_name}</div>
                  <div className="text-2xs text-ink-muted truncate">{l.matter_summary}</div>
                </button>
                <button onClick={() => openLead(l)} className="btn-ghost text-2xs">View</button>
                <button onClick={() => declineLead.mutate(l.id)} className="btn-ghost text-2xs">Decline</button>
                <button onClick={() => acceptLead.mutate(l)} className="btn-primary text-2xs">Accept → open file</button>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* All cases */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <h2 className="eyebrow">All cases</h2>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search size={13} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-ink-faint" />
              <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search cases…"
                className="field-input !py-1.5 !pl-8 text-sm w-56" data-search />
            </div>
            {canCreate && (
              <button onClick={() => setModalOpen(true)} className="btn-primary">
                <Plus size={14} strokeWidth={2} /><span>New case</span>
              </button>
            )}
          </div>
        </div>
        {isLoading ? (
          <div className="card p-16 flex justify-center"><div className="spinner" /></div>
        ) : (
          <div className="border border-rule divide-y divide-rule">
            {cases.map((c) => (
              <Link key={c.id} to={`/cases/${c.id}`}
                className="bg-surface flex items-center gap-4 px-5 py-3 hover:bg-paper-deep/40">
                <span className="text-2xs font-mono text-oxblood w-28 shrink-0">{c.case_number}</span>
                <span className="text-sm text-ink flex-1 truncate">{c.title}</span>
                <span className="text-xs text-ink-muted w-40 truncate">{c.client_name}</span>
                <span className="text-2xs uppercase tracking-eyebrow text-ink-muted w-36 text-right">
                  {stages.find((s) => s.key === c.stage)?.label ?? c.stage}
                </span>
              </Link>
            ))}
            {cases.length === 0 && (
              <div className="bg-surface p-10 text-center text-sm text-ink-muted">No case files yet.</div>
            )}
          </div>
        )}
      </section>

      {modalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in">
          <div className="absolute inset-0 bg-ink/40 backdrop-blur-[2px]" onClick={() => setModalOpen(false)} />
          <div className="relative bg-surface border border-rule rounded-DEFAULT max-w-xl w-full
                          max-h-[90vh] overflow-y-auto shadow-modal animate-fade-up">
            <div className="h-[3px] bg-oxblood" />
            <div className="p-8">
              <button onClick={() => setModalOpen(false)}
                className="absolute top-5 right-5 text-ink-faint hover:text-ink-muted" aria-label="Close">
                <X size={20} strokeWidth={1.5} />
              </button>
              <div className="mb-6"><div className="page-eyebrow">New matter</div>
                <h2 className="page-title !text-2xl">Open a case file</h2></div>
              <form onSubmit={(e) => { e.preventDefault(); createMutation.mutate(); }} className="space-y-4">
                <div>
                  <label className="field-label">Title *</label>
                  <input required value={form.title} autoFocus
                    onChange={(e) => setForm({ ...form, title: e.target.value })}
                    className="field-input" placeholder="e.g., X Corp vs State of Delhi" />
                </div>
                <div>
                  <label className="field-label">Client *</label>
                  <select required value={form.client_id}
                    onChange={(e) => setForm({ ...form, client_id: Number(e.target.value) })}
                    className="field-select">
                    <option value={0} disabled>Select a client…</option>
                    {clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                  </select>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="field-label">Court</label>
                    <input value={form.court}
                      onChange={(e) => setForm({ ...form, court: e.target.value })}
                      className="field-input" placeholder="Delhi High Court" />
                  </div>
                  <div>
                    <label className="field-label">Case / filing no.</label>
                    <input value={form.court_case_number}
                      onChange={(e) => setForm({ ...form, court_case_number: e.target.value })}
                      className="field-input font-mono" placeholder="W.P.(C) 1234/2026" />
                  </div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="field-label">Matter type</label>
                    <input value={form.matter_type}
                      onChange={(e) => setForm({ ...form, matter_type: e.target.value })}
                      className="field-input" placeholder="Constitutional / Civil / Tax…" />
                  </div>
                  <div>
                    <label className="field-label">Priority</label>
                    <select value={form.priority}
                      onChange={(e) => setForm({ ...form, priority: e.target.value })}
                      className="field-select">
                      {(meta?.priorities ?? [{ key: 'normal', label: 'Normal' }]).map((p) => (
                        <option key={p.key} value={p.key}>{p.label}</option>
                      ))}
                    </select>
                  </div>
                </div>
                <div className="flex gap-3 justify-end pt-4 border-t border-rule">
                  <button type="button" onClick={() => setModalOpen(false)} className="btn-ghost">Cancel</button>
                  <button type="submit" className="btn-primary" disabled={createMutation.isPending}>Open file</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {leadModalOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in">
          <div className="absolute inset-0 bg-ink/40 backdrop-blur-[2px]" onClick={() => setLeadModalOpen(false)} />
          <div className="relative bg-surface border border-rule rounded-DEFAULT max-w-lg w-full
                          max-h-[90vh] overflow-y-auto shadow-modal animate-fade-up">
            <div className="h-[3px] bg-oxblood" />
            <div className="p-8">
              <button onClick={() => setLeadModalOpen(false)}
                className="absolute top-5 right-5 text-ink-faint hover:text-ink-muted" aria-label="Close">
                <X size={20} strokeWidth={1.5} />
              </button>
              <div className="mb-6"><div className="page-eyebrow">Intake</div>
                <h2 className="page-title !text-2xl">Log an enquiry</h2></div>
              <form onSubmit={(e) => { e.preventDefault(); createLead.mutate(); }} className="space-y-4">
                <div>
                  <label className="field-label">Contact name *</label>
                  <input required autoFocus value={leadForm.contact_name}
                    onChange={(e) => setLeadForm({ ...leadForm, contact_name: e.target.value })}
                    className="field-input" placeholder="Who approached you?" />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="field-label">Phone</label>
                    <input value={leadForm.phone}
                      onChange={(e) => setLeadForm({ ...leadForm, phone: e.target.value })}
                      className="field-input" />
                  </div>
                  <div>
                    <label className="field-label">Email</label>
                    <input value={leadForm.email}
                      onChange={(e) => setLeadForm({ ...leadForm, email: e.target.value })}
                      className="field-input" />
                  </div>
                </div>
                <div>
                  <label className="field-label">Matter summary</label>
                  <input value={leadForm.matter_summary}
                    onChange={(e) => setLeadForm({ ...leadForm, matter_summary: e.target.value })}
                    className="field-input" placeholder="e.g., Property dispute" />
                </div>
                <div>
                  <label className="field-label">Intake notes</label>
                  <textarea value={leadForm.intake_notes} rows={4}
                    onChange={(e) => setLeadForm({ ...leadForm, intake_notes: e.target.value })}
                    className="field-input" placeholder="His story, the facts, your first read…" />
                </div>
                <div className="flex gap-3 justify-end pt-4 border-t border-rule">
                  <button type="button" onClick={() => setLeadModalOpen(false)} className="btn-ghost">Cancel</button>
                  <button type="submit" className="btn-primary" disabled={createLead.isPending}>Save enquiry</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {viewLead && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in">
          <div className="absolute inset-0 bg-ink/40 backdrop-blur-[2px]" onClick={() => setViewLead(null)} />
          <div className="relative bg-surface border border-rule rounded-DEFAULT max-w-lg w-full max-h-[90vh] overflow-y-auto shadow-modal animate-fade-up">
            <div className="h-[3px] bg-oxblood" />
            <div className="p-8">
              <button onClick={() => setViewLead(null)} className="absolute top-5 right-5 text-ink-faint hover:text-ink-muted"><X size={20} strokeWidth={1.5} /></button>
              <div className="mb-6"><div className="page-eyebrow">Enquiry</div><h2 className="page-title !text-2xl">{viewLead.contact_name}</h2></div>
              {leadEdit ? (
                <div className="space-y-4">
                  <div className="grid grid-cols-2 gap-4">
                    <div><label className="field-label">Contact name</label><input value={leadDraft.contact_name ?? ''} onChange={(e) => setLeadDraft({ ...leadDraft, contact_name: e.target.value })} className="field-input" /></div>
                    <div><label className="field-label">Phone</label><input value={leadDraft.phone ?? ''} onChange={(e) => setLeadDraft({ ...leadDraft, phone: e.target.value })} className="field-input" /></div>
                  </div>
                  <div><label className="field-label">Email</label><input value={leadDraft.email ?? ''} onChange={(e) => setLeadDraft({ ...leadDraft, email: e.target.value })} className="field-input" /></div>
                  <div><label className="field-label">Matter summary</label><input value={leadDraft.matter_summary ?? ''} onChange={(e) => setLeadDraft({ ...leadDraft, matter_summary: e.target.value })} className="field-input" /></div>
                  <div><label className="field-label">Intake notes</label><textarea rows={4} value={leadDraft.intake_notes ?? ''} onChange={(e) => setLeadDraft({ ...leadDraft, intake_notes: e.target.value })} className="field-textarea" /></div>
                  <div className="flex gap-3 justify-end pt-4 border-t border-rule">
                    <button onClick={() => setLeadEdit(false)} className="btn-ghost">Cancel</button>
                    <button onClick={() => saveLead.mutate()} className="btn-primary" disabled={saveLead.isPending}>Save</button>
                  </div>
                </div>
              ) : (
                <div className="space-y-4">
                  <dl className="grid grid-cols-2 gap-x-6 gap-y-3">
                    <div><dt className="text-2xs uppercase tracking-eyebrow text-ink-faint">Phone</dt><dd className="text-sm text-ink mt-0.5">{viewLead.phone || '—'}</dd></div>
                    <div><dt className="text-2xs uppercase tracking-eyebrow text-ink-faint">Email</dt><dd className="text-sm text-ink mt-0.5">{viewLead.email || '—'}</dd></div>
                    <div><dt className="text-2xs uppercase tracking-eyebrow text-ink-faint">Status</dt><dd className="text-sm text-ink mt-0.5 capitalize">{viewLead.status}</dd></div>
                    <div><dt className="text-2xs uppercase tracking-eyebrow text-ink-faint">Matter</dt><dd className="text-sm text-ink mt-0.5">{viewLead.matter_summary || '—'}</dd></div>
                  </dl>
                  {viewLead.intake_notes && (
                    <div><dt className="text-2xs uppercase tracking-eyebrow text-ink-faint mb-1">Intake notes</dt>
                      <p className="text-sm text-ink-muted whitespace-pre-wrap">{viewLead.intake_notes}</p></div>
                  )}
                  <div className="flex gap-3 justify-end pt-4 border-t border-rule">
                    <button onClick={() => setLeadEdit(true)} className="btn-ghost">Edit</button>
                    <button onClick={() => { declineLead.mutate(viewLead.id); setViewLead(null); }} className="btn-ghost">Decline</button>
                    <button onClick={() => { acceptLead.mutate(viewLead); setViewLead(null); }} className="btn-primary">Accept → open file</button>
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
