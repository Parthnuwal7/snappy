import { CaseMeta } from '../api';
import { ArrowRight, ChevronRight, Lock } from 'lucide-react';

interface Props {
  stage: string;
  meta?: CaseMeta;
  canUpdate: boolean;
  onAction: (key: string) => void;
  onAdvance: (nextKey: string) => void;
  advancing: boolean;
}

export default function StageRail({ stage, meta, canUpdate, onAction, onAdvance, advancing }: Props) {
  const guide = meta?.stage_guides?.[stage];
  const nextKey = meta?.stage_flow?.[stage] ?? null;
  const nextLabel = nextKey ? (meta?.stages.find((s) => s.key === nextKey)?.label ?? nextKey) : null;
  if (!guide) return null;

  return (
    <aside className="lg:w-72 shrink-0 lg:sticky lg:top-6 self-start space-y-4">
      <div className="card p-4">
        <div className="eyebrow mb-1">This stage</div>
        <p className="text-sm text-ink-muted leading-snug mb-4">{guide.focus}</p>
        <div className="space-y-1.5">
          {guide.actions.map((a) =>
            a.available ? (
              <button key={a.key} onClick={() => onAction(a.key)}
                className="w-full flex items-center justify-between text-left text-sm text-ink
                           px-3 py-2 border border-rule hover:border-oxblood hover:text-oxblood transition-colors rounded-sm">
                <span>{a.label}</span><ChevronRight size={14} />
              </button>
            ) : (
              <div key={a.key}
                className="w-full flex items-center justify-between text-left text-sm text-ink-faint
                           px-3 py-2 border border-dashed border-rule rounded-sm"
                title="Arrives in a later phase">
                <span>{a.label}</span><Lock size={12} />
              </div>
            ),
          )}
        </div>
      </div>

      {canUpdate && nextKey && (
        <button onClick={() => onAdvance(nextKey)} disabled={advancing}
          className="btn-primary w-full justify-center disabled:opacity-50">
          <span>Advance to {nextLabel}</span><ArrowRight size={14} />
        </button>
      )}
      {!nextKey && (
        <div className="text-2xs uppercase tracking-eyebrow text-ink-faint text-center">Final stage</div>
      )}
    </aside>
  );
}
