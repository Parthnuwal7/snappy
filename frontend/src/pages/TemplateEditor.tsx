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
