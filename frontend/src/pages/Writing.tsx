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
