import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
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
