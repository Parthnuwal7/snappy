import { useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, CaseFile, CaseParty } from '../api';
import { usePermissions } from '../hooks/usePermissions';
import { useToast } from '../contexts/ToastContext';
import { ArrowLeft, Plus, Trash2, FileText, Pencil, X, Check, Upload, Download, Paperclip } from 'lucide-react';
import StageRail from '../components/StageRail';
import NotesPanel from '../components/NotesPanel';

const errMsg = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong');
const today = () => new Date().toISOString().slice(0, 10);
const money = (n?: number | null) => (n == null ? '—' : '₹' + n.toLocaleString('en-IN'));

const PRIORITY_STYLE: Record<string, string> = {
  urgent: 'text-oxblood bg-oxblood-wash',
  high: 'text-oxblood bg-oxblood-wash',
  normal: 'text-ink-muted bg-paper-deep',
  low: 'text-ink-faint bg-paper-deep',
};

type Draft = Partial<CaseFile> & { parties: CaseParty[] };
type Tab = 'overview' | 'timeline' | 'documents' | 'evidence' | 'fees';

export default function CaseDetail() {
  const { id } = useParams();
  const caseId = Number(id);
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const { has } = usePermissions();
  const canUpdate = has('case_files.update');
  const canSeeMembers = has('members.read');
  const canUploadDocs = has('documents.create');
  const canDeleteDocs = has('documents.delete');

  const [tab, setTab] = useState<Tab>('overview');

  const { data: meta } = useQuery({ queryKey: ['case-meta'], queryFn: api.getCaseMeta });
  const { data: caseFile, isLoading } = useQuery({
    queryKey: ['case-file', caseId], queryFn: () => api.getCaseFile(caseId),
  });
  const { data: events = [] } = useQuery({
    queryKey: ['case-events', caseId], queryFn: () => api.getCaseEvents(caseId),
  });
  const { data: invoices = [] } = useQuery({
    queryKey: ['case-invoices', caseId], queryFn: () => api.getCaseInvoices(caseId),
  });
  const { data: documents = [] } = useQuery({
    queryKey: ['case-documents', caseId], queryFn: () => api.getCaseDocuments(caseId),
  });
  const { data: clients = [] } = useQuery({ queryKey: ['clients'], queryFn: () => api.getClients() });
  const { data: members = [] } = useQuery({
    queryKey: ['firm', 'members'], queryFn: api.getMembers, enabled: canSeeMembers,
  });
  const { data: financials } = useQuery({
    queryKey: ['case-financials', caseId], queryFn: () => api.getCaseFinancials(caseId),
  });
  const { data: stageHistory = [] } = useQuery({
    queryKey: ['case-stage-history', caseId], queryFn: () => api.getStageHistory(caseId),
  });
  const { data: expenses = [] } = useQuery({
    queryKey: ['case-expenses', caseId], queryFn: () => api.getCaseExpenses(caseId),
  });
  const { data: notes = [] } = useQuery({
    queryKey: ['case-notes', caseId], queryFn: () => api.getCaseNotes(caseId),
  });
  const { data: exhibits = [] } = useQuery({
    queryKey: ['case-exhibits', caseId], queryFn: () => api.getCaseExhibits(caseId),
  });

  const advocateName = (uid?: number | null) =>
    uid ? (members.find((m) => m.id === uid)?.email ?? `User #${uid}`) : null;

  // ---- edit modal --------------------------------------------------------
  const [editOpen, setEditOpen] = useState(false);
  const [draft, setDraft] = useState<Draft>({ parties: [] });
  const openEdit = () => {
    if (!caseFile) return;
    setDraft({ ...caseFile, parties: caseFile.parties ? [...caseFile.parties] : [] });
    setEditOpen(true);
  };
  const setField = (k: keyof Draft, v: unknown) => setDraft((d) => ({ ...d, [k]: v }));
  const setParty = (i: number, k: keyof CaseParty, v: string) =>
    setDraft((d) => ({ ...d, parties: d.parties.map((p, idx) => idx === i ? { ...p, [k]: v } : p) }));
  const addParty = () => setDraft((d) => ({ ...d, parties: [...d.parties, { name: '', role: '' }] }));
  const removeParty = (i: number) =>
    setDraft((d) => ({ ...d, parties: d.parties.filter((_, idx) => idx !== i) }));

  const saveCase = useMutation({
    mutationFn: () => api.updateCaseFile(caseId, {
      title: draft.title, client_id: draft.client_id, matter_type: draft.matter_type,
      court: draft.court, court_case_number: draft.court_case_number,
      jurisdiction: draft.jurisdiction, act_section: draft.act_section,
      opposing_counsel: draft.opposing_counsel, priority: draft.priority,
      agreed_fee: draft.agreed_fee ?? null,
      handling_advocate_user_id: draft.handling_advocate_user_id || null,
      filing_date: draft.filing_date || null,
      open_date: draft.open_date || null, description: draft.description,
      parties: draft.parties.filter((p) => p.name.trim()),
    }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['case-file', caseId] });
      queryClient.invalidateQueries({ queryKey: ['case-files'] });
      queryClient.invalidateQueries({ queryKey: ['case-financials', caseId] });
      setEditOpen(false); showToast('Case updated');
    },
    onError: (e) => showToast(errMsg(e), 'error'),
  });

  // ---- stage / timeline --------------------------------------------------
  const invalidateStage = () => {
    queryClient.invalidateQueries({ queryKey: ['case-file', caseId] });
    queryClient.invalidateQueries({ queryKey: ['case-files'] });
    queryClient.invalidateQueries({ queryKey: ['case-stage-history', caseId] });
  };
  const stageMutation = useMutation({
    mutationFn: (stage: string) => api.updateCaseFile(caseId, { stage }),
    onSuccess: () => { invalidateStage(); showToast('Stage updated'); },
    onError: (e) => showToast(errMsg(e), 'error'),
  });

  const railAction = (key: string) => {
    switch (key) {
      case 'note': setTab('timeline'); break;
      case 'add_party': openEdit(); break;
      case 'documents': setTab('documents'); break;
      case 'mark_exhibit': setTab('evidence'); break;
      case 'record_proceedings': setProcOpen(true); break;
      case 'raise_bill': setTab('fees'); break;
      default: break;
    }
  };

  const [step, setStep] = useState({ event_date: today(), kind: 'note', title: '', notes: '' });
  const [editingEventId, setEditingEventId] = useState<number | null>(null);
  const [eventDraft, setEventDraft] = useState({ event_date: '', kind: 'note', title: '', notes: '' });
  const addStep = useMutation({
    mutationFn: () => api.addCaseEvent(caseId, step),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['case-events', caseId] });
      setStep({ event_date: today(), kind: 'note', title: '', notes: '' }); showToast('Step added');
    },
    onError: (e) => showToast(errMsg(e), 'error'),
  });
  const saveStep = useMutation({
    mutationFn: (eventId: number) => api.updateCaseEvent(eventId, eventDraft),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['case-events', caseId] });
      setEditingEventId(null); showToast('Step updated');
    },
    onError: (e) => showToast(errMsg(e), 'error'),
  });
  const delStep = useMutation({
    mutationFn: (eventId: number) => api.deleteCaseEvent(eventId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['case-events', caseId] }),
    onError: (e) => showToast(errMsg(e), 'error'),
  });

  // ---- documents ---------------------------------------------------------
  const [docTitle, setDocTitle] = useState('');
  const [docType, setDocType] = useState('other');
  const [docFile, setDocFile] = useState<File | null>(null);
  const uploadDoc = useMutation({
    mutationFn: () => api.uploadCaseDocument(caseId, docFile as File, { title: docTitle, doc_type: docType }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['case-documents', caseId] });
      setDocTitle(''); setDocType('other'); setDocFile(null); showToast('Document uploaded');
    },
    onError: (e) => showToast(errMsg(e), 'error'),
  });
  const deleteDoc = useMutation({
    mutationFn: (docId: number) => api.deleteCaseDocument(docId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['case-documents', caseId] }),
    onError: (e) => showToast(errMsg(e), 'error'),
  });
  const openDoc = async (docId: number) => {
    try { const { url } = await api.getDocumentDownloadUrl(docId); window.open(url, '_blank'); }
    catch (e) { showToast(errMsg(e), 'error'); }
  };

  // ---- expenses ----------------------------------------------------------
  const [exp, setExp] = useState({ expense_date: today(), description: '', category: 'misc', amount: 0 });
  const invalidateFees = () => {
    queryClient.invalidateQueries({ queryKey: ['case-expenses', caseId] });
    queryClient.invalidateQueries({ queryKey: ['case-financials', caseId] });
  };
  const addExpense = useMutation({
    mutationFn: () => api.addCaseExpense(caseId, exp),
    onSuccess: () => { invalidateFees(); setExp({ expense_date: today(), description: '', category: 'misc', amount: 0 }); showToast('Expense added'); },
    onError: (e) => showToast(errMsg(e), 'error'),
  });
  const deleteExpense = useMutation({
    mutationFn: (eid: number) => api.deleteCaseExpense(eid),
    onSuccess: () => invalidateFees(),
    onError: (e) => showToast(errMsg(e), 'error'),
  });

  // ---- exhibits ----------------------------------------------------------
  const EMPTY_EXHIBIT = { exhibit_mark: '', description: '', party: '', status: 'marked', document_id: '', hearing_event_id: '' };
  const [exhibit, setExhibit] = useState(EMPTY_EXHIBIT);
  const invalidateExhibits = () => queryClient.invalidateQueries({ queryKey: ['case-exhibits', caseId] });
  const addExhibit = useMutation({
    mutationFn: () => api.addCaseExhibit(caseId, {
      exhibit_mark: exhibit.exhibit_mark, description: exhibit.description,
      party: exhibit.party || null, status: exhibit.status,
      document_id: exhibit.document_id ? Number(exhibit.document_id) : null,
      hearing_event_id: exhibit.hearing_event_id ? Number(exhibit.hearing_event_id) : null,
    }),
    onSuccess: () => { invalidateExhibits(); setExhibit(EMPTY_EXHIBIT); showToast('Exhibit added'); },
    onError: (e) => showToast(errMsg(e), 'error'),
  });
  const setExhibitStatus = useMutation({
    mutationFn: ({ id, status }: { id: number; status: string }) => api.updateCaseExhibit(id, { status }),
    onSuccess: invalidateExhibits,
    onError: (e) => showToast(errMsg(e), 'error'),
  });
  const deleteExhibit = useMutation({
    mutationFn: (id: number) => api.deleteCaseExhibit(id),
    onSuccess: invalidateExhibits,
    onError: (e) => showToast(errMsg(e), 'error'),
  });
  const hearings = events.filter((ev) => ev.kind === 'hearing');

  // ---- proceedings / next date -------------------------------------------
  const invalidateHearing = () => {
    queryClient.invalidateQueries({ queryKey: ['case-file', caseId] });
    queryClient.invalidateQueries({ queryKey: ['case-files'] });
    queryClient.invalidateQueries({ queryKey: ['case-events', caseId] });
  };
  const [procOpen, setProcOpen] = useState(false);
  const [proc, setProc] = useState({ outcome: '', purpose: '', next_date: today() });
  const currentHearing = events.find((ev) => ev.kind === 'hearing' && ev.event_date === caseFile?.next_hearing_date);
  const recordProc = useMutation({
    mutationFn: () => api.recordProceedings(caseId, {
      next_date: proc.next_date, purpose: proc.purpose || undefined,
      outcome: proc.outcome || undefined, current_event_id: currentHearing?.id,
    }),
    onSuccess: () => { invalidateHearing(); setProcOpen(false); setProc({ outcome: '', purpose: '', next_date: today() }); showToast('Proceedings recorded'); },
    onError: (e) => showToast(errMsg(e), 'error'),
  });
  const nextDateMut = useMutation({
    mutationFn: (next_date: string) => api.setNextDate(caseId, { next_date }),
    onSuccess: () => { invalidateHearing(); showToast('Next date updated'); },
    onError: (e) => showToast(errMsg(e), 'error'),
  });

  if (isLoading || !caseFile) {
    return <div className="max-w-page mx-auto px-8 py-16 flex justify-center"><div className="spinner" /></div>;
  }

  const fact = (label: string, value?: string | null) => value ? (
    <div><dt className="text-2xs uppercase tracking-eyebrow text-ink-faint">{label}</dt>
      <dd className="text-sm text-ink mt-0.5">{value}</dd></div>
  ) : null;

  return (
    <div className="max-w-page mx-auto px-8 lg:px-12 py-10">
      <Link to="/cases" className="inline-flex items-center gap-1.5 text-xs text-ink-muted hover:text-oxblood mb-6">
        <ArrowLeft size={13} /> Back to docket
      </Link>

      <header className="mb-6">
        <div className="flex items-center gap-3">
          <div className="page-eyebrow font-mono">{caseFile.case_number}</div>
          <span className={`text-2xs uppercase tracking-eyebrow px-1.5 py-0.5 rounded-sm ${PRIORITY_STYLE[caseFile.priority] ?? PRIORITY_STYLE.normal}`}>
            {caseFile.priority}
          </span>
        </div>
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <h1 className="page-title">{caseFile.title}</h1>
          <div className="flex items-center gap-3">
            <div>
              <label className="field-label">Stage</label>
              <select value={caseFile.stage} disabled={!canUpdate}
                onChange={(e) => stageMutation.mutate(e.target.value)} className="field-select w-48">
                {(meta?.stages ?? []).map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
              </select>
            </div>
            {canUpdate && <button onClick={openEdit} className="btn-ghost mt-5"><Pencil size={13} /> Edit details</button>}
          </div>
        </div>
        <dl className="grid grid-cols-2 md:grid-cols-4 gap-x-6 gap-y-3 mt-5">
          {fact('Client', caseFile.client_name)}
          {fact('Court', caseFile.court)}
          {fact('Case / filing no.', caseFile.court_case_number)}
          {fact('Jurisdiction', caseFile.jurisdiction)}
          {fact('Matter type', caseFile.matter_type)}
          {fact('Act / section', caseFile.act_section)}
          {fact('Opposing counsel', caseFile.opposing_counsel)}
          {fact('Handling advocate', advocateName(caseFile.handling_advocate_user_id))}
          {fact('Filed', caseFile.filing_date)}
          <div>
            <dt className="text-2xs uppercase tracking-eyebrow text-ink-faint">Next hearing</dt>
            <dd className="text-sm text-ink mt-0.5">
              {canUpdate ? (
                <input type="date" value={caseFile.next_hearing_date ?? ''}
                  onChange={(e) => e.target.value && nextDateMut.mutate(e.target.value)}
                  className="field-input !py-0.5 !text-sm w-40" />
              ) : (caseFile.next_hearing_date ?? '—')}
            </dd>
          </div>
          {fact('Opened', caseFile.open_date)}
          {fact('Agreed fee', caseFile.agreed_fee != null ? money(caseFile.agreed_fee) : null)}
        </dl>
      </header>

      <div className="flex flex-col lg:flex-row gap-8">
      <div className="flex-1 min-w-0">
      {/* Tabs */}
      <div className="flex gap-1 border-b border-rule mb-6">
        {(['overview', 'timeline', 'documents', 'evidence', 'fees'] as const).map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm capitalize border-b-2 -mb-px transition-colors ${
              tab === t ? 'border-oxblood text-ink' : 'border-transparent text-ink-muted hover:text-ink'}`}>
            {t === 'fees' ? 'Fees & billing' : t}
          </button>
        ))}
      </div>

      {/* Overview */}
      {tab === 'overview' && (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          <div className="lg:col-span-2 space-y-6">
            {caseFile.description && <p className="text-sm text-ink-muted whitespace-pre-wrap">{caseFile.description}</p>}
            <div>
              <div className="eyebrow mb-3">Progression</div>
              <ol className="space-y-2">
                {stageHistory.map((h) => (
                  <li key={h.id} className="text-sm text-ink-muted">
                    <span className="font-mono text-2xs text-ink-faint">{h.changed_at?.slice(0, 10)}</span>{' '}
                    {h.from_stage ? `${h.from_stage} → ` : 'opened at '}<span className="text-ink">{h.to_stage}</span>
                  </li>
                ))}
                {stageHistory.length === 0 && <li className="text-sm text-ink-muted">No history.</li>}
              </ol>
            </div>
            {notes.some((n) => n.pinned) && (
              <div>
                <div className="eyebrow mb-3">Pinned notes</div>
                <ul className="space-y-2">
                  {notes.filter((n) => n.pinned).map((n) => (
                    <li key={n.id} className="text-sm text-ink border-l-2 border-oxblood pl-2.5 whitespace-pre-wrap">{n.body}</li>
                  ))}
                </ul>
              </div>
            )}
          </div>
          <aside>
            <div className="eyebrow mb-3">Parties</div>
            <div className="border border-rule divide-y divide-rule">
              {(caseFile.parties ?? []).map((p, i) => (
                <div key={i} className="bg-surface px-4 py-2.5">
                  <div className="text-sm text-ink">{p.name}</div>
                  <div className="text-2xs uppercase tracking-eyebrow text-ink-muted">{p.role}</div>
                </div>
              ))}
              {(caseFile.parties ?? []).length === 0 && <div className="bg-surface px-4 py-3 text-sm text-ink-muted">No parties.</div>}
            </div>
          </aside>
        </div>
      )}

      {/* Timeline */}
      {tab === 'timeline' && (
        <section className="max-w-3xl">
          {canUpdate && (
            <form onSubmit={(e) => { e.preventDefault(); addStep.mutate(); }} className="card p-4 mb-5 space-y-3">
              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="field-label">Date</label>
                  <input type="date" value={step.event_date} onChange={(e) => setStep({ ...step, event_date: e.target.value })} className="field-input" />
                </div>
                <div>
                  <label className="field-label">Kind</label>
                  <select value={step.kind} onChange={(e) => setStep({ ...step, kind: e.target.value })} className="field-select">
                    {(meta?.event_kinds ?? []).map((k) => <option key={k} value={k}>{k}</option>)}
                  </select>
                </div>
              </div>
              <input required value={step.title} placeholder="What happened — e.g. Notice issued"
                onChange={(e) => setStep({ ...step, title: e.target.value })} className="field-input" />
              <textarea value={step.notes} rows={2} placeholder="Notes (optional)"
                onChange={(e) => setStep({ ...step, notes: e.target.value })} className="field-textarea" />
              <div className="flex justify-end">
                <button type="submit" className="btn-primary" disabled={addStep.isPending}><Plus size={14} strokeWidth={2} /><span>Add step</span></button>
              </div>
            </form>
          )}
          <ol className="relative border-l border-rule ml-2 space-y-5">
            {events.map((ev) => (
              <li key={ev.id} className="ml-5">
                <span className="absolute -left-[5px] mt-1.5 h-2 w-2 rounded-full bg-oxblood" />
                {editingEventId === ev.id ? (
                  <div className="card p-3 space-y-2">
                    <div className="grid grid-cols-2 gap-2">
                      <input type="date" value={eventDraft.event_date} onChange={(e) => setEventDraft({ ...eventDraft, event_date: e.target.value })} className="field-input" />
                      <select value={eventDraft.kind} onChange={(e) => setEventDraft({ ...eventDraft, kind: e.target.value })} className="field-select">
                        {(meta?.event_kinds ?? []).map((k) => <option key={k} value={k}>{k}</option>)}
                      </select>
                    </div>
                    <input value={eventDraft.title} onChange={(e) => setEventDraft({ ...eventDraft, title: e.target.value })} className="field-input" />
                    <textarea value={eventDraft.notes} rows={2} onChange={(e) => setEventDraft({ ...eventDraft, notes: e.target.value })} className="field-textarea" />
                    <div className="flex justify-end gap-2">
                      <button onClick={() => setEditingEventId(null)} className="btn-ghost"><X size={13} /> Cancel</button>
                      <button onClick={() => saveStep.mutate(ev.id)} className="btn-primary"><Check size={13} /> Save</button>
                    </div>
                  </div>
                ) : (
                  <div className="flex items-start justify-between gap-3 group">
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="text-2xs font-mono text-ink-muted">{ev.event_date}</span>
                        <span className="text-2xs uppercase tracking-eyebrow text-oxblood bg-oxblood-wash px-1.5 py-0.5 rounded-sm">{ev.kind}</span>
                      </div>
                      <div className="text-sm text-ink font-medium mt-1">{ev.title}</div>
                      {ev.notes && <div className="text-sm text-ink-muted mt-0.5 whitespace-pre-wrap">{ev.notes}</div>}
                      {ev.purpose && <div className="text-2xs text-ink-muted mt-0.5">Purpose: {ev.purpose}</div>}
                      {ev.outcome && <div className="text-sm text-ink-muted mt-0.5 italic whitespace-pre-wrap">{ev.outcome}</div>}
                    </div>
                    {canUpdate && (
                      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition">
                        <button onClick={() => { setEditingEventId(ev.id); setEventDraft({ event_date: ev.event_date, kind: ev.kind, title: ev.title, notes: ev.notes ?? '' }); }} className="p-1 text-ink-muted hover:text-ink"><Pencil size={13} /></button>
                        <button onClick={() => delStep.mutate(ev.id)} className="p-1 text-ink-muted hover:text-oxblood"><Trash2 size={13} /></button>
                      </div>
                    )}
                  </div>
                )}
              </li>
            ))}
            {events.length === 0 && <li className="ml-5 text-sm text-ink-muted">No steps recorded yet.</li>}
          </ol>
        </section>
      )}

      {/* Documents */}
      {tab === 'documents' && (
        <div className="max-w-2xl">
          {canUploadDocs && (
            <div className="card p-4 mb-4 space-y-2">
              <input value={docTitle} placeholder="Title" onChange={(e) => setDocTitle(e.target.value)} className="field-input" />
              <select value={docType} onChange={(e) => setDocType(e.target.value)} className="field-select">
                {(meta?.doc_types ?? []).map((d) => <option key={d.key} value={d.key}>{d.label}</option>)}
              </select>
              <input type="file" onChange={(e) => setDocFile(e.target.files?.[0] ?? null)} className="text-xs" />
              <button onClick={() => uploadDoc.mutate()} disabled={!docFile || !docTitle || uploadDoc.isPending} className="btn-primary disabled:opacity-50"><Upload size={14} /> Upload</button>
            </div>
          )}
          <div className="border border-rule divide-y divide-rule">
            {documents.map((d) => (
              <div key={d.id} className="bg-surface flex items-center gap-2 px-4 py-2.5 group">
                <Paperclip size={13} className="text-ink-faint shrink-0" />
                <button onClick={() => openDoc(d.id)} className="text-sm text-ink flex-1 text-left hover:text-oxblood truncate">{d.title}</button>
                <span className="text-2xs uppercase tracking-eyebrow text-ink-muted">{d.doc_type}</span>
                <button onClick={() => openDoc(d.id)} className="p-1 text-ink-muted hover:text-ink"><Download size={13} /></button>
                {canDeleteDocs && <button onClick={() => { if (confirm(`Delete "${d.title}"?`)) deleteDoc.mutate(d.id); }} className="p-1 text-ink-muted hover:text-oxblood opacity-0 group-hover:opacity-100"><Trash2 size={13} /></button>}
              </div>
            ))}
            {documents.length === 0 && <div className="bg-surface px-4 py-3 text-sm text-ink-muted">No documents yet.</div>}
          </div>
        </div>
      )}

      {/* Evidence — exhibit register */}
      {tab === 'evidence' && (
        <div className="max-w-3xl">
          {canUpdate && (
            <form onSubmit={(e) => { e.preventDefault(); addExhibit.mutate(); }} className="card p-4 mb-4 space-y-2">
              <div className="grid grid-cols-2 gap-2">
                <input value={exhibit.exhibit_mark} placeholder="Mark — e.g. Ex. P-1"
                  onChange={(e) => setExhibit({ ...exhibit, exhibit_mark: e.target.value })} className="field-input font-mono" />
                <select value={exhibit.party} onChange={(e) => setExhibit({ ...exhibit, party: e.target.value })} className="field-select">
                  <option value="">— Producing party —</option>
                  {(meta?.exhibit_parties ?? []).map((p) => <option key={p.key} value={p.key}>{p.label}</option>)}
                </select>
              </div>
              <input value={exhibit.description} placeholder="Description"
                onChange={(e) => setExhibit({ ...exhibit, description: e.target.value })} className="field-input" />
              <div className="grid grid-cols-3 gap-2">
                <select value={exhibit.status} onChange={(e) => setExhibit({ ...exhibit, status: e.target.value })} className="field-select">
                  {(meta?.exhibit_statuses ?? []).map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
                </select>
                <select value={exhibit.document_id} onChange={(e) => setExhibit({ ...exhibit, document_id: e.target.value })} className="field-select">
                  <option value="">— Link file —</option>
                  {documents.map((d) => <option key={d.id} value={d.id}>{d.title}</option>)}
                </select>
                <select value={exhibit.hearing_event_id} onChange={(e) => setExhibit({ ...exhibit, hearing_event_id: e.target.value })} className="field-select">
                  <option value="">— Hearing —</option>
                  {hearings.map((h) => <option key={h.id} value={h.id}>{h.event_date} · {h.title}</option>)}
                </select>
              </div>
              <div className="flex justify-end">
                <button type="submit" className="btn-primary" disabled={addExhibit.isPending}><Plus size={14} /> Add exhibit</button>
              </div>
            </form>
          )}
          <div className="border border-rule divide-y divide-rule">
            {exhibits.map((ex) => {
              const doc = documents.find((d) => d.id === ex.document_id);
              return (
                <div key={ex.id} className="bg-surface flex items-center gap-3 px-4 py-2.5 group">
                  <span className="text-2xs font-mono text-oxblood w-16 shrink-0">{ex.exhibit_mark}</span>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm text-ink truncate">{ex.description}</div>
                    <div className="text-2xs text-ink-muted">
                      {ex.party}{doc && <button onClick={() => openDoc(doc.id)} className="ml-2 text-oxblood hover:underline">{doc.title}</button>}
                    </div>
                  </div>
                  {canUpdate ? (
                    <select value={ex.status} onChange={(e) => setExhibitStatus.mutate({ id: ex.id, status: e.target.value })}
                      className="field-select w-32 text-2xs">
                      {(meta?.exhibit_statuses ?? []).map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
                    </select>
                  ) : (
                    <span className="text-2xs uppercase tracking-eyebrow text-ink-muted">{ex.status}</span>
                  )}
                  {canUpdate && <button onClick={() => deleteExhibit.mutate(ex.id)} className="p-1 text-ink-muted hover:text-oxblood opacity-0 group-hover:opacity-100"><Trash2 size={13} /></button>}
                </div>
              );
            })}
            {exhibits.length === 0 && <div className="bg-surface px-4 py-3 text-sm text-ink-muted">No exhibits marked yet.</div>}
          </div>
        </div>
      )}

      {/* Fees & billing */}
      {tab === 'fees' && (
        <div className="space-y-8">
          <div className="grid grid-cols-2 md:grid-cols-5 gap-px bg-rule border border-rule">
            {([['Agreed fee', financials?.agreed_fee], ['Expenses', financials?.total_expenses],
               ['Invoiced', financials?.total_invoiced], ['Paid', financials?.total_paid],
               ['Outstanding', financials?.outstanding]] as [string, number | null | undefined][]).map(([label, val]) => (
              <div key={label} className="bg-surface p-4">
                <div className="text-2xs uppercase tracking-eyebrow text-ink-faint">{label}</div>
                <div className="font-display text-xl text-ink mt-1 tabular">{money(val)}</div>
              </div>
            ))}
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
            <div className="lg:col-span-2">
              <div className="eyebrow mb-3">Expenses</div>
              {canUpdate && (
                <form onSubmit={(e) => { e.preventDefault(); addExpense.mutate(); }} className="card p-3 mb-3 flex flex-wrap gap-2 items-end">
                  <input type="date" value={exp.expense_date} onChange={(e) => setExp({ ...exp, expense_date: e.target.value })} className="field-input w-36" />
                  <input value={exp.description} placeholder="Description" onChange={(e) => setExp({ ...exp, description: e.target.value })} className="field-input flex-1 min-w-[140px]" />
                  <select value={exp.category} onChange={(e) => setExp({ ...exp, category: e.target.value })} className="field-select w-36">
                    {(meta?.expense_categories ?? []).map((c) => <option key={c.key} value={c.key}>{c.label}</option>)}
                  </select>
                  <input type="number" value={exp.amount} onChange={(e) => setExp({ ...exp, amount: Number(e.target.value) })} className="field-input w-28 tabular" placeholder="₹" />
                  <button type="submit" className="btn-primary" disabled={!exp.description || addExpense.isPending}>Add</button>
                </form>
              )}
              <div className="border border-rule divide-y divide-rule">
                {expenses.map((x) => (
                  <div key={x.id} className="bg-surface flex items-center gap-3 px-4 py-2.5 group">
                    <span className="text-2xs font-mono text-ink-faint w-20">{x.expense_date}</span>
                    <span className="text-sm text-ink flex-1">{x.description}</span>
                    <span className="text-2xs uppercase tracking-eyebrow text-ink-muted">{x.category}</span>
                    <span className="text-sm tabular text-ink">{money(x.amount)}</span>
                    {canUpdate && <button onClick={() => deleteExpense.mutate(x.id)} className="p-1 text-ink-muted hover:text-oxblood opacity-0 group-hover:opacity-100"><Trash2 size={13} /></button>}
                  </div>
                ))}
                {expenses.length === 0 && <div className="bg-surface px-4 py-3 text-sm text-ink-muted">No expenses logged.</div>}
              </div>
            </div>
            <aside>
              <div className="eyebrow mb-3">Invoices</div>
              <div className="border border-rule divide-y divide-rule">
                {invoices.map((inv) => (
                  <div key={inv.id} className="bg-surface flex items-center gap-2 px-4 py-2.5">
                    <FileText size={13} className="text-ink-faint" />
                    <span className="text-sm text-ink flex-1">{inv.invoice_number}</span>
                    <span className="text-sm tabular text-ink-muted">{money(inv.total)}</span>
                  </div>
                ))}
                {invoices.length === 0 && <div className="bg-surface px-4 py-3 text-sm text-ink-muted">No invoices.</div>}
              </div>
              <Link to={`/invoices/new?case_file_id=${caseId}&client_id=${caseFile.client_id}`} className="btn-ghost mt-3 inline-flex"><Plus size={14} /> New invoice</Link>
            </aside>
          </div>
        </div>
      )}
      </div>

      <div className="lg:w-72 shrink-0 space-y-4">
        <StageRail stage={caseFile.stage} meta={meta} canUpdate={canUpdate}
          onAction={railAction} onAdvance={(k) => stageMutation.mutate(k)}
          advancing={stageMutation.isPending} />
        <NotesPanel caseId={caseId} canUpdate={canUpdate} />
      </div>
      </div>

      {/* Record proceedings modal */}
      {procOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in">
          <div className="absolute inset-0 bg-ink/40 backdrop-blur-[2px]" onClick={() => setProcOpen(false)} />
          <div className="relative bg-surface border border-rule rounded-DEFAULT max-w-lg w-full shadow-modal animate-fade-up">
            <div className="h-[3px] bg-oxblood" />
            <div className="p-8">
              <button onClick={() => setProcOpen(false)} className="absolute top-5 right-5 text-ink-faint hover:text-ink-muted"><X size={20} strokeWidth={1.5} /></button>
              <div className="mb-6"><div className="page-eyebrow">Order sheet</div><h2 className="page-title !text-2xl">Record proceedings</h2></div>
              <form onSubmit={(e) => { e.preventDefault(); recordProc.mutate(); }} className="space-y-4">
                {currentHearing && (
                  <p className="text-2xs text-ink-muted">Disposing hearing dated <span className="font-mono">{currentHearing.event_date}</span>.</p>
                )}
                <div>
                  <label className="field-label">What happened today</label>
                  <textarea value={proc.outcome} rows={2} placeholder="e.g. Reply filed; matter adjourned for evidence"
                    onChange={(e) => setProc({ ...proc, outcome: e.target.value })} className="field-textarea" />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="field-label">Purpose of next date</label>
                    <select value={proc.purpose} onChange={(e) => setProc({ ...proc, purpose: e.target.value })} className="field-select">
                      <option value="">—</option>
                      {(meta?.hearing_purposes ?? []).map((p) => <option key={p.key} value={p.key}>{p.label}</option>)}
                    </select>
                  </div>
                  <div>
                    <label className="field-label">Next date *</label>
                    <input required type="date" value={proc.next_date}
                      onChange={(e) => setProc({ ...proc, next_date: e.target.value })} className="field-input" />
                  </div>
                </div>
                <div className="flex gap-3 justify-end pt-4 border-t border-rule">
                  <button type="button" onClick={() => setProcOpen(false)} className="btn-ghost">Cancel</button>
                  <button type="submit" className="btn-primary" disabled={recordProc.isPending}>Save</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}

      {/* Edit modal */}
      {editOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 animate-fade-in">
          <div className="absolute inset-0 bg-ink/40 backdrop-blur-[2px]" onClick={() => setEditOpen(false)} />
          <div className="relative bg-surface border border-rule rounded-DEFAULT max-w-2xl w-full max-h-[90vh] overflow-y-auto shadow-modal animate-fade-up">
            <div className="h-[3px] bg-oxblood" />
            <div className="p-8">
              <button onClick={() => setEditOpen(false)} className="absolute top-5 right-5 text-ink-faint hover:text-ink-muted"><X size={20} strokeWidth={1.5} /></button>
              <div className="mb-6"><div className="page-eyebrow">Amend file</div><h2 className="page-title !text-2xl">Edit case details</h2></div>
              <form onSubmit={(e) => { e.preventDefault(); saveCase.mutate(); }} className="space-y-4">
                <div><label className="field-label">Title *</label>
                  <input required value={draft.title ?? ''} onChange={(e) => setField('title', e.target.value)} className="field-input" /></div>
                <div className="grid grid-cols-2 gap-4">
                  <div><label className="field-label">Client</label>
                    <select value={draft.client_id ?? 0} onChange={(e) => setField('client_id', Number(e.target.value))} className="field-select">
                      {clients.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
                    </select></div>
                  <div><label className="field-label">Priority</label>
                    <select value={draft.priority ?? 'normal'} onChange={(e) => setField('priority', e.target.value)} className="field-select">
                      {(meta?.priorities ?? []).map((p) => <option key={p.key} value={p.key}>{p.label}</option>)}
                    </select></div>
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div><label className="field-label">Court</label><input value={draft.court ?? ''} onChange={(e) => setField('court', e.target.value)} className="field-input" /></div>
                  <div><label className="field-label">Case / filing no.</label><input value={draft.court_case_number ?? ''} onChange={(e) => setField('court_case_number', e.target.value)} className="field-input font-mono" /></div>
                  <div><label className="field-label">Jurisdiction</label><input value={draft.jurisdiction ?? ''} onChange={(e) => setField('jurisdiction', e.target.value)} className="field-input" /></div>
                  <div><label className="field-label">Matter type</label><input value={draft.matter_type ?? ''} onChange={(e) => setField('matter_type', e.target.value)} className="field-input" /></div>
                  <div><label className="field-label">Act / section</label><input value={draft.act_section ?? ''} onChange={(e) => setField('act_section', e.target.value)} className="field-input" /></div>
                  <div><label className="field-label">Opposing counsel</label><input value={draft.opposing_counsel ?? ''} onChange={(e) => setField('opposing_counsel', e.target.value)} className="field-input" /></div>
                </div>
                {canSeeMembers && (
                  <div><label className="field-label">Handling advocate</label>
                    <select value={draft.handling_advocate_user_id ?? ''} onChange={(e) => setField('handling_advocate_user_id', e.target.value ? Number(e.target.value) : null)} className="field-select">
                      <option value="">— Unassigned —</option>
                      {members.map((m) => <option key={m.id} value={m.id}>{m.email}</option>)}
                    </select></div>
                )}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                  <div><label className="field-label">Agreed fee (₹)</label><input type="number" value={draft.agreed_fee ?? ''} onChange={(e) => setField('agreed_fee', e.target.value ? Number(e.target.value) : null)} className="field-input tabular" /></div>
                  <div><label className="field-label">Filed</label><input type="date" value={draft.filing_date ?? ''} onChange={(e) => setField('filing_date', e.target.value)} className="field-input" /></div>
                  <div><label className="field-label">Opened</label><input type="date" value={draft.open_date ?? ''} onChange={(e) => setField('open_date', e.target.value)} className="field-input" /></div>
                </div>
                <div><label className="field-label">Description</label><textarea value={draft.description ?? ''} rows={3} onChange={(e) => setField('description', e.target.value)} className="field-textarea" /></div>
                <div>
                  <div className="flex items-center justify-between mb-2">
                    <label className="field-label !mb-0">Parties</label>
                    <button type="button" onClick={addParty} className="text-xs text-oxblood hover:underline inline-flex items-center gap-1"><Plus size={12} /> Add party</button>
                  </div>
                  <div className="space-y-2">
                    {draft.parties.map((p, i) => (
                      <div key={i} className="flex gap-2">
                        <input value={p.name} placeholder="Name" onChange={(e) => setParty(i, 'name', e.target.value)} className="field-input flex-1" />
                        <input value={p.role ?? ''} placeholder="Role" onChange={(e) => setParty(i, 'role', e.target.value)} className="field-input w-40" />
                        <button type="button" onClick={() => removeParty(i)} className="p-2 text-ink-muted hover:text-oxblood"><Trash2 size={14} /></button>
                      </div>
                    ))}
                    {draft.parties.length === 0 && <div className="text-xs text-ink-faint">No parties yet.</div>}
                  </div>
                </div>
                <div className="flex gap-3 justify-end pt-4 border-t border-rule">
                  <button type="button" onClick={() => setEditOpen(false)} className="btn-ghost">Cancel</button>
                  <button type="submit" className="btn-primary" disabled={saveCase.isPending}>Save changes</button>
                </div>
              </form>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
