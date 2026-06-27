import { useMemo } from 'react';
import { Link } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { api, CaseFile } from '../api';
import { usePermissions } from '../hooks/usePermissions';
import { useToast } from '../contexts/ToastContext';

const errMsg = (e: unknown) => (e instanceof Error ? e.message : 'Something went wrong');

const PRIORITY_DOT: Record<string, string> = {
  urgent: 'bg-oxblood', high: 'bg-oxblood/60', normal: 'bg-ink-faint', low: 'bg-rule',
};

export default function CasesKanban() {
  const queryClient = useQueryClient();
  const { showToast } = useToast();
  const { has } = usePermissions();
  const canMove = has('case_files.update');

  const { data: meta } = useQuery({ queryKey: ['case-meta'], queryFn: api.getCaseMeta });
  const { data: cases = [], isLoading } = useQuery({
    queryKey: ['case-files'], queryFn: () => api.getCaseFiles(),
  });

  const stages = (meta?.stages ?? []).filter((s) => s.key !== 'closed');
  const byStage = useMemo(() => {
    const map: Record<string, CaseFile[]> = {};
    stages.forEach((s) => { map[s.key] = []; });
    cases.forEach((c) => { if (map[c.stage]) map[c.stage].push(c); });
    return map;
  }, [cases, stages]);

  const moveMutation = useMutation({
    mutationFn: ({ id, stage }: { id: number; stage: string }) => api.moveCaseFile(id, stage),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['case-files'] }),
    onError: (e) => showToast(errMsg(e), 'error'),
  });

  const onDrop = (stage: string, e: React.DragEvent) => {
    e.preventDefault();
    const id = Number(e.dataTransfer.getData('text/case-id'));
    if (id && canMove) moveMutation.mutate({ id, stage });
  };

  if (isLoading) return <div className="card p-16 flex justify-center"><div className="spinner" /></div>;

  return (
    <div className="flex gap-4 overflow-x-auto pb-4">
      {stages.map((s) => (
        <div key={s.key}
          onDragOver={(e) => e.preventDefault()}
          onDrop={(e) => onDrop(s.key, e)}
          className="w-72 shrink-0">
          <div className="eyebrow mb-2 flex items-center justify-between">
            <span>{s.label}</span>
            <span className="text-ink-faint">{byStage[s.key]?.length ?? 0}</span>
          </div>
          <div className="space-y-2 min-h-[60px]">
            {(byStage[s.key] ?? []).map((c) => (
              <Link key={c.id} to={`/cases/${c.id}`}
                draggable={canMove}
                onDragStart={(e) => e.dataTransfer.setData('text/case-id', String(c.id))}
                className="block card p-3 hover:bg-paper-deep/40 transition-colors">
                <div className="flex items-center gap-1.5">
                  <span className={`h-1.5 w-1.5 rounded-full shrink-0 ${PRIORITY_DOT[c.priority] ?? PRIORITY_DOT.normal}`}
                    title={`Priority: ${c.priority}`} />
                  <div className="text-2xs font-mono text-oxblood">{c.case_number}</div>
                </div>
                <div className="text-sm text-ink font-medium leading-snug mt-0.5">{c.title}</div>
                <div className="text-2xs text-ink-muted mt-1">{c.client_name}</div>
                {c.court && <div className="text-2xs text-ink-faint mt-0.5">{c.court}</div>}
                {c.next_hearing_date && (
                  <div className="text-2xs text-oxblood mt-1">Next: {c.next_hearing_date}</div>
                )}
              </Link>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}
