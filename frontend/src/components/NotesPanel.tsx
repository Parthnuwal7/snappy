import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api } from '../api';
import { useToast } from '../contexts/ToastContext';
import { Pin, PinOff, Trash2, Plus } from 'lucide-react';

const errMsg = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong');

export default function NotesPanel({ caseId, canUpdate }: { caseId: number; canUpdate: boolean }) {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const [body, setBody] = useState('');

  const { data: notes = [] } = useQuery({
    queryKey: ['case-notes', caseId], queryFn: () => api.getCaseNotes(caseId),
  });
  const invalidate = () => queryClient.invalidateQueries({ queryKey: ['case-notes', caseId] });

  const add = useMutation({
    mutationFn: () => api.addCaseNote(caseId, { body }),
    onSuccess: () => { invalidate(); setBody(''); },
    onError: (e) => showToast(errMsg(e), 'error'),
  });
  const togglePin = useMutation({
    mutationFn: ({ id, pinned }: { id: number; pinned: boolean }) => api.updateCaseNote(id, { pinned }),
    onSuccess: invalidate,
    onError: (e) => showToast(errMsg(e), 'error'),
  });
  const del = useMutation({
    mutationFn: (id: number) => api.deleteCaseNote(id),
    onSuccess: invalidate,
    onError: (e) => showToast(errMsg(e), 'error'),
  });

  return (
    <div className="card p-4">
      <div className="eyebrow mb-3">Notes</div>
      {canUpdate && (
        <form onSubmit={(e) => { e.preventDefault(); if (body.trim()) add.mutate(); }} className="mb-3">
          <textarea value={body} rows={2} placeholder="Jot a note…"
            onChange={(e) => setBody(e.target.value)} className="field-textarea text-sm" />
          <div className="flex justify-end mt-1.5">
            <button type="submit" disabled={!body.trim() || add.isPending} className="btn-primary text-2xs disabled:opacity-50">
              <Plus size={12} /> Add
            </button>
          </div>
        </form>
      )}
      <div className="space-y-2">
        {notes.map((n) => (
          <div key={n.id} className={`group text-sm border-l-2 pl-2.5 ${n.pinned ? 'border-oxblood' : 'border-rule'}`}>
            <p className="text-ink whitespace-pre-wrap">{n.body}</p>
            <div className="flex items-center gap-2 mt-0.5">
              <span className="text-2xs text-ink-faint">{n.created_at?.slice(0, 10)}</span>
              {canUpdate && (
                <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition">
                  <button onClick={() => togglePin.mutate({ id: n.id, pinned: !n.pinned })}
                    className="text-ink-muted hover:text-oxblood" title={n.pinned ? 'Unpin' : 'Pin to timeline'}>
                    {n.pinned ? <PinOff size={12} /> : <Pin size={12} />}
                  </button>
                  <button onClick={() => del.mutate(n.id)} className="text-ink-muted hover:text-oxblood" title="Delete">
                    <Trash2 size={12} />
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
        {notes.length === 0 && <p className="text-sm text-ink-muted">No notes yet.</p>}
      </div>
    </div>
  );
}
